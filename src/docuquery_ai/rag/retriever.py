from ..db.manager import MultiDatabaseManager
from ..db.models import HybridQuery
from typing import List, Any

class Retriever:
    """
    Retrieves relevant information from the MultiDatabaseManager based on a query.
    """
    def __init__(self, db_manager: MultiDatabaseManager):
        """
        Initializes the Retriever with a MultiDatabaseManager instance.

        Args:
            db_manager: An instance of MultiDatabaseManager for database interactions.
        """
        self.db_manager = db_manager

    async def retrieve(self, query: str, top_k: int = 10) -> List[Any]:
        """
        Performs a retrieval operation based on the given query.

        Args:
            query: The query string.
            top_k: The number of top results to retrieve (currently not used in hybrid_search).

        Returns:
            A list of retrieved results.
        """
        hybrid_query = HybridQuery(text=query)
        return await self.db_manager.hybrid_search(hybrid_query)
