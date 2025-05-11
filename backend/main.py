import os
import io
import tempfile
import logging
from typing import List, Dict, Any, Optional
import pandas as pd
import pdfplumber
import docx
import pptx
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import google.generativeai as genai
from langchain_core.documents import Document
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from langchain_core.language_models.chat_models import BaseChatModel
import duckdb

from rag_core import embed, retrieve, register_duckdb_table

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
logger.info(f"Google API Key configured: {os.getenv('GOOGLE_API_KEY')[:5]}...")

# Initialize FastAPI app
app = FastAPI(title="DocuQuery API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load system prompt
try:
    with open("./docs/system_prompt.md", "r") as f:
        SYSTEM_PROMPT = f.read()
    logger.info("System prompt loaded successfully")
except Exception as e:
    logger.error(f"Error loading system prompt: {e}")
    SYSTEM_PROMPT = "You are DocuQuery, an expert document analysis assistant."

# Initialize LLM
try:
    import google.generativeai as genai
    
    # Configure the API key
    genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
    
    # Initialize LLM with proper initialization for version 0.0.6
    from langchain_google_genai import ChatGoogleGenerativeAI
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash", 
        temperature=0.2,
        convert_system_message_to_human=True,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    logger.info("LLM initialized successfully")
except Exception as e:
    logger.error(f"Error initializing LLM: {e}")
    import traceback
    logger.error(traceback.format_exc())
    
    # Fallback to a simple model that doesn't require external APIs
    from langchain_core.language_models.chat_models import SimpleChatModel
    from langchain_core.messages import AIMessage
    from langchain_core.outputs import ChatGeneration, ChatResult
    
    class FallbackChatModel(SimpleChatModel):
        def _call(self, messages, stop=None, run_manager=None, **kwargs):
            return "I'm sorry, but I cannot process your request at the moment. The language model is unavailable. Please check your API keys and try again later."
            
        async def _acall(self, messages, stop=None, run_manager=None, **kwargs):
            return self._call(messages, stop, run_manager, **kwargs)
    
    llm = FallbackChatModel()
    logger.info("Using fallback chat model due to initialization error")

# File upload directory
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Document loaders
def load_csv_xlsx(file_path: str) -> List[Document]:
    """Load CSV or XLSX file into documents and register as DuckDB table"""
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
            logger.info(f"Loaded CSV file with {len(df)} rows")
        else:
            # Handle XLS/XLSX files with better error handling
            try:
                df = pd.read_excel(file_path, engine='openpyxl' if file_path.endswith('.xlsx') else 'xlrd')
                logger.info(f"Loaded Excel file with {len(df)} rows")
            except Exception as xlsx_error:
                logger.error(f"Error with openpyxl/xlrd: {xlsx_error}, trying alternative engine")
                try:
                    # Fallback method for problematic Excel files
                    df = pd.read_excel(file_path, engine='pyxlsb' if file_path.endswith('.xlsb') else None)
                    logger.info(f"Loaded Excel file with fallback engine, {len(df)} rows")
                except Exception as alt_error:
                    logger.error(f"All Excel reading methods failed: {alt_error}")
                    raise
        
        # Handle empty dataframes
        if df.empty:
            logger.warning(f"File {file_path} contains no data")
            return []
            
        # Register dataframe as DuckDB table with proper schema
        table_name = os.path.basename(file_path).split('.')[0].replace(' ', '_').lower()
        register_success = register_duckdb_table(df, table_name)
        logger.info(f"DuckDB table registration for '{table_name}': {'success' if register_success else 'failed'}")
        
        # Create document for the schema
        schema_info = f"Table: {table_name}\nColumns: {', '.join(df.columns.tolist())}\nRows: {len(df)}"
        schema_doc = Document(
            page_content=schema_info,
            metadata={
                "source": os.path.basename(file_path),
                "file_type": "tabular",
                "table_name": table_name,
                "is_schema": True
            }
        )
        documents = [schema_doc]
        
        # Create statistical summary if possible
        try:
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                stats = df[numeric_cols].describe().to_string()
                stats_doc = Document(
                    page_content=f"Statistical summary for {table_name}:\n{stats}",
                    metadata={
                        "source": os.path.basename(file_path),
                        "file_type": "tabular",
                        "table_name": table_name,
                        "is_stats": True
                    }
                )
                documents.append(stats_doc)
        except Exception as stats_error:
            logger.warning(f"Could not generate statistics: {stats_error}")
        
        # Convert each row to a Document
        for i, row in df.iterrows():
            # Convert row to dict and handle non-serializable objects
            row_dict = row.to_dict()
            for k, v in row_dict.items():
                if pd.isna(v):
                    row_dict[k] = None
                elif isinstance(v, (pd.Timestamp, pd._libs.tslibs.timestamps.Timestamp)):
                    row_dict[k] = str(v)
            
            # Create document with row data as metadata and a summary as content
            content = f"Row {i} of {os.path.basename(file_path)}: {', '.join([f'{k}: {v}' for k, v in row_dict.items()])}"
            doc = Document(
                page_content=content,
                metadata={
                    "row": i,
                    "source": os.path.basename(file_path),
                    "table_name": table_name,
                    "file_type": "tabular",
                    **row_dict
                }
            )
            documents.append(doc)
        
        logger.info(f"Created {len(documents)} documents from tabular data")
        return documents
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def load_pdf(file_path: str) -> List[Document]:
    """Load PDF file into documents"""
    documents = []
    try:
        with pdfplumber.open(file_path) as pdf:
            logger.info(f"PDF has {len(pdf.pages)} pages")
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if text.strip():
                    doc = Document(
                        page_content=text,
                        metadata={
                            "page": i + 1,
                            "source": os.path.basename(file_path)
                        }
                    )
                    documents.append(doc)
        logger.info(f"Created {len(documents)} documents from PDF")
        return documents
    except Exception as e:
        logger.error(f"Error loading PDF {file_path}: {e}")
        return []

def load_docx(file_path: str) -> List[Document]:
    """Load DOCX file into documents with improved structure detection"""
    documents = []
    try:
        doc = docx.Document(file_path)
        logger.info(f"DOCX has {len(doc.paragraphs)} paragraphs")
        
        # Extract content with better structure awareness
        current_section = "HEADER"
        section_content = {}
        section_map = {}
        all_text = ""
        
        # First pass to identify document structure and sections
        for i, para in enumerate(doc.paragraphs):
            text = para.text.strip()
            if not text:
                continue
                
            all_text += text + "\n"
            
            # Detect section headers (all caps, short lines)
            if text.isupper() and len(text) < 50 and not text.endswith(':'):
                current_section = text
                section_content[current_section] = []
            else:
                if current_section not in section_content:
                    section_content[current_section] = []
                section_content[current_section].append((i, text))
                section_map[i] = current_section
        
        # Create one document with all content (better for small files like resumes)
        if all_text.strip():
            full_doc = Document(
                page_content=all_text,
                metadata={
                    "source": os.path.basename(file_path),
                    "file_type": "docx",
                    "sections": list(section_content.keys())
                }
            )
            documents.append(full_doc)
            logger.info(f"Created document with {len(all_text)} characters and {len(section_content)} sections")
        
        # Create section documents for more targeted retrieval
        for section, paras in section_content.items():
            if paras:
                section_text = f"{section}\n" + "\n".join([p[1] for p in paras])
                section_doc = Document(
                    page_content=section_text,
                    metadata={
                        "source": os.path.basename(file_path),
                        "section": section,
                        "paragraph_range": f"{paras[0][0]}-{paras[-1][0]}",
                        "file_type": "docx"
                    }
                )
                documents.append(section_doc)
        
        # Also create individual paragraph documents for more granular retrieval
        for i, para in enumerate(doc.paragraphs):
            if para.text.strip():
                section = section_map.get(i, "UNKNOWN")
                para_doc = Document(
                    page_content=para.text,
                    metadata={
                        "paragraph": i + 1,
                        "source": os.path.basename(file_path),
                        "section": section,
                        "file_type": "docx"
                    }
                )
                documents.append(para_doc)
        
        logger.info(f"Created {len(documents)} documents from DOCX")
        return documents
    except Exception as e:
        logger.error(f"Error loading DOCX {file_path}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def load_pptx(file_path: str) -> List[Document]:
    """Load PPTX file into documents"""
    documents = []
    try:
        pres = pptx.Presentation(file_path)
        logger.info(f"PPTX has {len(pres.slides)} slides")
        for i, slide in enumerate(pres.slides):
            # Extract text from all shapes in the slide
            texts = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text.strip():
                    texts.append(shape.text)
            
            if texts:
                content = "\n".join(texts)
                doc = Document(
                    page_content=content,
                    metadata={
                        "slide": i + 1,
                        "source": os.path.basename(file_path)
                    }
                )
                documents.append(doc)
        logger.info(f"Created {len(documents)} documents from PPTX")
        return documents
    except Exception as e:
        logger.error(f"Error loading PPTX {file_path}: {e}")
        return []

def load_text(file_path: str) -> List[Document]:
    """Load TXT or MD file into documents"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.info(f"Loaded text file with {len(content)} characters")
        
        if not content.strip():
            logger.warning(f"Text file {file_path} is empty")
            return []
        
        # Create one document with all content
        doc = Document(
            page_content=content,
            metadata={
                "source": os.path.basename(file_path),
                "file_type": "text"
            }
        )
        
        # Also create documents by paragraph for more granular retrieval
        paragraphs = []
        for i, para in enumerate(content.split('\n\n')):
            if para.strip():
                para_doc = Document(
                    page_content=para.strip(),
                    metadata={
                        "paragraph": i + 1,
                        "source": os.path.basename(file_path)
                    }
                )
                paragraphs.append(para_doc)
        
        logger.info(f"Created {len(paragraphs) + 1} documents from text file")
        return [doc] + paragraphs
    except Exception as e:
        logger.error(f"Error loading text file {file_path}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def process_file(file_path: str) -> Dict[str, Any]:
    """Process file based on its extension"""
    logger.info(f"Processing file: {file_path}")
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return {"success": False, "message": f"File not found: {file_path}"}
    
    file_ext = os.path.splitext(file_path)[1].lower()
    logger.info(f"File extension: {file_ext}")
    
    if file_ext in ['.csv', '.xlsx', '.xls', '.xlsb']:
        docs = load_csv_xlsx(file_path)
        file_type = "tabular"
    elif file_ext == '.pdf':
        docs = load_pdf(file_path)
        file_type = "pdf"
    elif file_ext == '.docx':
        docs = load_docx(file_path)
        file_type = "docx"
    elif file_ext == '.pptx':
        docs = load_pptx(file_path)
        file_type = "pptx"
    elif file_ext in ['.txt', '.md']:
        docs = load_text(file_path)
        file_type = "text"
    else:
        logger.error(f"Unsupported file type: {file_ext}")
        return {"success": False, "message": f"Unsupported file type: {file_ext}"}
    
    if not docs:
        logger.error(f"No content extracted from {os.path.basename(file_path)}")
        return {"success": False, "message": f"No content extracted from {os.path.basename(file_path)}"}
    
    # Embed documents
    logger.info(f"Embedding {len(docs)} documents from {file_path}")
    try:
        chunks_count = embed(file_path, docs)
        logger.info(f"Successfully embedded {chunks_count} chunks")
        
        return {
            "success": True,
            "file_type": file_type,
            "file_name": os.path.basename(file_path),
            "chunks_count": chunks_count
        }
    except Exception as e:
        logger.error(f"Error embedding documents: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"success": False, "message": f"Error embedding documents: {str(e)}"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a file"""
    try:
        logger.info(f"Received file upload: {file.filename}")
        # Create uploads directory if it doesn't exist
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        # Save file
        file_path = os.path.join(UPLOAD_DIR, file.filename)
        logger.info(f"Saving file to {file_path}")
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"File saved to {file_path}, size: {len(content)} bytes")
        
        # Process file synchronously
        logger.info(f"Processing file synchronously: {file.filename}")
        result = process_file(file_path)
        logger.info(f"File processing result: {result}")
        return result
            
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/chat")
async def chat(query: str = Form(...), history: Optional[str] = Form(None)):
    """Process a chat message"""
    try:
        logger.info(f"Received chat query: {query}")
        
        # Parse history from JSON string if provided
        chat_history = []
        if history:
            import json
            try:
                chat_history = json.loads(history)
                logger.info(f"Parsed chat history with {len(chat_history)} messages")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse history: {e}")
        
        # Determine if query appears to be asking for SQL-like information
        sql_indicators = ["list", "count", "how many", "average", "sum", "total", "compare", 
                        "sort", "filter", "show me", "table", "spreadsheet", "excel"]
        
        is_likely_sql_query = any(indicator in query.lower() for indicator in sql_indicators)
        logger.info(f"Query SQL likelihood assessment: {is_likely_sql_query}")
        
        # Retrieve relevant documents
        retrieval_result = retrieve(query)
        logger.info(f"Retrieval result type: {retrieval_result['type']}")
        
        # Prepare context for LLM
        context = ""
        
        if retrieval_result["type"] == "sql_result":
            # Format SQL results
            context += f"SQL Query: {retrieval_result['query']}\n\n"
            context += "Results:\n"
            
            # Get column names if available
            if "columns" in retrieval_result:
                context += f"Columns: {', '.join(retrieval_result['columns'])}\n"
                
            for i, row in enumerate(retrieval_result["data"]):
                context += f"Row {i+1}: {row}\n"
            logger.info(f"SQL results: {len(retrieval_result['data'])} rows")
            
            # Add hint about export capability
            context += "\nNote: This data can be exported as Excel by using the export feature.\n"
        
        elif retrieval_result["type"] == "documents":
            # Format document results
            doc_count = len(retrieval_result["data"]) if "data" in retrieval_result else 0
            logger.info(f"Retrieved {doc_count} documents")
            
            # Check if documents are from tabular data
            has_tabular = any(doc.metadata.get('is_tabular', False) for doc in retrieval_result["data"])
            table_names = set()
            
            # First pass to identify table names and assess if SQL might be better
            for doc in retrieval_result["data"]:
                if doc.metadata.get('is_tabular', False) and 'table_name' in doc.metadata:
                    table_names.add(doc.metadata['table_name'])
            
            # If we detected tabular data and the query looks like it needs SQL, add a hint
            if has_tabular and table_names and is_likely_sql_query:
                context += f"Your question appears to be about tabular data. I'll try to answer directly, but for more detailed analysis, you could ask using SQL.\n\n"
            
            # Format retrieved documents with proper citations
            for doc in retrieval_result["data"]:
                source = doc.metadata.get("source", "unknown")
                
                # Collect table names for tabular data
                if doc.metadata.get('is_tabular', False) and 'table_name' in doc.metadata:
                    table_names.add(doc.metadata['table_name'])
                
                # Add appropriate locator based on document type
                locator = ""
                if "page" in doc.metadata:
                    locator = f"#page={doc.metadata['page']}"
                elif "slide" in doc.metadata:
                    locator = f"#slide={doc.metadata['slide']}"
                elif "paragraph" in doc.metadata:
                    locator = f"#paragraph={doc.metadata['paragraph']}"
                elif "row" in doc.metadata:
                    locator = f"#row={doc.metadata['row']}"
                
                # Format as a citation
                citation = f"[{source}{locator}]"
                context += f"Content {citation}: {doc.page_content}\n\n"
            
            # Add hint about SQL querying capability for tabular data
            if has_tabular and table_names:
                context += f"\nNote: This data comes from tables: {', '.join(table_names)}. "
                context += f"You can query this data using SQL with 'SELECT * FROM {next(iter(table_names))}'\n"
        
        elif retrieval_result["type"] == "error":
            context += f"Error: {retrieval_result['message']}"
            logger.error(f"Retrieval error: {retrieval_result['message']}")
        
        # Create prompt
        system_prompt = SYSTEM_PROMPT + "\n\n" + """
IMPORTANT GUIDELINES:
1. Always cite sources using [filename:page/paragraph/row] format
2. For tabular data questions, suggest SQL queries when appropriate
3. Ask specific clarifying questions when information is insufficient
4. Only provide information that's directly supported by the retrieved evidence
5. Format your answers clearly with direct responses to the user's question first
"""
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", f"Context information is below.\n\n{context}\n\nQuestion: {query}")
        ])
        
        # Generate response
        logger.info("Generating response from LLM")
        chain = prompt | llm
        response = chain.invoke({})
        logger.info("LLM response generated successfully")
        
        # Post-process response to ensure proper formatting
        response_text = response.content
        
        # If no citations in response but we have documents, add a generic citation
        if "[" not in response_text and retrieval_result["type"] == "documents" and len(retrieval_result["data"]) > 0:
            sources = [doc.metadata.get("source", "unknown") for doc in retrieval_result["data"]]
            unique_sources = list(set(sources))
            if unique_sources:
                source_citation = f" (Source: {', '.join(unique_sources)})"
                response_text += source_citation
        
        return {"response": response_text}
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.get("/export")
async def export_data(sql: str, filename: Optional[str] = None):
    """Export data as XLSX based on SQL query"""
    try:
        # Execute SQL query
        logger.info(f"Exporting data with SQL: {sql}")
        retrieval_result = retrieve(sql)
        
        if retrieval_result["type"] != "sql_result":
            logger.error(f"Invalid SQL query: {sql}")
            raise HTTPException(status_code=400, detail="Invalid SQL query")
        
        # Check if we have data
        if not retrieval_result["data"]:
            logger.warning("SQL query returned no data")
            raise HTTPException(status_code=404, detail="Query returned no data")
        
        # Convert results to DataFrame
        df = pd.DataFrame(retrieval_result["data"])
        logger.info(f"Exporting {len(df)} rows")
        
        # Generate filename if not provided
        export_filename = filename
        if not export_filename:
            import time
            timestamp = int(time.time())
            export_filename = f"export_{timestamp}.xlsx"
        elif not export_filename.endswith(('.xlsx', '.xls')):
            export_filename += '.xlsx'
        
        # Create in-memory Excel file
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        output.seek(0)
        
        # Return streaming response
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={export_filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error exporting data: {str(e)}")

@app.get("/tables")
async def list_tables():
    """List available tables in the database"""
    try:
        # Get available tables
        tables = duckdb.connect(database=":memory:", read_only=False).execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables]
        logger.info(f"Available tables: {table_names}")
        
        table_info = []
        for table_name in table_names:
            try:
                # Get row count
                count = duckdb.connect(database=":memory:", read_only=False).execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                
                # Get column info
                columns = duckdb.connect(database=":memory:", read_only=False).execute(f"PRAGMA table_info({table_name})").fetchall()
                column_names = [col[1] for col in columns]
                
                table_info.append({
                    "name": table_name,
                    "rows": count,
                    "columns": column_names
                })
            except Exception as e:
                logger.error(f"Error getting info for table {table_name}: {e}")
                table_info.append({
                    "name": table_name,
                    "error": str(e)
                })
        
        return {"tables": table_info}
        
    except Exception as e:
        logger.error(f"Error listing tables: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error listing tables: {str(e)}")

@app.get("/")
async def root():
    return {"message": "DocuQuery API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True) 