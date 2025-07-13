import pytest
from docuquery_ai.rag.processor import RAGProcessor
from docuquery_ai.db.manager import MultiDatabaseManager

@pytest.fixture
def rag_processor():
    return RAGProcessor(MultiDatabaseManager())

@pytest.mark.asyncio
async def test_process(rag_processor, monkeypatch):
    async def mock_retrieve(self, query):
        return ["result1", "result2"]
    async def mock_generate(self, query, context):
        return "answer"

    monkeypatch.setattr("docuquery_ai.rag.retriever.Retriever.retrieve", mock_retrieve)
    monkeypatch.setattr("docuquery_ai.rag.context.ContextAssembler.assemble", lambda self, results: "context")
    monkeypatch.setattr("docuquery_ai.rag.generator.ResponseGenerator.generate", mock_generate)
    answer = await rag_processor.process("test query")
    assert answer == "answer"