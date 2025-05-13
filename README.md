# DocuQuery AI

A powerful document query system that combines RAG (Retrieval-Augmented Generation) with structured data handling capabilities. Upload documents and interact with them through natural language queries.

## Features

- **Document Processing**:
  - Supports PDF, DOCX, PPTX, TXT, MD files
  - Handles structured data (CSV, XLS, XLSX)
  - Automatic text chunking and embedding
  - Vector store for semantic search

- **Query Capabilities**:
  - Natural language understanding
  - RAG for unstructured documents
  - Direct data operations on structured files
  - Table filtering and downloads
  - Entity extraction

- **Modern UI**:
  - Real-time chat interface
  - Drag-and-drop file upload
  - Interactive data visualization
  - Responsive design
  - Modern UI animations with Magic UI components
  - Premium shine border effects

## Tech Stack

### Backend
- FastAPI
- LangChain
- Google Vertex AI (Embeddings & LLM)
- FAISS Vector Store
- Pandas for structured data
- Various document parsers (PyPDF2, python-docx, etc.)

### Frontend
- Next.js 14
- React
- TypeScript
- TailwindCSS
- React Dropzone

## Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/docuquery-ai.git
   cd docuquery-ai
   ```

2. **Set up environment variables**:
   ```bash
   # Copy example env files
   cp backend/.env.example backend/.env
   ```
   Edit the `.env` file with your:
   - Google Cloud credentials
   - Backend API key
   - Other configuration

3. **Using Docker (Recommended)**:
   ```bash
   docker-compose up --build
   ```
   This will start both frontend and backend services.

4. **Manual Setup**:
   
   Backend:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # or `venv\Scripts\activate` on Windows
   pip install -r requirements.txt
   uvicorn app.main:app --reload
   ```

   Frontend:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

5. **Access the application**:
   - Frontend: http://localhost:3000
   - Backend API: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Usage

1. **Upload Documents**:
   - Use the file upload interface
   - Drag & drop supported
   - Multiple files accepted

2. **Query Your Documents**:
   - Type natural language questions
   - Ask about document content
   - Request specific data from structured files
   - Download filtered results

3. **Examples**:
   ```
   "What are the main risks mentioned in the report?"
   "Show me all departments from employees.xlsx"
   "Find sales records over $50,000"
   "Extract all dates and locations from the documents"
   ```

## Architecture

The system uses a hybrid approach:
- RAG for unstructured documents (PDF, DOCX, etc.)
- Direct data operations for structured files (CSV, Excel)
- LLM for query understanding and response generation
- Vector store for semantic search
- Caching for structured data operations

## Development

- **Backend Structure**:
  - `app/`: Main application code
  - `core/`: Configuration and security
  - `models/`: Pydantic models
  - `services/`: Business logic
  - `routers/`: API endpoints

- **Frontend Structure**:
  - `app/`: Next.js app directory
  - `components/`: React components
  - `styles/`: CSS and styling

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

MIT License - see LICENSE file for details.

## Acknowledgments

- LangChain for RAG implementation
- Google Vertex AI for ML capabilities
- FastAPI for the robust backend
- Next.js team for the frontend framework

## UI Components

The application uses custom Magic UI components to create a premium look and feel:

### BorderBeam Component

The BorderBeam component adds a beautiful animated shine effect to containers, creating a premium border animation that draws attention to important UI elements. Used in:

- Chat interface
- File uploader
- Application header

To use the BorderBeam component:

```jsx
import { BorderBeam } from '@/app/components/ui/border-beam';

// Inside your component
<div className="relative overflow-hidden">
  <BorderBeam 
    size={80}
    duration={8}
    colorFrom="#3B82F6" 
    colorTo="#8B5CF6"
  />
  {/* Your content */}
</div>
```

#### Properties

- `size`: Size of the beam effect (default: 50)
- `duration`: Animation duration in seconds (default: 6)
- `colorFrom`: Start color of the gradient (default: "#ffaa40")
- `colorTo`: End color of the gradient (default: "#9c40ff")
- `reverse`: Reverse animation direction (default: false)
