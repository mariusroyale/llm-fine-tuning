"""RAG retriever for codebase queries."""

from dataclasses import dataclass, field
from typing import Optional

from google import genai

from .chunker import CodeChunk
from .embedder import VertexEmbedder
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
        top_k: int = 5,
        language: Optional[str] = None,
        chunk_type: Optional[str] = None,
        include_sources: bool = True,
        include_dependencies: bool = False,
        max_dependencies: int = 3,
    ) -> RAGResponse:
        """Query the codebase and generate an answer.

        Args:
            question: User's question
            top_k: Number of chunks to retrieve
            language: Filter by language
            chunk_type: Filter by chunk type
            include_sources: Include source chunks in response
            include_dependencies: Fetch and include class dependencies
            max_dependencies: Maximum dependencies per source chunk

        Returns:
            RAGResponse with answer and sources
        """
        # Embed the question
        query_embedding = self.embedder.embed_text(question)

        # Retrieve relevant chunks
        results = self.store.search(
            query_embedding=query_embedding,
            top_k=top_k,
            language=language,
            chunk_type=chunk_type,
        )

        chunks = [chunk for chunk, _ in results]
        scores = [score for _, score in results]

        # Optionally fetch dependencies
        dependencies = []
        if include_dependencies:
            dependencies = self._fetch_dependencies(chunks, max_dependencies)

        # Build context from chunks and dependencies
        context = self._build_context(chunks, dependencies)

        # Generate answer
        answer = self._generate_answer(question, context)

        return RAGResponse(
            answer=answer,
            sources=chunks if include_sources else [],
            scores=scores,
            query=question,
            model=self.llm_model,
            dependencies=dependencies if include_sources else [],
        )

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

    def _generate_answer(self, question: str, context: str) -> str:
        """Generate an answer using the LLM."""
        prompt = f"""Based on the following code snippets from the codebase, answer the question.

{context}

---

Question: {question}

Answer:"""

        response = self.client.models.generate_content(
            model=self.llm_model,
            contents=prompt,
            config={
                "system_instruction": self.system_prompt,
                "temperature": 0.3,
                "max_output_tokens": 2048,
            },
        )

        return response.text


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
