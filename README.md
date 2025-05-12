# DocuQuery

DocuQuery is a RAG (Retrieval-Augmented Generation) chatbot that allows you to query your documents using natural language. It supports multiple file formats including CSV, XLSX, PDF, DOCX, PPTX, TXT, and MD.

## Features

- **Multi-format document support**: CSV, XLSX, PDF, DOCX, PPTX, TXT, MD
- **Drag-and-drop file upload**: Easy document ingestion
- **Natural language querying**: Ask questions about your documents in plain English
- **SQL querying for tabular data**: Run SQL queries on CSV and Excel files
- **Export functionality**: Export query results as Excel files
- **Citation tracking**: All responses include citations to the source documents
- **Named Entity Recognition**: Automatically extracts persons and sections from your documents
- **Code-first tabular queries**: Bypasses the LLM for simple count/list operations on tabular data
- **File-scoped queries**: Keep conversations context-bound to specific documents

## Tech Stack

- **Backend**: FastAPI, DuckDB, Chroma, Google Gemini 2.0 Flash, spaCy NER
- **Frontend**: React, Vite, Tailwind CSS
- **Deployment**: Docker Compose

## Getting Started

### Prerequisites

- Docker and Docker Compose
- Google API key for Gemini (get one at https://makersuite.google.com/app/apikey)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/docuquery.git
   cd docuquery
   ```

2. Create a `.env` file in the root directory with your Google API key:
   ```
   GOOGLE_API_KEY=your_google_api_key_here
   ```

3. Build and start the application:
   ```bash
   docker compose up --build
   ```

4. Access the application at http://localhost:5173

## Usage

1. Upload your documents using the drag-and-drop interface
2. Wait for the documents to be processed and indexed
3. Ask questions about your documents in the chat interface
4. For tabular data, you can:
   - Ask natural language questions like "How many sales were made in Q1?"
   - Use direct commands like "List all customers in New York"
   - Use SQL queries by starting your message with "SELECT"
5. To export data, ask for an export or use a SQL query and click the "Download Excel File" button
6. For documents with named entities, you can ask "Who are the people mentioned in this document?"

## Development

### Project Structure

```
docuquery/
├── backend/
│   ├── Dockerfile
│   ├── main.py
│   ├── rag_core.py
│   ├── response_generator.py
│   ├── test_document_indexing.py
│   ├── test_imports.py
│   └── requirements.txt
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   └── src/
│       ├── App.jsx
│       ├── api.js
│       └── components/
│           ├── ChatWindow.jsx
│           └── FileDrop.jsx
├── docs/
│   └── system_prompt.md
└── docker-compose.yml
```

### Local Development

To develop locally:

1. Start the backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   python -m spacy download en_core_web_sm
   uvicorn main:app --reload
   ```

2. Start the frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

### Testing

Run the test suite to verify functionality:

```bash
cd backend
python -m unittest discover
```

## Recent Enhancements

- **Row-level spreadsheet ingestion**: Each row is now individually indexed with its own metadata
- **Named Entity Recognition**: Using spaCy to extract person names and document sections
- **Code-first tabular queries**: Direct SQL generation for simple count/list operations
- **File-scoped namespace**: Queries can now be limited to specific uploaded files
- **Enhanced exports**: Improved Excel export functionality via the /export endpoint

## License

MIT 