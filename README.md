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

## Deployment Instructions

### Deploying to Vercel

1. **Setup Vercel Environment Variables**:
   - Go to your Vercel project settings
   - Add the following environment variables:
     - `NEXT_PUBLIC_BACKEND_URL`: URL of your backend API (e.g., https://your-backend-api.com)
     - `NEXT_PUBLIC_BACKEND_API_KEY`: Secret API key for backend authentication

### Deploying to Render

1. **Setup Render Blueprint**:
   - The included `render.yaml` file configures the deployment
   - It will automatically create database and necessary services

2. **Environment Variables**:
   - Most variables are automatically set through the blueprint
   - Custom variables like API keys need to be set in the Render dashboard

3. **Default Admin User**:
   - On first deployment, an admin user is automatically created 
   - Default email: `admin@docuquery.ai` (can be customized via `SEED_ADMIN_EMAIL`)
   - Password: Auto-generated (view in Render logs or set via `SEED_ADMIN_PASSWORD`)
   - Use these credentials for the initial login
   - Create additional users through the application

4. **Important Notes**:
   - Database setup happens automatically on first deployment
   - Uploaded files are stored in a persistent disk
   - API documentation available at `/docs` endpoint

## Local Development

```bash
# Install dependencies
npm install
cd frontend && npm install

# Run frontend and backend concurrently
npm run dev

# Run frontend only
npm run dev:frontend

# Run backend only
npm run dev:backend
```

## Project Structure

- `frontend/`: Next.js application
- `backend/`: FastAPI application for document processing and querying

## Technologies Used

- **Frontend**: Next.js, React, TailwindCSS, Framer Motion
- **Backend**: FastAPI, LangChain, FAISS, Python
- **Document Processing**: LangChain document loaders and processors
