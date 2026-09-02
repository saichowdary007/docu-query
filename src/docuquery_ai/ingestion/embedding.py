from typing import List

try:  # pragma: no cover - optional dependency
    from sentence_transformers import SentenceTransformer
except Exception:  # pragma: no cover - dependency not available
    SentenceTransformer = None


class EmbeddingGenerator:
    """
    Generates vector embeddings for text using a pre-trained SentenceTransformer model.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initializes the generator and loads the underlying model if available."""

        if SentenceTransformer is None:
            self.model = None
        else:
            self.model = SentenceTransformer(model_name)

    async def generate_embeddings(self, text: str) -> List[float]:
        """
        Generates a vector embedding for the given text.

        Args:
            text: The input text string.

        Returns:
            A list of floats representing the embedding vector.
        """
        # In a real async scenario, this might use a non-blocking model or run in a thread pool
        if self.model is None:
            return []
        return self.model.encode(text).tolist()
