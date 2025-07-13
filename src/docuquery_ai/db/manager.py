import logging
from typing import List, Dict, Any
from .models import Document, HybridQuery

from ..ingestion.pipeline import IngestionPipeline
from ..query.engine import QueryEngine
from docuquery_ai.exceptions import IngestionError, QueryError, DocumentNotFound, UnsupportedFileType

from .relational import RelationalDBManager
from .vector import VectorDBManager
from .graph import GraphDBManager
from .knowledge_graph import KnowledgeGraphDBManager

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
        self.query_engine.set_db_managers(self.relational_db, self.vector_db, self.graph_db, self.knowledge_graph_db)

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
                await self.vector_db.add_vectors(document.id, document.embeddings, document.metadata)

            # Store in graph DB
            for entity in document.entities:
                await self.graph_db.add_node(entity["text"], entity["label"], entity)
            for rel in document.relationships:
                await self.graph_db.add_edge(rel["source"], rel["target"], rel["type"], rel)

            # Store in knowledge graph DB
            for triple in document.knowledge_triples:
                await self.knowledge_graph_db.add_triple(triple[0], triple[1], triple[2])

            logger.info(f"Successfully ingested document: {document.id}")
            return document.id
        except UnsupportedFileType as e:
            logger.error(f"Unsupported file type during ingestion: {e}")
            raise IngestionError(f"Failed to ingest document due to unsupported file type: {e}") from e
        except Exception as e:
            logger.error(f"Error during document ingestion for {filename}: {e}", exc_info=True)
            raise IngestionError(f"Failed to ingest document {filename}: {e}") from e

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
        try:
            # This would typically involve querying the vector_db
            return await self.vector_db.search_vectors(query_vector=[], filters=filters) # Placeholder
        except Exception as e:
            logger.error(f"Error during semantic search for {query}: {e}", exc_info=True)
            raise QueryError(f"Failed to perform semantic search: {e}") from e

    async def search_relational(self, query: Any) -> List[Any]:
        """
        Performs a relational search across the integrated databases.
        (Currently a placeholder)

        Args:
            query: The relational query (e.g., SQL query object).

        Returns:
            A list of search results.
        """
        try:
            # This would typically involve querying the relational_db
            return await self.relational_db.search_documents(query) # Placeholder
        except Exception as e:
            logger.error(f"Error during relational search for {query}: {e}", exc_info=True)
            raise QueryError(f"Failed to perform relational search: {e}") from e

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
        try:
            # This would typically involve querying the graph_db
            return await self.graph_db.traverse(start_node, relationship) # Placeholder
        except Exception as e:
            logger.error(f"Error during graph traversal from {start_node}: {e}", exc_info=True)
            raise QueryError(f"Failed to traverse graph: {e}") from e

    async def query_knowledge(self, sparql_query: str) -> List[Any]:
        """
        Queries the knowledge graph using SPARQL.
        (Currently a placeholder)

        Args:
            sparql_query: The SPARQL query string.

        Returns:
            A list of triples from the knowledge graph.
        """
        try:
            # This would typically involve querying the knowledge_graph_db
            return await self.knowledge_graph_db.query_sparql(sparql_query) # Placeholder
        except Exception as e:
            logger.error(f"Error during knowledge graph query for {sparql_query}: {e}", exc_info=True)
            raise QueryError(f"Failed to query knowledge graph: {e}") from e

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
        except Exception as e:
            logger.error(f"Error during hybrid search for {query.text}: {e}", exc_info=True)
            raise QueryError(f"Failed to perform hybrid search: {e}") from e

    def dispose(self):
        """
        Disposes of resources held by the database managers.
        """
        self.relational_db.dispose()
        # Add dispose calls for other managers if they have them
