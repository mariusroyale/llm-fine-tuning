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

    def format_sources(self) -> str:
        """Format sources for display."""
        lines = []
        for i, (chunk, score) in enumerate(zip(self.sources, self.scores), 1):
            location = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
            name = chunk.method_name or chunk.class_name or chunk.file_path
            lines.append(f"{i}. {name} ({location}) [score: {score:.3f}]")
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
    ) -> RAGResponse:
        """Query the codebase and generate an answer.

        Args:
            question: User's question
            top_k: Number of chunks to retrieve
            language: Filter by language
            chunk_type: Filter by chunk type
            include_sources: Include source chunks in response

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

        # Build context from chunks
        context = self._build_context(chunks)

        # Generate answer
        answer = self._generate_answer(question, context)

        return RAGResponse(
            answer=answer,
            sources=chunks if include_sources else [],
            scores=scores,
            query=question,
            model=self.llm_model,
        )

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

    def _build_context(self, chunks: list[CodeChunk]) -> str:
        """Build context string from retrieved chunks."""
        context_parts = []

        for i, chunk in enumerate(chunks, 1):
            location = f"{chunk.file_path}:{chunk.start_line}-{chunk.end_line}"
            header = f"--- Code Snippet {i} ({location}) ---"

            if chunk.documentation:
                header += f"\nDocumentation: {chunk.documentation}"

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
