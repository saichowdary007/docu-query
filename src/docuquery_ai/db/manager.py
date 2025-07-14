import logging
from typing import Any, Dict, List

from docuquery_ai.exceptions import (
    DocumentNotFound,
    IngestionError,
    QueryError,
    UnsupportedFileType,
)

from ..ingestion.pipeline import IngestionPipeline
from ..query.engine import QueryEngine
from .graph import GraphDBManager
from .knowledge_graph import KnowledgeGraphDBManager
from .models import Document, HybridQuery
from .relational import RelationalDBManager
from .vector import VectorDBManager

logger = logging.getLogger(__name__)


class MultiDatabaseManager:
    """
    Manages interactions with multiple database paradigms (Relational, Vector, Graph, Knowledge Graph).
    Provides a unified interface for document ingestion and querying across these databases.
    """

    def __init__(self):
        """
        Initializes the MultiDatabaseManager with an IngestionPipeline and QueryEngine.
        """
        self.ingestion_pipeline = IngestionPipeline()
        self.query_engine = QueryEngine()
        self.relational_db = RelationalDBManager()
        self.vector_db = VectorDBManager()
        self.graph_db = GraphDBManager()
        self.knowledge_graph_db = KnowledgeGraphDBManager()
        self.query_engine.set_db_managers(
            self.relational_db, self.vector_db, self.graph_db, self.knowledge_graph_db
        )

    async def ingest_document(self, file_path: str, filename: str) -> str:
        """
        Ingests a document by processing it through the ingestion pipeline and
        preparing it for storage in various databases.

        Args:
            file_path: The absolute path to the document file.
            filename: The name of the document file.

        Returns:
            The ID of the ingested document.
        """
        try:
            document = await self.ingestion_pipeline.ingest_file(file_path, filename)

            # Store in relational DB
            await self.relational_db.create_document_record(
                doc_id=document.id,
                title=document.title,
                content=document.content,
                file_path=file_path,
                file_type=document.metadata.get("file_type", "unknown"),
                user_id=document.metadata.get("user_id", "unknown"),
                is_structured=document.metadata.get("is_structured", False),
                structure_type=document.metadata.get("structure_type"),
            )

            # Store in vector DB
            if document.embeddings:
                await self.vector_db.add_vectors(
                    document.id, document.embeddings, document.metadata
                )

            # Store in graph DB
            for entity in document.entities:
                await self.graph_db.add_node(entity["text"], entity["label"], entity)
            for rel in document.relationships:
                await self.graph_db.add_edge(
                    rel["source"], rel["target"], rel["type"], rel
                )

            # Store in knowledge graph DB
            for triple in document.knowledge_triples:
                await self.knowledge_graph_db.add_triple(
                    triple[0], triple[1], triple[2]
                )

            logger.info(f"Successfully ingested document: {document.id}")
            return document.id
        except UnsupportedFileType as e:
            logger.error(f"Unsupported file type during ingestion: {e}")
            raise IngestionError(
                f"Failed to ingest document due to unsupported file type: {e}"
            ) from e
        except (ValueError, IOError) as exc:
            logger.error(
                "Error during document ingestion for %s: %s",
                filename,
                exc,
                exc_info=True,
            )
            raise IngestionError(
                f"Failed to ingest document {filename}: {exc}"
            ) from exc

    async def search_semantic(self, query: str, filters: Dict) -> List[Any]:
        """
        Performs a semantic search across the integrated databases.
        (Currently a placeholder)

        Args:
            query: The semantic query string.
            filters: A dictionary of filters to apply to the search.

        Returns:
            A list of search results.
        """
        raise NotImplementedError("search_semantic is not implemented yet")

    async def search_relational(self, query: Any) -> List[Any]:
        """
        Performs a relational search across the integrated databases.
        (Currently a placeholder)

        Args:
            query: The relational query (e.g., SQL query object).

        Returns:
            A list of search results.
        """
        raise NotImplementedError("search_relational is not implemented yet")

    async def traverse_graph(self, start_node: str, relationship: str) -> List[Any]:
        """
        Traverses the graph database based on a starting node and relationship.
        (Currently a placeholder)

        Args:
            start_node: The ID of the starting node for traversal.
            relationship: The type of relationship to traverse.

        Returns:
            A list of nodes found during traversal.
        """
        raise NotImplementedError("traverse_graph is not implemented yet")

    async def query_knowledge(self, sparql_query: str) -> List[Any]:
        """
        Queries the knowledge graph using SPARQL.
        (Currently a placeholder)

        Args:
            sparql_query: The SPARQL query string.

        Returns:
            A list of triples from the knowledge graph.
        """
        raise NotImplementedError("query_knowledge is not implemented yet")

    async def hybrid_search(self, query: HybridQuery) -> List[Any]:
        """
        Executes a hybrid search using the QueryEngine, combining different
        search paradigms based on the HybridQuery.

        Args:
            query: An instance of HybridQuery specifying the search parameters.

        Returns:
            A list of aggregated search results.
        """
        try:
            return await self.query_engine.execute_query(query)
        except (ValueError, IOError) as exc:
            logger.error(
                "Error during hybrid search for %s: %s", query.text, exc, exc_info=True
            )
            raise QueryError(f"Failed to perform hybrid search: {exc}") from exc

    def dispose(self):
        """
        Disposes of resources held by the database managers.
        """
        self.relational_db.dispose()
        # Add dispose calls for other managers if they have them
