from .retriever import Retriever
from .context import ContextAssembler
from .generator import ResponseGenerator
from ..db.manager import MultiDatabaseManager

class RAGProcessor:
    """
    Orchestrates the Retrieval-Augmented Generation (RAG) process.
    It retrieves relevant information, assembles context, and generates a response.
    """
    def __init__(self, db_manager: MultiDatabaseManager):
        """
        Initializes the RAGProcessor with a MultiDatabaseManager instance.

        Args:
            db_manager: An instance of MultiDatabaseManager for database interactions.
        """
        self.retriever = Retriever(db_manager)
        self.context_assembler = ContextAssembler()
        self.response_generator = ResponseGenerator()

    async def process(self, query: str) -> str:
        """
        Executes the RAG pipeline for a given query.

        Args:
            query: The user's query string.

        Returns:
            A string containing the generated response.
        """
        retrieved_results = await self.retriever.retrieve(query)
        context = self.context_assembler.assemble(retrieved_results)
        response = await self.response_generator.generate(query, context)
        return response
