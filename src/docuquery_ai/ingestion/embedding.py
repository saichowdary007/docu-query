try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except Exception:  # pragma: no cover - optional dependency missing
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    SentenceTransformer = None  # type: ignore
from typing import List

class EmbeddingGenerator:
    """
    Generates vector embeddings for text using a pre-trained SentenceTransformer model.
    """
    def __init__(self, model_name: str = 'all-MiniLM-L6-v2'):
        """
        Initializes the EmbeddingGenerator with a specified SentenceTransformer model.

        Args:
            model_name: The name of the SentenceTransformer model to use.
        """
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.model = SentenceTransformer(model_name)
            except Exception:  # pragma: no cover - model download failure
                self.model = None
        else:  # pragma: no cover - fall back in tests
            self.model = None

    async def generate_embeddings(self, text: str) -> List[float]:
        """
        Generates a vector embedding for the given text.

        Args:
            text: The input text string.

        Returns:
            A list of floats representing the embedding vector.
        """
        if self.model is None:
            # Fallback deterministic embedding for tests
            return [0.0]
        # In a real async scenario, this might use a non-blocking model or run in a thread pool
        return self.model.encode(text).tolist()
