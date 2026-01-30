"""RAG retriever for codebase queries."""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from google import genai

from .chunker import CodeChunk
from .embedder import VertexEmbedder
from .query_analyzer import (
    QueryAnalysis,
    QueryIntent,
    analyze_query,
    get_keywords_for_search,
)
from .vector_store import PgVectorStore


@dataclass
class RAGResponse:
    """Response from a RAG query."""

    answer: str
    sources: list[CodeChunk]
    scores: list[float]
    query: str
    model: str
    dependencies: list[CodeChunk] = field(default_factory=list)
    query_analysis: Optional[QueryAnalysis] = None

    def format_sources(self) -> str:
        """Format sources for display."""
        lines = []
        for i, (chunk, score) in enumerate(zip(self.sources, self.scores), 1):
            location = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
            name = chunk.method_name or chunk.class_name or chunk.file_path
            lines.append(f"{i}. {name} ({location}) [score: {score:.3f}]")

        if self.dependencies:
            lines.append("\nRelated dependencies:")
            for i, chunk in enumerate(self.dependencies, 1):
                location = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
                name = chunk.class_name or chunk.file_path
                lines.append(f"  {i}. {name} ({location})")

        return "\n".join(lines)


class CodeRetriever:
    """Retrieve relevant code and generate answers using RAG."""

    DEFAULT_SYSTEM_PROMPT = """You are an expert software engineer assistant. Your task is to answer questions about a codebase using the provided code snippets as context.

Guidelines:
- Answer based ONLY on the provided code snippets
- If the answer is not in the provided code, say so clearly
- Include specific file paths and line numbers when referencing code
- Provide code snippets in your answer when relevant
- Be concise but thorough"""

    def __init__(
        self,
        embedder: VertexEmbedder,
        store: PgVectorStore,
        llm_model: str = "gemini-2.5-pro",
        system_prompt: Optional[str] = None,
    ):
        """Initialize the retriever.

        Args:
            embedder: Embedder for query vectors
            store: Vector store for chunk retrieval
            llm_model: Model for answer generation
            system_prompt: Custom system prompt
        """
        self.embedder = embedder
        self.store = store
        self.llm_model = llm_model
        self.system_prompt = system_prompt or self.DEFAULT_SYSTEM_PROMPT

        self.client = genai.Client(
            vertexai=True,
            project=embedder.project_id,
            location=embedder.location,
        )

    def query(
        self,
        question: str,
        top_k: Optional[int] = None,
        language: Optional[str] = None,
        chunk_type: Optional[str] = None,
        include_sources: bool = True,
        include_dependencies: Optional[bool] = None,
        max_dependencies: int = 3,
        use_hybrid_search: bool = True,
        min_similarity: Optional[float] = None,
    ) -> RAGResponse:
        """Query the codebase and generate an answer.

        Uses intelligent query analysis to automatically determine:
        - Query intent (definition, explanation, list, usage, etc.)
        - Optimal number of results (top_k)
        - Similarity threshold
        - Whether to include dependencies
        - Chunk type filtering

        Args:
            question: User's question
            top_k: Number of chunks to retrieve (auto-determined if None)
            language: Filter by language
            chunk_type: Filter by chunk type (auto-determined if None)
            include_sources: Include source chunks in response
            include_dependencies: Fetch dependencies (auto-determined if None)
            max_dependencies: Maximum dependencies per source chunk
            use_hybrid_search: Combine semantic and keyword search for better accuracy
            min_similarity: Minimum similarity threshold (auto-determined if None)

        Returns:
            RAGResponse with answer and sources
        """
        # Analyze the query to determine intent and extract information
        analysis = analyze_query(question)
        print(f"[DEBUG] Query intent: {analysis.intent.value}", file=sys.stderr)
        print(f"[DEBUG] Class names: {analysis.class_names}", file=sys.stderr)
        print(f"[DEBUG] Primary terms: {analysis.primary_terms}", file=sys.stderr)
        if analysis.expanded_terms:
            print(
                f"[DEBUG] Expanded terms: {analysis.expanded_terms[:5]}",
                file=sys.stderr,
            )

        # Use analysis recommendations if not explicitly provided
        if top_k is None:
            top_k = analysis.suggested_top_k
        if min_similarity is None:
            min_similarity = analysis.min_similarity
        if include_dependencies is None:
            include_dependencies = analysis.include_dependencies
        if chunk_type is None:
            chunk_type = analysis.chunk_type_filter

        print(
            f"[DEBUG] Using top_k={top_k}, min_similarity={min_similarity}, "
            f"include_deps={include_dependencies}, chunk_type={chunk_type}",
            file=sys.stderr,
        )

        question_lower = question.lower()
        is_list_count_query = analysis.intent == QueryIntent.LIST_COUNT
        is_class_query = chunk_type == "class" or any(
            keyword in question_lower for keyword in ["class", "classes"]
        )
        is_schema_query = analysis.intent == QueryIntent.SCHEMA

        # Try to find specific classes directly
        direct_class_chunk = None
        all_class_chunks = None
        if analysis.class_names:
            for class_name in analysis.class_names:
                direct_class_chunk = self.store.get_class_chunk(class_name)
                if direct_class_chunk:
                    print(
                        f"[DEBUG] Found direct class match: {class_name}",
                        file=sys.stderr,
                    )
                    if is_schema_query:
                        all_class_chunks = self.store.get_all_chunks_for_class(
                            class_name
                        )
                        print(
                            f"[DEBUG] Schema query. Retrieved {len(all_class_chunks)} chunks",
                            file=sys.stderr,
                        )
                    break

        # If asking to list/count classes, get ALL classes from database
        all_classes_list = None
        if is_list_count_query and is_class_query:
            all_classes = self.store.list_classes(language=language)
            if all_classes:
                all_classes_list = all_classes
                print(
                    f"[DEBUG] List query. Found {len(all_classes)} classes.",
                    file=sys.stderr,
                )

        # Perform hybrid search: combine semantic and keyword search
        chunks, scores = self._hybrid_search(
            question=question,
            analysis=analysis,
            top_k=top_k,
            language=language,
            chunk_type=chunk_type,
            min_similarity=min_similarity,
            use_hybrid=use_hybrid_search,
        )

        # If we found a direct class match, prioritize it
        if direct_class_chunk:
            if is_schema_query and all_class_chunks:
                chunks = all_class_chunks
                scores = [1.0] * len(chunks)
                print(
                    f"[DEBUG] Using all {len(chunks)} chunks for schema",
                    file=sys.stderr,
                )
            else:
                chunks = [c for c in chunks if c.id != direct_class_chunk.id]
                scores = scores[: len(chunks)]
                chunks.insert(0, direct_class_chunk)
                scores.insert(0, 1.0)

        # Optionally fetch dependencies
        dependencies = []
        if include_dependencies:
            dependencies = self._fetch_dependencies(chunks, max_dependencies)

        # Build context from chunks and dependencies
        context = self._build_context(chunks, dependencies)

        # For list/count queries, use ONLY the complete list
        if is_list_count_query and is_class_query and all_classes_list:
            class_summaries = []
            for cls in sorted(
                all_classes_list, key=lambda c: c.class_name or c.file_path
            ):
                class_name = cls.class_name or Path(cls.file_path).stem
                location = f"{cls.file_path}:{cls.start_line}-{cls.end_line}"
                class_summaries.append(f"{class_name} ({location})")

            context = f"""DATABASE QUERY RESULT - ALL {len(all_classes_list)} INDEXED CLASSES

This is a direct database query result showing ALL classes indexed in the system.

{chr(10).join(f"{i + 1}. {cls}" for i, cls in enumerate(class_summaries))}

Total: {len(all_classes_list)} classes."""

            print(
                f"[DEBUG] Using ONLY complete list ({len(all_classes_list)} classes).",
                file=sys.stderr,
            )

        # Generate answer using LLM
        answer = self._generate_answer(
            question, context, is_list_query=(is_list_count_query and is_class_query)
        )

        return RAGResponse(
            answer=answer,
            sources=chunks if include_sources else [],
            scores=scores,
            query=question,
            model=self.llm_model,
            dependencies=dependencies if include_sources else [],
            query_analysis=analysis,
        )

    def _hybrid_search(
        self,
        question: str,
        analysis: QueryAnalysis,
        top_k: int,
        language: Optional[str],
        chunk_type: Optional[str],
        min_similarity: float,
        use_hybrid: bool = True,
    ) -> tuple[list[CodeChunk], list[float]]:
        """Perform hybrid search combining semantic and keyword search.

        Uses Reciprocal Rank Fusion (RRF) to merge results from both
        search methods, providing better accuracy than either alone.

        Args:
            question: Original question
            analysis: Query analysis results
            top_k: Number of results to return
            language: Language filter
            chunk_type: Chunk type filter
            min_similarity: Minimum similarity threshold
            use_hybrid: Whether to use hybrid search

        Returns:
            Tuple of (chunks, scores)
        """
        # Semantic search - embed the question
        query_embedding = self.embedder.embed_text(question)

        # Fetch more candidates for hybrid merging
        semantic_top_k = top_k * 2 if use_hybrid else top_k

        semantic_results = self.store.search(
            query_embedding=query_embedding,
            top_k=semantic_top_k,
            language=language,
            chunk_type=chunk_type,
            min_similarity=min_similarity,
        )

        print(
            f"[DEBUG] Semantic search: {len(semantic_results)} results "
            f"(threshold={min_similarity})",
            file=sys.stderr,
        )

        if not use_hybrid:
            chunks = [chunk for chunk, _ in semantic_results[:top_k]]
            scores = [score for _, score in semantic_results[:top_k]]
            return chunks, scores

        # Keyword search using extracted and expanded terms
        keywords = get_keywords_for_search(analysis)
        all_keywords = keywords + analysis.expanded_terms[:5]

        keyword_results = self.store.keyword_search(
            keywords=all_keywords,
            top_k=top_k,
            language=language,
            chunk_type=chunk_type,
        )

        print(
            f"[DEBUG] Keyword search: {len(keyword_results)} results "
            f"for {len(all_keywords)} keywords",
            file=sys.stderr,
        )

        # Merge results using Reciprocal Rank Fusion (RRF)
        merged = self._merge_results_rrf(
            semantic_results=semantic_results,
            keyword_results=keyword_results,
            top_k=top_k,
        )

        print(f"[DEBUG] Merged results: {len(merged)} chunks", file=sys.stderr)

        chunks = [chunk for chunk, _ in merged]
        scores = [score for _, score in merged]

        return chunks, scores

    def _merge_results_rrf(
        self,
        semantic_results: list[tuple[CodeChunk, float]],
        keyword_results: list[tuple[CodeChunk, float]],
        top_k: int,
        k: int = 60,
    ) -> list[tuple[CodeChunk, float]]:
        """Merge results using Reciprocal Rank Fusion.

        RRF score = sum(1 / (k + rank)) for each result list.
        This method is effective at combining results from different
        ranking systems without needing score normalization.

        Args:
            semantic_results: Results from semantic search
            keyword_results: Results from keyword search
            top_k: Number of results to return
            k: RRF constant (higher = less aggressive ranking)

        Returns:
            Merged list of (chunk, score) tuples
        """
        chunk_scores: dict[str, tuple[CodeChunk, float]] = {}

        # Score semantic results
        for rank, (chunk, _) in enumerate(semantic_results):
            rrf_score = 1.0 / (k + rank + 1)
            if chunk.id in chunk_scores:
                existing_chunk, existing_score = chunk_scores[chunk.id]
                chunk_scores[chunk.id] = (existing_chunk, existing_score + rrf_score)
            else:
                chunk_scores[chunk.id] = (chunk, rrf_score)

        # Score keyword results (with slight boost for exact matches)
        for rank, (chunk, _) in enumerate(keyword_results):
            rrf_score = 1.0 / (k + rank + 1) * 1.1  # 10% boost for keyword matches
            if chunk.id in chunk_scores:
                existing_chunk, existing_score = chunk_scores[chunk.id]
                chunk_scores[chunk.id] = (existing_chunk, existing_score + rrf_score)
            else:
                chunk_scores[chunk.id] = (chunk, rrf_score)

        # Sort by combined score
        sorted_results = sorted(
            chunk_scores.values(),
            key=lambda x: x[1],
            reverse=True,
        )

        # Normalize scores to 0-1 range
        if sorted_results:
            max_score = sorted_results[0][1]
            sorted_results = [
                (chunk, score / max_score) for chunk, score in sorted_results
            ]

        return sorted_results[:top_k]

    def query_with_dependencies(
        self,
        question: str,
        top_k: int = 5,
        max_dependencies: int = 5,
    ) -> RAGResponse:
        """Query with automatic dependency resolution.

        This is a convenience method that enables dependency-aware retrieval,
        useful for questions about templates, schemas, or code that references
        other classes.

        Args:
            question: User's question
            top_k: Number of chunks to retrieve
            max_dependencies: Maximum dependencies to include

        Returns:
            RAGResponse with answer, sources, and dependencies
        """
        return self.query(
            question=question,
            top_k=top_k,
            include_dependencies=True,
            max_dependencies=max_dependencies,
        )

    def query_class_with_context(
        self,
        class_name: str,
        include_referencing: bool = True,
        include_referenced: bool = True,
    ) -> RAGResponse:
        """Query for a specific class with full dependency context.

        Args:
            class_name: Class name to look up
            include_referencing: Include chunks that reference this class
            include_referenced: Include classes this class references

        Returns:
            RAGResponse with class context
        """
        # Get the class chunk
        class_chunk = self.store.get_class_chunk(class_name)
        if not class_chunk:
            return RAGResponse(
                answer=f"Class `{class_name}` not found in the codebase.",
                sources=[],
                scores=[],
                query=f"Lookup: {class_name}",
                model=self.llm_model,
                dependencies=[],
            )

        sources = [class_chunk]
        scores = [1.0]
        dependencies = []

        # Get chunks that reference this class (e.g., templates)
        if include_referencing:
            referencing = self.store.search_by_class_reference(class_name, top_k=5)
            for chunk in referencing:
                if chunk.id != class_chunk.id:
                    dependencies.append(chunk)

        # Get classes that this class references
        if include_referenced and class_chunk.references:
            for ref_class in class_chunk.references[:5]:
                ref_chunk = self.store.get_class_chunk(ref_class)
                if ref_chunk and ref_chunk.id != class_chunk.id:
                    dependencies.append(ref_chunk)

        # Build context
        context = self._build_context(sources, dependencies)

        # Generate comprehensive answer
        question = f"Describe the {class_name} class, its purpose, and its relationships with other code."
        answer = self._generate_answer(question, context)

        return RAGResponse(
            answer=answer,
            sources=sources,
            scores=scores,
            query=f"Class lookup: {class_name}",
            model=self.llm_model,
            dependencies=dependencies,
        )

    def find_template_dependencies(
        self,
        template_path: str,
    ) -> RAGResponse:
        """Find all Java classes referenced by a template.

        Args:
            template_path: Path to the template file

        Returns:
            RAGResponse with the template and its Java dependencies
        """
        # Search for the template chunk
        query_embedding = self.embedder.embed_text(f"template {template_path}")
        results = self.store.search(
            query_embedding=query_embedding,
            top_k=1,
            chunk_type="template",
        )

        if not results:
            return RAGResponse(
                answer=f"Template not found: {template_path}",
                sources=[],
                scores=[],
                query=f"Template lookup: {template_path}",
                model=self.llm_model,
                dependencies=[],
            )

        template_chunk, score = results[0]
        dependencies = []

        # Get all referenced classes
        if template_chunk.references:
            for class_name in template_chunk.references:
                class_chunk = self.store.get_class_chunk(class_name)
                if class_chunk:
                    dependencies.append(class_chunk)

        # Build context
        context = self._build_context([template_chunk], dependencies)

        # Generate answer
        question = f"Explain the template and its Java class dependencies."
        answer = self._generate_answer(question, context)

        return RAGResponse(
            answer=answer,
            sources=[template_chunk],
            scores=[score],
            query=f"Template dependencies: {template_path}",
            model=self.llm_model,
            dependencies=dependencies,
        )

    def _fetch_dependencies(
        self,
        chunks: list[CodeChunk],
        max_per_chunk: int = 3,
    ) -> list[CodeChunk]:
        """Fetch dependencies for a list of chunks.

        Args:
            chunks: Source chunks to find dependencies for
            max_per_chunk: Maximum dependencies per chunk

        Returns:
            List of dependency chunks (deduplicated)
        """
        seen_ids = {c.id for c in chunks}
        dependencies = []

        for chunk in chunks:
            # Get classes referenced by this chunk
            if chunk.references:
                for class_name in chunk.references[:max_per_chunk]:
                    dep_chunk = self.store.get_class_chunk(class_name)
                    if dep_chunk and dep_chunk.id not in seen_ids:
                        dependencies.append(dep_chunk)
                        seen_ids.add(dep_chunk.id)

            # For templates/documents, also find what references them
            if chunk.chunk_type in ("template", "document") and chunk.class_name:
                referencing = self.store.search_by_class_reference(
                    chunk.class_name, top_k=max_per_chunk
                )
                for ref_chunk in referencing:
                    if ref_chunk.id not in seen_ids:
                        dependencies.append(ref_chunk)
                        seen_ids.add(ref_chunk.id)

        return dependencies

    def retrieve_only(
        self,
        question: str,
        top_k: int = 10,
        language: Optional[str] = None,
        chunk_type: Optional[str] = None,
    ) -> list[tuple[CodeChunk, float]]:
        """Retrieve relevant chunks without generating an answer.

        Args:
            question: User's question
            top_k: Number of chunks to retrieve
            language: Filter by language
            chunk_type: Filter by chunk type

        Returns:
            List of (chunk, score) tuples
        """
        query_embedding = self.embedder.embed_text(question)

        return self.store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            language=language,
            chunk_type=chunk_type,
        )

    def _build_context(
        self,
        chunks: list[CodeChunk],
        dependencies: Optional[list[CodeChunk]] = None,
    ) -> str:
        """Build context string from retrieved chunks and dependencies."""
        context_parts = []

        # Main chunks
        for i, chunk in enumerate(chunks, 1):
            location = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
            header = f"--- Code Snippet {i} ({location}) ---"

            if chunk.documentation:
                header += f"\nDocumentation: {chunk.documentation}"

            if chunk.references:
                header += f"\nReferences: {', '.join(chunk.references[:5])}"

            context_parts.append(
                f"{header}\n\n```{chunk.language}\n{chunk.content}\n```"
            )

        # Dependencies section
        if dependencies:
            context_parts.append("\n--- Related Dependencies ---\n")
            for i, chunk in enumerate(dependencies, 1):
                location = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
                chunk_type = chunk.chunk_type or "code"
                header = f"--- Dependency {i}: {chunk.class_name or chunk.file_path} ({chunk_type}) ---"
                header += f"\nLocation: {location}"

                context_parts.append(
                    f"{header}\n\n```{chunk.language}\n{chunk.content}\n```"
                )

        return "\n\n".join(context_parts)

    def _generate_answer(
        self, question: str, context: str, is_list_query: bool = False
    ) -> str:
        """Generate an answer using the LLM."""
        # Check if context contains a complete class list
        has_complete_list = "DATABASE QUERY RESULT" in context or is_list_query

        if has_complete_list or is_list_query:
            # Extract the count from the context
            count_match = re.search(r"ALL (\d+) INDEXED CLASSES", context)
            total_count = count_match.group(1) if count_match else "all"

            # Override system prompt for list queries - make it crystal clear
            system_instruction = f"""You are answering a question about which classes are indexed in a codebase.

The context provided is a DIRECT DATABASE QUERY RESULT showing ALL {total_count} classes that are indexed. This is NOT code snippets - this is the complete database record.

Your task:
- List ALL {total_count} classes from the database query result
- Do NOT say "I can only see X classes" - you have ALL {total_count} classes
- Do NOT reference "code snippets" - this is a database query result
- Provide a complete, numbered list of all classes"""

            prompt = f"""You have been given a database query result showing all indexed classes:

{context}

---

Question: {question}

Answer by listing ALL classes from the database query result above. This is a complete list - use all of it."""
        else:
            system_instruction = self.system_prompt
            prompt = f"""Based on the following code snippets from the codebase, answer the question.

{context}

---

Question: {question}

Answer:"""

        print(f"[DEBUG] Calling LLM ({self.llm_model}) with prompt length: {len(prompt)} chars", file=sys.stderr)
        print(f"[DEBUG] Context length: {len(context)} chars", file=sys.stderr)
        
        try:
            response = self.client.models.generate_content(
                model=self.llm_model,
                contents=prompt,
                config={
                    "system_instruction": system_instruction,
                    "temperature": 0.3,
                    "max_output_tokens": 8192,  # Increased to allow full class listings
                },
            )
            
            answer_text = response.text
            print(f"[DEBUG] LLM response received, length: {len(answer_text)} chars", file=sys.stderr)
            return answer_text
        except Exception as e:
            print(f"[ERROR] LLM call failed: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc(file=sys.stderr)
            raise


class InteractiveRetriever:
    """Interactive RAG session with conversation history."""

    def __init__(
        self,
        retriever: CodeRetriever,
        max_history: int = 10,
    ):
        """Initialize interactive session.

        Args:
            retriever: Base retriever
            max_history: Maximum conversation turns to keep
        """
        self.retriever = retriever
        self.max_history = max_history
        self.history: list[dict] = []

    def query(
        self,
        question: str,
        top_k: int = 5,
    ) -> RAGResponse:
        """Query with conversation context.

        Args:
            question: User's question
            top_k: Number of chunks to retrieve

        Returns:
            RAGResponse with answer and sources
        """
        # Add conversation context to retrieval
        enhanced_question = self._enhance_question(question)

        # Get response
        response = self.retriever.query(enhanced_question, top_k=top_k)

        # Update history
        self.history.append(
            {
                "role": "user",
                "content": question,
            }
        )
        self.history.append(
            {
                "role": "assistant",
                "content": response.answer,
            }
        )

        # Trim history if needed
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2 :]

        return response

    def _enhance_question(self, question: str) -> str:
        """Enhance question with conversation context."""
        if not self.history:
            return question

        # Add recent context
        recent = self.history[-4:]  # Last 2 exchanges
        context_parts = []

        for entry in recent:
            role = "User" if entry["role"] == "user" else "Assistant"
            context_parts.append(f"{role}: {entry['content'][:200]}...")

        context = "\n".join(context_parts)
        return f"Previous conversation:\n{context}\n\nCurrent question: {question}"

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.history = []


def create_retriever(
    project_id: str,
    location: str = "us-central1",
    embedding_model: str = "text-embedding-005",
    llm_model: str = "gemini-2.5-pro",
    db_host: str = "localhost",
    db_port: int = 5432,
    db_name: str = "codebase_rag",
    db_user: str = "postgres",
    db_password: Optional[str] = None,
    system_prompt: Optional[str] = None,
) -> CodeRetriever:
    """Factory function to create a configured retriever.

    Args:
        project_id: GCP project ID
        location: GCP region
        embedding_model: Embedding model name
        llm_model: LLM model for generation
        db_host: PostgreSQL host
        db_port: PostgreSQL port
        db_name: Database name
        db_user: Database user
        db_password: Database password
        system_prompt: Custom system prompt

    Returns:
        Configured CodeRetriever instance
    """
    embedder = VertexEmbedder(
        project_id=project_id,
        location=location,
        model=embedding_model,
    )

    store = PgVectorStore(
        host=db_host,
        port=db_port,
        database=db_name,
        user=db_user,
        password=db_password,
        embedding_dimensions=embedder.dimensions,
    )
    store.connect()

    return CodeRetriever(
        embedder=embedder,
        store=store,
        llm_model=llm_model,
        system_prompt=system_prompt,
    )
