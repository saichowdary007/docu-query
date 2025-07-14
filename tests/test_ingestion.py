import pytest

from docuquery_ai.db.models import Document
from docuquery_ai.ingestion.pipeline import IngestionPipeline


@pytest.fixture
def ingestion_pipeline():
    return IngestionPipeline()


@pytest.mark.asyncio
async def test_ingest_file(ingestion_pipeline, monkeypatch):
    async def mock_generate_embeddings(self, text):
        return [1.0, 2.0, 3.0]

    async def mock_extract_entities(self, text):
        return [{"text": "test", "label": "MISC"}]

    monkeypatch.setattr(
        "docuquery_ai.ingestion.embedding.EmbeddingGenerator.generate_embeddings",
        mock_generate_embeddings,
    )
    monkeypatch.setattr(
        "docuquery_ai.ingestion.ner.NER.extract_entities", mock_extract_entities
    )
    with open("/tmp/test.txt", "w") as f:
        f.write("This is a test document.")
    doc = await ingestion_pipeline.ingest_file("/tmp/test.txt", "test.txt")
    assert doc.id == "test.txt"
    assert doc.content == "This is a test document."
    assert doc.embeddings == [1.0, 2.0, 3.0]
    assert doc.entities == [{"text": "test", "label": "MISC"}]
