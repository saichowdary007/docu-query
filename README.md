# DocuQuery AI

[![PyPI package](https://img.shields.io/pypi/v/docuquery-ai.svg?color=brightgreen)](https://pypi.org/project/docuquery-ai/) [![Python Support](https://img.shields.io/badge/python-3.8%7C3.9%7C3.10%7C3.11-blue.svg)](https://pypi.org/project/docuquery-ai/) [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful document query system that combines RAG (Retrieval-Augmented Generation) with structured data handling capabilities. Upload documents and interact with them through natural language queries.

## Features

- **Document Processing**: Supports PDF, DOCX, PPTX, TXT, MD files
- **Structured Data**: Handles CSV, XLS, XLSX with direct data operations
- **Vector Search**: Automatic text chunking and embedding with FAISS
- **Natural Language Queries**: RAG for unstructured documents
- **Google Vertex AI**: Integration with Google's LLM and embedding models
- **CLI Interface**: Command-line tool for easy document management
- **Python API**: Clean programmatic interface for integration

## Installation

Install from PyPI:

```bash
pip install docuquery-ai
```

For development with optional dependencies:

```bash
pip install docuquery-ai[dev,web]
```

For GPU acceleration (if you have CUDA):

```bash
pip install docuquery-ai[gpu]
```

## Quick Start

### 1. Set up Google Cloud credentials

```bash
export GOOGLE_API_KEY="your-google-api-key"
export GOOGLE_PROJECT_ID="your-google-project-id"
```

### 2. Python API Usage

```python
from docuquery_ai import DocumentQueryClient

# Initialize the client
client = DocumentQueryClient(
    google_api_key="your-api-key",
    google_project_id="your-project-id"
)

# Upload a document
result = client.upload_document("path/to/document.pdf")
print(f"Uploaded: {result['filename']}")

# Query the document
response = client.query("What are the main topics discussed?")
print(f"Answer: {response.answer}")

# List all documents
documents = client.list_documents()
for doc in documents:
    print(f"- {doc['filename']} ({doc['file_type']})")
```

### 3. CLI Usage

Initialize DocuQuery AI:

```bash
docuquery init
```

Upload a document:

```bash
docuquery upload document.pdf
```

Query your documents:

```bash
docuquery query "What are the key findings?"
```

List uploaded documents:

```bash
docuquery list
```

Get help:

```bash
docuquery --help
```

## Supported File Types

- **Text Documents**: PDF, DOCX, PPTX, TXT, MD
- **Structured Data**: CSV, XLS, XLSX
- **Archives**: Processing of multiple files

## Advanced Usage

### Custom Configuration

```python
from docuquery_ai import DocumentQueryClient

client = DocumentQueryClient(
    google_api_key="your-api-key",
    google_project_id="your-project-id",
    vector_store_path="./custom_vector_db",
    temp_upload_folder="./custom_temp"
)
```

### Query Specific Files

```python
# Upload multiple files
file1_result = client.upload_document("report1.pdf")
file2_result = client.upload_document("data.xlsx")

# Query specific files
response = client.query(
    "Compare the metrics between reports",
    file_ids=[file1_result['file_id'], file2_result['file_id']]
)
```

### Using with Different Users

```python
# Upload documents for different users
client.upload_document("doc1.pdf", user_id="user_123")
client.upload_document("doc2.pdf", user_id="user_456")

# Query documents for specific user
response = client.query("Summarize the content", user_id="user_123")
```

## Architecture

The system uses a hybrid approach:

- **RAG Pipeline**: For unstructured documents (PDF, DOCX, etc.)
- **Direct Data Operations**: For structured files (CSV, Excel)
- **Vector Store**: FAISS for semantic search
- **LLM Integration**: Google Vertex AI for query understanding and response generation
- **Database**: SQLite for metadata and file tracking

## CLI Commands

- `docuquery init` - Initialize configuration
- `docuquery upload <file>` - Upload and process a document
- `docuquery query "<question>"` - Query uploaded documents
- `docuquery list` - List all uploaded documents
- `docuquery delete <file_id>` - Delete a document
- `docuquery --help` - Show help information

## Development

### Installing for Development

```bash
git clone https://github.com/saichowdary007/DocuQuery-AI.git
cd DocuQuery-AI
pip install -e .[dev]
```

### Running Tests

```bash
pytest
```

### Code Formatting

```bash
black src/
isort src/
```

## Requirements

- Python 3.8+
- Google Cloud credentials (API key or service account)
- Internet connection for Google Vertex AI API calls

## Environment Variables

- `GOOGLE_API_KEY` - Google API key for Vertex AI
- `GOOGLE_PROJECT_ID` - Google Cloud project ID
- `GOOGLE_LOCATION` - Google Cloud location (default: us-central1)

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- [GitHub Issues](https://github.com/saichowdary007/DocuQuery-AI/issues)
- [Documentation](https://github.com/saichowdary007/DocuQuery-AI/blob/main/README.md)

## Acknowledgments

- [LangChain](https://github.com/hwchase17/langchain) for RAG implementation
- [Google Vertex AI](https://cloud.google.com/vertex-ai) for ML capabilities
- [FAISS](https://github.com/facebookresearch/faiss) for vector search
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
