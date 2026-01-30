"""PostgreSQL + pgvector storage for code embeddings."""

import json
import os
from typing import Optional

import numpy as np
import psycopg
from pgvector.psycopg import register_vector

from .chunker import CodeChunk


class PgVectorStore:
    """Store and search code embeddings using PostgreSQL + pgvector."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        database: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        table_name: str = "code_chunks",
        embedding_dimensions: int = 768,
    ):
        """Initialize the vector store.

        Args:
            host: PostgreSQL host (defaults to PGHOST env var or localhost)
            port: PostgreSQL port (defaults to PGPORT env var or 5432)
            database: Database name (defaults to PGDATABASE env var or codebase_rag)
            user: Database user (defaults to PGUSER env var or postgres)
            password: Database password (defaults to PGPASSWORD env var)
            table_name: Table name for storing chunks
            embedding_dimensions: Dimensions of embedding vectors
        """
        self.host = host or os.environ.get("PGHOST", "localhost")
        self.port = port or int(os.environ.get("PGPORT", "5432"))
        self.database = database or os.environ.get("PGDATABASE", "codebase_rag")
        self.user = user or os.environ.get("PGUSER", "postgres")
        self.password = password or os.environ.get("PGPASSWORD", "")
        self.table_name = table_name
        self.embedding_dimensions = embedding_dimensions

        self._conn = None

    @property
    def connection_string(self) -> str:
        """Build connection string."""
        return f"host={self.host} port={self.port} dbname={self.database} user={self.user} password={self.password}"

    def connect(self) -> None:
        """Establish database connection."""
        self._conn = psycopg.connect(self.connection_string)
        # Enable pgvector extension before registering
        with self._conn.cursor() as cur:
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
            self._conn.commit()
        register_vector(self._conn)

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def create_table(self) -> None:
        """Create the chunks table with vector extension."""
        with self._conn.cursor() as cur:
            # Enable pgvector extension
            cur.execute("CREATE EXTENSION IF NOT EXISTS vector")

            # Create table
            # Note: "references" is a reserved keyword, so we quote it
            cur.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    embedding vector({self.embedding_dimensions}),
                    language TEXT,
                    chunk_type TEXT,
                    file_path TEXT,
                    start_line INTEGER,
                    end_line INTEGER,
                    class_name TEXT,
                    method_name TEXT,
                    documentation TEXT,
                    "references" TEXT[],
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create index for vector similarity search
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_embedding_idx
                ON {self.table_name}
                USING ivfflat (embedding vector_cosine_ops)
                WITH (lists = 100)
            """)

            # Create index for file path lookups
            cur.execute(f"""
                CREATE INDEX IF NOT EXISTS {self.table_name}_file_path_idx
                ON {self.table_name} (file_path)
            """)

            self._conn.commit()

    def drop_table(self) -> None:
        """Drop the chunks table."""
        with self._conn.cursor() as cur:
            cur.execute(f"DROP TABLE IF EXISTS {self.table_name}")
            self._conn.commit()

    def upsert(
        self,
        chunks: list[CodeChunk],
        embeddings: list[list[float]],
    ) -> int:
        """Insert or update chunks with embeddings.

        Args:
            chunks: List of code chunks
            embeddings: Corresponding embedding vectors

        Returns:
            Number of rows upserted
        """
        if len(chunks) != len(embeddings):
            raise ValueError("Chunks and embeddings must have same length")

        with self._conn.cursor() as cur:
            for chunk, embedding in zip(chunks, embeddings):
                # Convert embedding to numpy array for pgvector adapter
                embedding_vec = np.array(embedding, dtype=np.float32)

                cur.execute(
                    f"""
                    INSERT INTO {self.table_name}
                    (id, content, embedding, language, chunk_type, file_path,
                     start_line, end_line, class_name, method_name, documentation, "references", metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        content = EXCLUDED.content,
                        embedding = EXCLUDED.embedding,
                        language = EXCLUDED.language,
                        chunk_type = EXCLUDED.chunk_type,
                        file_path = EXCLUDED.file_path,
                        start_line = EXCLUDED.start_line,
                        end_line = EXCLUDED.end_line,
                        class_name = EXCLUDED.class_name,
                        method_name = EXCLUDED.method_name,
                        documentation = EXCLUDED.documentation,
                        "references" = EXCLUDED."references",
                        metadata = EXCLUDED.metadata
                    """,
                    (
                        chunk.id,
                        chunk.content,
                        embedding_vec,
                        chunk.language,
                        chunk.chunk_type,
                        chunk.file_path,
                        chunk.start_line,
                        chunk.end_line,
                        chunk.class_name,
                        chunk.method_name,
                        chunk.documentation,
                        chunk.references if chunk.references else None,
                        json.dumps(chunk.metadata) if chunk.metadata else None,
                    ),
                )

            self._conn.commit()

        return len(chunks)

    def search(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        language: Optional[str] = None,
        chunk_type: Optional[str] = None,
        file_path_prefix: Optional[str] = None,
        min_similarity: float = 0.0,
    ) -> list[tuple[CodeChunk, float]]:
        """Search for similar chunks using cosine similarity.

        Args:
            query_embedding: Query vector
            top_k: Number of results to return
            language: Filter by language
            chunk_type: Filter by chunk type
            file_path_prefix: Filter by file path prefix
            min_similarity: Minimum similarity threshold (0.0-1.0)

        Returns:
            List of (chunk, similarity_score) tuples, ordered by similarity
        """
        # Build WHERE clause
        conditions = []
        params = [query_embedding, top_k]

        if language:
            conditions.append(f"language = %s")
            params.insert(-1, language)
        if chunk_type:
            conditions.append(f"chunk_type = %s")
            params.insert(-1, chunk_type)
        if file_path_prefix:
            conditions.append(f"file_path LIKE %s")
            params.insert(-1, f"{file_path_prefix}%")

        where_clause = ""
        if conditions:
            where_clause = "WHERE " + " AND ".join(conditions)

        # Convert query_embedding to numpy array for pgvector
        # pgvector adapter (registered via register_vector) will convert numpy array to vector type
        query_vec = np.array(query_embedding, dtype=np.float32)

        query = f"""
            SELECT
                id, content, language, chunk_type, file_path,
                start_line, end_line, class_name, method_name,
                documentation, "references", metadata,
                1 - (embedding <=> %s) as similarity
            FROM {self.table_name}
            {where_clause}
            ORDER BY embedding <=> %s
            LIMIT %s
        """

        # Replace the first query_embedding with numpy array
        # pgvector adapter will automatically convert it to vector type
        params[0] = query_vec
        # Add query_embedding again for ORDER BY
        params.insert(-1, query_vec)

        with self._conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        results = []
        for row in rows:
            similarity = row[12]
            # Apply minimum similarity threshold
            if similarity < min_similarity:
                continue
            references = row[10] if row[10] else []
            # Metadata is JSONB, so psycopg3 returns it as a dict already
            metadata = row[11] if row[11] else {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            chunk = CodeChunk(
                id=row[0],
                content=row[1],
                language=row[2],
                chunk_type=row[3],
                file_path=row[4],
                start_line=row[5],
                end_line=row[6],
                class_name=row[7],
                method_name=row[8],
                documentation=row[9],
                references=references,
                metadata=metadata,
            )
            results.append((chunk, similarity))

        return results

    def keyword_search(
        self,
        keywords: list[str],
        top_k: int = 10,
        language: Optional[str] = None,
        chunk_type: Optional[str] = None,
    ) -> list[tuple[CodeChunk, float]]:
        """Search for chunks containing keywords using full-text search.

        Args:
            keywords: List of keywords to search for
            top_k: Number of results to return
            language: Filter by language
            chunk_type: Filter by chunk type

        Returns:
            List of (chunk, relevance_score) tuples
        """
        if not keywords:
            return []

        # Build WHERE clause for filters
        conditions = []
        params = []

        if language:
            conditions.append("language = %s")
            params.append(language)
        if chunk_type:
            conditions.append("chunk_type = %s")
            params.append(chunk_type)

        # Build keyword matching - search in content, class_name, method_name, documentation
        keyword_conditions = []
        for keyword in keywords:
            keyword_lower = keyword.lower()
            keyword_conditions.append(
                "(LOWER(content) LIKE %s OR LOWER(COALESCE(class_name, '')) LIKE %s OR "
                "LOWER(COALESCE(method_name, '')) LIKE %s OR LOWER(COALESCE(documentation, '')) LIKE %s)"
            )
            pattern = f"%{keyword_lower}%"
            params.extend([pattern, pattern, pattern, pattern])

        if keyword_conditions:
            conditions.append(f"({' OR '.join(keyword_conditions)})")

        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""

        # Calculate a simple relevance score based on keyword matches
        # Higher score = more keywords matched
        score_cases = []
        for keyword in keywords:
            keyword_lower = keyword.lower()
            score_cases.append(
                f"CASE WHEN LOWER(content) LIKE %s THEN 1 ELSE 0 END + "
                f"CASE WHEN LOWER(COALESCE(class_name, '')) LIKE %s THEN 2 ELSE 0 END + "
                f"CASE WHEN LOWER(COALESCE(method_name, '')) LIKE %s THEN 2 ELSE 0 END"
            )
            pattern = f"%{keyword_lower}%"
            params.extend([pattern, pattern, pattern])

        score_expression = " + ".join(score_cases) if score_cases else "0"
        max_possible_score = (
            len(keywords) * 5
        )  # 1 for content + 2 for class + 2 for method

        query = f"""
            SELECT
                id, content, language, chunk_type, file_path,
                start_line, end_line, class_name, method_name,
                documentation, "references", metadata,
                ({score_expression})::float / {max_possible_score} as relevance
            FROM {self.table_name}
            {where_clause}
            ORDER BY relevance DESC
            LIMIT %s
        """
        params.append(top_k)

        with self._conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()

        results = []
        for row in rows:
            relevance = row[12]
            if relevance <= 0:
                continue
            references = row[10] if row[10] else []
            metadata = row[11] if row[11] else {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            chunk = CodeChunk(
                id=row[0],
                content=row[1],
                language=row[2],
                chunk_type=row[3],
                file_path=row[4],
                start_line=row[5],
                end_line=row[6],
                class_name=row[7],
                method_name=row[8],
                documentation=row[9],
                references=references,
                metadata=metadata,
            )
            results.append((chunk, relevance))

        return results

    def search_by_class_reference(
        self,
        class_name: str,
        top_k: int = 10,
    ) -> list[CodeChunk]:
        """Find chunks that reference a specific class.

        Args:
            class_name: Class name to search for
            top_k: Maximum results

        Returns:
            List of chunks that reference this class
        """
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    id, content, language, chunk_type, file_path,
                    start_line, end_line, class_name, method_name,
                    documentation, "references", metadata
                FROM {self.table_name}
                WHERE %s = ANY("references")
                LIMIT %s
                """,
                (class_name, top_k),
            )
            rows = cur.fetchall()

        results = []
        for row in rows:
            references = row[10] if row[10] else []
            # Metadata is JSONB, so psycopg3 returns it as a dict already
            metadata = row[11] if row[11] else {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            chunk = CodeChunk(
                id=row[0],
                content=row[1],
                language=row[2],
                chunk_type=row[3],
                file_path=row[4],
                start_line=row[5],
                end_line=row[6],
                class_name=row[7],
                method_name=row[8],
                documentation=row[9],
                references=references,
                metadata=metadata,
            )
            results.append(chunk)

        return results

    def get_class_chunk(self, class_name: str) -> Optional[CodeChunk]:
        """Get the chunk for a specific class.

        Args:
            class_name: Class name to find

        Returns:
            CodeChunk for the class, or None if not found
        """
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    id, content, language, chunk_type, file_path,
                    start_line, end_line, class_name, method_name,
                    documentation, "references", metadata
                FROM {self.table_name}
                WHERE class_name = %s AND chunk_type = 'class'
                LIMIT 1
                """,
                (class_name,),
            )
            row = cur.fetchone()

        if not row:
            return None

        references = row[10] if row[10] else []
        # Metadata is JSONB, so psycopg3 returns it as a dict already
        metadata = row[11] if row[11] else {}
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        return CodeChunk(
            id=row[0],
            content=row[1],
            language=row[2],
            chunk_type=row[3],
            file_path=row[4],
            start_line=row[5],
            end_line=row[6],
            class_name=row[7],
            method_name=row[8],
            documentation=row[9],
            references=references,
            metadata=metadata,
        )

    def get_all_chunks_for_class(self, class_name: str) -> list[CodeChunk]:
        """Get all chunks (class + methods) for a specific class.

        Args:
            class_name: Class name to find

        Returns:
            List of all chunks for this class
        """
        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    id, content, language, chunk_type, file_path,
                    start_line, end_line, class_name, method_name,
                    documentation, "references", metadata
                FROM {self.table_name}
                WHERE class_name = %s
                ORDER BY start_line ASC
                """,
                (class_name,),
            )
            rows = cur.fetchall()

        results = []
        for row in rows:
            references = row[10] if row[10] else []
            # Metadata is JSONB, so psycopg3 returns it as a dict already
            metadata = row[11] if row[11] else {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            chunk = CodeChunk(
                id=row[0],
                content=row[1],
                language=row[2],
                chunk_type=row[3],
                file_path=row[4],
                start_line=row[5],
                end_line=row[6],
                class_name=row[7],
                method_name=row[8],
                documentation=row[9],
                references=references,
                metadata=metadata,
            )
            results.append(chunk)

        return results

    def delete_by_file(self, file_path: str) -> int:
        """Delete all chunks from a specific file.

        Args:
            file_path: File path to delete chunks for

        Returns:
            Number of rows deleted
        """
        with self._conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {self.table_name} WHERE file_path = %s",
                (file_path,),
            )
            deleted = cur.rowcount
            self._conn.commit()
        return deleted

    def delete_by_prefix(self, file_path_prefix: str) -> int:
        """Delete all chunks with file paths matching prefix.

        Args:
            file_path_prefix: File path prefix to match

        Returns:
            Number of rows deleted
        """
        with self._conn.cursor() as cur:
            cur.execute(
                f"DELETE FROM {self.table_name} WHERE file_path LIKE %s",
                (f"{file_path_prefix}%",),
            )
            deleted = cur.rowcount
            self._conn.commit()
        return deleted

    def count(self) -> int:
        """Count total chunks in the store."""
        with self._conn.cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            return cur.fetchone()[0]

    def list_classes(self, language: Optional[str] = None) -> list[CodeChunk]:
        """List all class chunks, optionally filtered by language.

        Args:
            language: Filter by language (e.g., 'java')

        Returns:
            List of CodeChunk objects for classes
        """
        conditions = ["chunk_type = 'class'"]
        params = []

        if language:
            conditions.append("language = %s")
            params.append(language)

        where_clause = "WHERE " + " AND ".join(conditions)

        with self._conn.cursor() as cur:
            cur.execute(
                f"""
                SELECT
                    id, content, language, chunk_type, file_path,
                    start_line, end_line, class_name, method_name,
                    documentation, "references", metadata
                FROM {self.table_name}
                {where_clause}
                ORDER BY language, class_name
                """,
                params,
            )
            rows = cur.fetchall()

        results = []
        for row in rows:
            references = row[10] if row[10] else []
            # Metadata is JSONB, so psycopg3 returns it as a dict already
            metadata = row[11] if row[11] else {}
            if isinstance(metadata, str):
                metadata = json.loads(metadata)

            results.append(
                CodeChunk(
                    id=row[0],
                    content=row[1],
                    language=row[2],
                    chunk_type=row[3],
                    file_path=row[4],
                    start_line=row[5],
                    end_line=row[6],
                    class_name=row[7],
                    method_name=row[8],
                    documentation=row[9],
                    references=references,
                    metadata=metadata,
                )
            )

        return results

    def get_stats(self) -> dict:
        """Get statistics about stored chunks."""
        with self._conn.cursor() as cur:
            # Total count
            cur.execute(f"SELECT COUNT(*) FROM {self.table_name}")
            total = cur.fetchone()[0]

            # By language
            cur.execute(f"""
                SELECT language, COUNT(*)
                FROM {self.table_name}
                GROUP BY language
            """)
            by_language = dict(cur.fetchall())

            # By chunk type
            cur.execute(f"""
                SELECT chunk_type, COUNT(*)
                FROM {self.table_name}
                GROUP BY chunk_type
            """)
            by_type = dict(cur.fetchall())

            # File count
            cur.execute(f"""
                SELECT COUNT(DISTINCT file_path)
                FROM {self.table_name}
            """)
            file_count = cur.fetchone()[0]

        return {
            "total_chunks": total,
            "by_language": by_language,
            "by_type": by_type,
            "file_count": file_count,
        }


def create_store(
    host: str = "localhost",
    port: int = 5432,
    database: str = "codebase_rag",
    user: str = "postgres",
    password: Optional[str] = None,
    embedding_dimensions: int = 768,
) -> PgVectorStore:
    """Factory function to create a vector store.

    Args:
        host: PostgreSQL host
        port: PostgreSQL port
        database: Database name
        user: Database user
        password: Database password
        embedding_dimensions: Dimensions of embedding vectors

    Returns:
        Configured PgVectorStore instance
    """
    return PgVectorStore(
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        embedding_dimensions=embedding_dimensions,
    )
