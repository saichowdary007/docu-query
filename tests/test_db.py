import pytest
from docuquery_ai.db.manager import MultiDatabaseManager
from docuquery_ai.db.models import Document, HybridQuery

@pytest.fixture
async def db_manager():
    manager = MultiDatabaseManager()
    await manager.relational_db.recreate_tables() # Clear tables for each test
    try:
        yield manager
    finally:
        manager.relational_db.dispose()

@pytest.mark.asyncio
async def test_ingest_document(db_manager, monkeypatch):
    db_manager_instance = db_manager
    async def mock_ingest_file(self, file_path, filename):
        return Document(id=filename, title=filename, content="", metadata={}, embeddings=[], entities=[], relationships=[], knowledge_triples=[])
    monkeypatch.setattr("docuquery_ai.ingestion.pipeline.IngestionPipeline.ingest_file", mock_ingest_file)
    doc_id = await db_manager_instance.ingest_document("some/path", "test.txt")
    assert doc_id == "test.txt"

@pytest.mark.asyncio
async def test_hybrid_search(db_manager, monkeypatch):
    db_manager_instance = db_manager
    async def mock_execute_query(self, query):
        return ["result1", "result2"]
    monkeypatch.setattr("docuquery_ai.query.engine.QueryEngine.execute_query", mock_execute_query)
    results = await db_manager_instance.hybrid_search(HybridQuery(text="test query"))
    assert results == ["result1", "result2"]