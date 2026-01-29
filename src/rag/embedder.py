"""Vertex AI embeddings for code chunks."""

from typing import Optional

from google import genai
from tqdm import tqdm

from .chunker import CodeChunk


class VertexEmbedder:
    """Generate embeddings using Vertex AI."""

    # Embedding dimensions by model
    MODEL_DIMENSIONS = {
        "text-embedding-005": 768,
        "text-embedding-004": 768,
        "text-multilingual-embedding-002": 768,
    }

    def __init__(
        self,
        project_id: str,
        location: str = "us-central1",
        model: str = "text-embedding-005",
    ):
        """Initialize the embedder.

        Args:
            project_id: GCP project ID
            location: GCP region
            model: Embedding model name
        """
        self.project_id = project_id
        self.location = location
        self.model = model
        self.dimensions = self.MODEL_DIMENSIONS.get(model, 768)

        self.client = genai.Client(
            vertexai=True,
            project=project_id,
            location=location,
        )

    def embed_text(self, text: str) -> list[float]:
        """Embed a single text string.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        response = self.client.models.embed_content(
            model=self.model,
            contents=text,
        )
        return response.embeddings[0].values

    def embed_texts(
        self,
        texts: list[str],
        batch_size: int = 100,
        show_progress: bool = True,
    ) -> list[list[float]]:
        """Embed multiple texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call
            show_progress: Show progress bar

        Returns:
            List of embedding vectors
        """
        embeddings = []
        batches = [texts[i : i + batch_size] for i in range(0, len(texts), batch_size)]

        iterator = tqdm(batches, desc="Embedding") if show_progress else batches

        for batch in iterator:
            response = self.client.models.embed_content(
                model=self.model,
                contents=batch,
            )
            for embedding in response.embeddings:
                embeddings.append(embedding.values)

        return embeddings

    def embed_chunks(
        self,
        chunks: list[CodeChunk],
        batch_size: int = 100,
        show_progress: bool = True,
    ) -> list[tuple[CodeChunk, list[float]]]:
        """Embed code chunks.

        Args:
            chunks: List of code chunks to embed
            batch_size: Number of chunks per API call
            show_progress: Show progress bar

        Returns:
            List of (chunk, embedding) tuples
        """
        # Build text representations for embedding
        texts = [self._chunk_to_text(chunk) for chunk in chunks]

        # Get embeddings
        embeddings = self.embed_texts(texts, batch_size, show_progress)

        # Pair chunks with embeddings
        return list(zip(chunks, embeddings))

    def _chunk_to_text(self, chunk: CodeChunk) -> str:
        """Convert a chunk to text for embedding.

        Includes metadata to improve semantic search quality.
        """
        parts = []

        # Add context
        parts.append(f"Language: {chunk.language}")
        parts.append(f"Type: {chunk.chunk_type}")

        if chunk.class_name:
            parts.append(f"Class: {chunk.class_name}")
        if chunk.method_name:
            parts.append(f"Method: {chunk.method_name}")

        # Add documentation if available
        if chunk.documentation:
            parts.append(f"Documentation: {chunk.documentation}")

        # Add the code
        parts.append(f"Code:\n{chunk.content}")

        return "\n".join(parts)


def create_embedder(
    project_id: str,
    location: str = "us-central1",
    model: str = "text-embedding-005",
) -> VertexEmbedder:
    """Factory function to create an embedder.

    Args:
        project_id: GCP project ID
        location: GCP region
        model: Embedding model name

    Returns:
        Configured VertexEmbedder instance
    """
    return VertexEmbedder(
        project_id=project_id,
        location=location,
        model=model,
    )
