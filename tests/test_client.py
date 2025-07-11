import os
import pytest
from docuquery_ai import DocumentQueryClient
from docuquery_ai.services.nlp_service import GeminiChatModel

@pytest.fixture
def client():
    """Fixture for DocumentQueryClient."""
    return DocumentQueryClient(
        google_api_key="test-api-key",
        google_project_id="test-project-id",
        vector_store_path="/tmp/test_vector_db",
        temp_upload_folder="/tmp/test_temp_uploads",
    )

def test_upload_document(client):
    """Test uploading a document."""
    # Create a dummy file
    with open("/tmp/test.txt", "w") as f:
        f.write("This is a test document.")

    result = client.upload_document("/tmp/test.txt", user_id="test_user")
    assert result["success"] is True
    assert result["filename"] == "test.txt"
    assert result["file_type"] == ".txt"
    assert result["is_structured"] is False
    assert result["documents_count"] > 0

@pytest.mark.asyncio
async def test_query(client, monkeypatch):
    """Test querying a document."""

    def mock_call_api(self, messages):
        return {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": "The document is about a cat."
                            }
                        ]
                    }
                }
            ]
        }

    monkeypatch.setattr(GeminiChatModel, "_call_api", mock_call_api)
    # Upload a document
    with open("/tmp/test.txt", "w") as f:
        f.write("This is a test document about a cat.")

    client.upload_document("/tmp/test.txt", user_id="test_user")

    response = await client.query(question="What is the document about?", user_id="test_user")
    assert response.answer != ""

def test_list_documents(client):
    """Test listing documents."""
    # Upload a document
    with open("/tmp/test.txt", "w") as f:
        f.write("This is a test document.")

    client.upload_document("/tmp/test.txt", user_id="test_user")

    documents = client.list_documents(user_id="test_user")
    assert len(documents) > 0

def test_delete_document(client):
    """Test deleting a document."""
    # Upload a document
    with open("/tmp/test.txt", "w") as f:
        f.write("This is a test document.")

    result = client.upload_document("/tmp/test.txt", user_id="test_user")
    file_id = result["file_id"]

    # Delete the document
    deleted = client.delete_document(file_id, user_id="test_user")
    assert deleted is True

    # Verify that the document is no longer listed
    documents = client.list_documents(user_id="test_user")
    assert len(documents) == 0