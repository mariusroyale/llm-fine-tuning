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
    
    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Estimate token count for a text.
        
        Uses conservative estimate: ~2 characters per token for code/JSON.
        This is more accurate for code than the typical 4 chars/token.
        """
        return int(len(text) / 2)

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
        max_tokens_per_batch: int = 15000,  # Conservative limit (API limit is 20k)
    ) -> list[list[float]]:
        """Embed multiple texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Maximum number of texts per API call (may be reduced if token limit hit)
            show_progress: Show progress bar
            max_tokens_per_batch: Maximum tokens per batch (default 15k, API limit is 20k)

        Returns:
            List of embedding vectors
        """
        embeddings = []
        
        # Build batches respecting token limits
        batches = []
        current_batch = []
        current_tokens = 0
        skipped_count = 0
        
        for text in texts:
            text_tokens = self._estimate_tokens(text)
            
            # If single text exceeds limit, skip it with a warning
            if text_tokens > max_tokens_per_batch:
                skipped_count += 1
                embeddings.append(None)  # Placeholder for skipped item
                continue
            
            # Check if adding this text would exceed the limit
            if current_batch and (current_tokens + text_tokens > max_tokens_per_batch):
                # Start a new batch
                batches.append(current_batch)
                current_batch = [text]
                current_tokens = text_tokens
            else:
                # Add to current batch
                current_batch.append(text)
                current_tokens += text_tokens
                
                # If batch is full by count, check token limit before adding more
                if len(current_batch) >= batch_size:
                    batches.append(current_batch)
                    current_batch = []
                    current_tokens = 0
        
        # Add remaining batch
        if current_batch:
            batches.append(current_batch)
        
        if skipped_count > 0:
            import warnings
            warnings.warn(
                f"Skipped {skipped_count} texts that exceeded token limit of {max_tokens_per_batch}"
            )

        iterator = tqdm(batches, desc="Embedding") if show_progress else batches

        for batch in iterator:
            try:
                response = self.client.models.embed_content(
                    model=self.model,
                    contents=batch,
                )
                for embedding in response.embeddings:
                    embeddings.append(embedding.values)
            except Exception as e:
                # If batch fails due to token limit, process individually
                error_msg = str(e).lower()
                if "token count" in error_msg or "20000" in error_msg or "invalid_argument" in error_msg:
                    import warnings
                    warnings.warn(
                        f"Batch of {len(batch)} items exceeded token limit, processing individually"
                    )
                    for text in batch:
                        try:
                            # Check if individual text is too large
                            if self._estimate_tokens(text) > max_tokens_per_batch:
                                warnings.warn(f"Skipping text with estimated {self._estimate_tokens(text)} tokens")
                                embeddings.append(None)
                                continue
                            
                            response = self.client.models.embed_content(
                                model=self.model,
                                contents=[text],
                            )
                            embeddings.append(response.embeddings[0].values)
                        except Exception as e2:
                            # Track the specific error for reporting
                            error_msg = str(e2).lower()
                            if "token count" in error_msg or "20000" in error_msg:
                                # Still too large even individually
                                token_est = self._estimate_tokens(text)
                                embeddings.append(None)  # Will be tracked as skipped
                            else:
                                # Other API error
                                import warnings
                                warnings.warn(f"Failed to embed individual text: {e2}")
                                embeddings.append(None)
                else:
                    raise

        return embeddings

    def embed_chunks(
        self,
        chunks: list[CodeChunk],
        batch_size: int = 100,
        show_progress: bool = True,
    ) -> tuple[list[tuple[CodeChunk, list[float]]], list[dict]]:
        """Embed code chunks.

        Args:
            chunks: List of code chunks to embed
            batch_size: Maximum number of chunks per API call (may be reduced if token limit hit)
            show_progress: Show progress bar

        Returns:
            Tuple of:
            - List of (chunk, embedding) tuples for successfully embedded chunks
            - List of dicts with skipped chunk info: {'chunk': CodeChunk, 'reason': str, 'token_count': int}
        """
        # Build text representations for embedding
        texts = [self._chunk_to_text(chunk) for chunk in chunks]
        
        max_tokens_per_batch = 15000

        # Get embeddings (will handle token limits automatically)
        embeddings = self.embed_texts(texts, batch_size, show_progress)

        # Pair chunks with embeddings, tracking skipped ones
        result = []
        skipped = []
        
        for chunk, text, embedding in zip(chunks, texts, embeddings):
            if embedding is not None:
                result.append((chunk, embedding))
            else:
                # Chunk was skipped - determine why
                token_count = self._estimate_tokens(text)
                if token_count > max_tokens_per_batch:
                    reason = f"Exceeds token limit ({token_count:,} tokens > {max_tokens_per_batch:,} limit)"
                else:
                    reason = "Failed during embedding (API error or token estimation mismatch)"
                
                skipped.append({
                    'chunk': chunk,
                    'reason': reason,
                    'token_count': token_count,
                    'file_path': str(chunk.file_path),
                    'chunk_type': chunk.chunk_type,
                    'size_chars': len(text),
                    'size_lines': chunk.end_line - chunk.start_line + 1 if chunk.start_line and chunk.end_line else None,
                })
        
        return result, skipped

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
