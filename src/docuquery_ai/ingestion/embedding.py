from typing import List

from sentence_transformers import SentenceTransformer


class EmbeddingGenerator:
    """
    Generates vector embeddings for text using a pre-trained SentenceTransformer model.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initializes the EmbeddingGenerator with a specified SentenceTransformer model.

        Args:
            model_name: The name of the SentenceTransformer model to use.
        """
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
        return self.model.encode(text).tolist()
