import logging
from typing import Any, List

from docuquery_ai.exceptions import QueryError

from ..db.models import HybridQuery
from .aggregator import ResultAggregator
from .cache import QueryCache

logger = logging.getLogger(__name__)


class QueryEngine:
    """
    Orchestrates multi-database queries, aggregates results, and manages caching.
    """

    def __init__(self):
        """
        Initializes the QueryEngine with a ResultAggregator and QueryCache.
        """
        self.aggregator = ResultAggregator()
        self.cache = QueryCache()
        # These will be set by MultiDatabaseManager
        self.relational_db = None
        self.vector_db = None
        self.graph_db = None
        self.knowledge_graph_db = None

    def set_db_managers(self, relational_db, vector_db, graph_db, knowledge_graph_db):
        self.relational_db = relational_db
        self.vector_db = vector_db
        self.graph_db = graph_db
        self.knowledge_graph_db = knowledge_graph_db

    async def execute_query(self, query: HybridQuery) -> List[Any]:
        """
        Executes a hybrid query across multiple database paradigms.

        Args:
            query: An instance of HybridQuery specifying the search parameters.

        Returns:
            A list of aggregated and potentially cached search results.
        """
        try:
            cached_result = self.cache.get(str(query))
            if cached_result:
                logger.info(f"Cache hit for query: {query.text}")
                return cached_result

            logger.info(f"Executing hybrid query: {query.text}")
            results = []

            if not query.databases or "relational" in query.databases:
                if self.relational_db:
                    logger.debug("Querying relational database.")
                    results.append(
                        await self.relational_db.search_documents(query.text)
                    )
            if not query.databases or "vector" in query.databases:
                if self.vector_db:
                    logger.debug("Querying vector database.")
                    # Assuming query.embeddings is populated by a prior step or passed in HybridQuery
                    results.append(
                        await self.vector_db.search_vectors(
                            query_vector=[], filters=query.filters
                        )
                    )  # Placeholder for actual query_vector
            if not query.databases or "graph" in query.databases:
                if self.graph_db:
                    logger.debug("Querying graph database.")
                    results.append(
                        await self.graph_db.traverse(query.text, "")
                    )  # Placeholder for graph query
            if not query.databases or "knowledge_graph" in query.databases:
                if self.knowledge_graph_db:
                    logger.debug("Querying knowledge graph database.")
                    results.append(
                        await self.knowledge_graph_db.query_sparql(query.text)
                    )  # Placeholder for SPARQL query

            aggregated_results = self.aggregator.aggregate(results)
            self.cache.set(str(query), aggregated_results)
            logger.info(f"Query executed successfully for: {query.text}")
            return aggregated_results
        except (ValueError, IOError) as exc:
            logger.error(
                "Error during query execution for %s: %s",
                query.text,
                exc,
                exc_info=True,
            )
            raise QueryError(f"Failed to execute query {query.text}: {exc}") from exc
