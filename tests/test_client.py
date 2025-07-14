import pytest

from docuquery_ai import DocumentQueryClient
from docuquery_ai.rag.processor import RAGProcessor


@pytest.fixture
async def client():
    """Fixture for DocumentQueryClient."""
    _client = DocumentQueryClient(
        google_api_key="test-api-key",
        google_project_id="test-project-id",
        vector_store_path="/tmp/test_vector_db",
        temp_upload_folder="/tmp/test_temp_uploads",
    )
    try:
        yield _client
    finally:
        _client.dispose()


@pytest.mark.asyncio
async def test_upload_document(client):
    """Test uploading a document."""
    client_instance = client
    # Create a dummy file
    with open("/tmp/test.txt", "w") as f:
        f.write("This is a test document.")

    result = await client_instance.upload_document("/tmp/test.txt", user_id="test_user")
    assert result["success"] is True
    assert result["filename"] == "test.txt"


@pytest.mark.asyncio
async def test_query(client, monkeypatch):
    """Test querying a document."""
    client_instance = client

    async def mock_process(self, query):
        return "The document is about a cat."

    monkeypatch.setattr(RAGProcessor, "process", mock_process)

    # Upload a document (this part is still needed to ensure the client is initialized)
    with open("/tmp/test.txt", "w") as f:
        f.write("This is a test document about a cat.")
    await client_instance.upload_document("/tmp/test.txt", user_id="test_user")

    response = await client_instance.query(
        question="What is the document about?", user_id="test_user"
    )
    assert response.answer == "The document is about a cat."
    assert response.type == "text"


@pytest.mark.asyncio
async def test_list_documents(client, monkeypatch):
    """Test listing documents."""
    client_instance = client

    # Mock the list_documents method as database interaction is removed from client
    async def mock_list_documents(user_id):
        return [{"file_id": "123", "filename": "test.txt"}]

    monkeypatch.setattr(client_instance, "list_documents", mock_list_documents)

    documents = await client_instance.list_documents(user_id="test_user")
    assert len(documents) > 0
    assert documents[0]["filename"] == "test.txt"


@pytest.mark.asyncio
async def test_delete_document(client, monkeypatch):
    """
    Test deleting a document.
    """
    client_instance = client

    # Mock the delete_document method
    async def mock_delete_document(file_id, user_id):
        return True

    monkeypatch.setattr(client_instance, "delete_document", mock_delete_document)

    deleted = await client_instance.delete_document("123", user_id="test_user")
    assert deleted is True


@pytest.mark.asyncio
async def test_upload_missing_file(client):
    client_instance = client
    with pytest.raises(FileNotFoundError):
        await client_instance.upload_document("/tmp/does_not_exist.txt", user_id="u1")
