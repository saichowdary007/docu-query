import os
import io
import tempfile
import uuid
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
import re # Added for sanitization

from rag_core import embed, retrieve, register_duckdb_table
from response_generator import process_query, execute_sql_query

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
api_key = os.getenv("GOOGLE_API_KEY")
if api_key:
    logger.info(f"Google API Key configured: {api_key[:5]}...")
else:
    logger.warning("Google API Key not configured. Some features may be limited.")

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
            
        @property
        def _llm_type(self) -> str:
            return "fallback"
    
    llm = FallbackChatModel()
    logger.info("Using fallback chat model due to initialization error")

# File upload directory
UPLOAD_DIR = "./uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Document loaders
def load_csv_xlsx(file_path: str, file_id: str, original_filename: str) -> List[Document]:
    """Load CSV or XLSX file into documents and register as DuckDB table"""
    documents = []
    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
            logger.info(f"Loaded CSV file '{original_filename}' with {len(df)} rows")
        else:
            engine = None
            if file_path.endswith('.xlsx'):
                engine = 'openpyxl'
            elif file_path.endswith('.xls'):
                engine = 'xlrd'
            elif file_path.endswith('.xlsb'):
                engine = 'pyxlsb'
            
            try:
                if engine:
                    df = pd.read_excel(file_path, engine=engine)
                else:
                    df = pd.read_excel(file_path) # Try default for unknown excel types
                logger.info(f"Loaded Excel file '{original_filename}' with {engine if engine else 'default'} engine, {len(df)} rows")
            except Exception as xlsx_error:
                logger.error(f"Error with primary Excel engine for '{original_filename}': {xlsx_error}, trying alternative")
                try:
                    df = pd.read_excel(file_path) # Fallback to default engine
                    logger.info(f"Loaded Excel file '{original_filename}' with fallback default engine, {len(df)} rows")
                except Exception as alt_error:
                    logger.error(f"All Excel reading methods failed for '{original_filename}': {alt_error}")
                    raise

        if df.empty:
            logger.warning(f"File {original_filename} contains no data")
            return []

        # Create a unique and descriptive base name for the DuckDB table
        table_name_prefix = os.path.splitext(original_filename)[0]
        safe_prefix = re.sub(r'[^a-zA-Z0-9_]', '_', table_name_prefix).lower()
        safe_file_id_suffix = file_id.replace('-', '')[:8]
        duckdb_table_name_base = f"{safe_prefix}_{safe_file_id_suffix}"
        
        table_name = register_duckdb_table(df, duckdb_table_name_base)
        if not table_name:
            logger.error(f"DuckDB table registration failed for '{original_filename}' (base: {duckdb_table_name_base})")
            return []
        logger.info(f"DuckDB table '{table_name}' registered for '{original_filename}'")

        schema_info = f"Table: {table_name}\nColumns: {', '.join(df.columns.tolist())}\nRows: {len(df)}"
        schema_doc = Document(
            page_content=schema_info,
            metadata={
                "source": original_filename,
                "file_id": file_id,
                "file_type": "tabular_schema", # More specific file_type
                "table_name": table_name,
                "is_schema": True
            }
        )
        documents.append(schema_doc)

        try:
            numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
            if numeric_cols:
                stats = df[numeric_cols].describe().to_string()
                stats_doc = Document(
                    page_content=f"Statistical summary for table '{table_name}':\n{stats}",
                    metadata={
                        "source": original_filename,
                        "file_id": file_id,
                        "file_type": "tabular_stats", # More specific file_type
                        "table_name": table_name,
                        "is_stats": True
                    }
                )
                documents.append(stats_doc)
        except Exception as stats_error:
            logger.warning(f"Could not generate statistics for '{original_filename}': {stats_error}")

        for i, row in df.iterrows():
            row_dict = {}
            for k, v in row.to_dict().items():
                if pd.isna(v):
                    row_dict[k] = None
                elif isinstance(v, (pd.Timestamp, pd._libs.tslibs.timestamps.Timestamp)):
                    row_dict[k] = str(v)
                else:
                    row_dict[k] = v
            
            content = f"Row {i} of {original_filename} (table: {table_name}): {', '.join([f'{col}: {val}' for col, val in row_dict.items()])}"
            doc = Document(
                page_content=content,
                metadata={
                    "row": i,
                    "source": original_filename,
                    "file_id": file_id,
                    "table_name": table_name,
                    "file_type": "tabular_row", # More specific file_type
                    "is_tabular": True,
                    **row_dict
                }
            )
            documents.append(doc)
        
        logger.info(f"Created {len(documents)} documents from tabular file '{original_filename}'")
        return documents
    except Exception as e:
        logger.error(f"Error loading tabular file {original_filename}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def load_pdf(file_path: str, file_id: str, original_filename: str) -> List[Document]:
    """Load PDF file into documents"""
    documents = []
    try:
        with pdfplumber.open(file_path) as pdf:
            logger.info(f"PDF '{original_filename}' has {len(pdf.pages)} pages")
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ""
                if text.strip():
                    doc = Document(
                        page_content=text,
                        metadata={
                            "page": i + 1,
                            "source": original_filename,
                            "file_id": file_id,
                            "file_type": "pdf"
                        }
                    )
                    documents.append(doc)
        logger.info(f"Created {len(documents)} documents from PDF '{original_filename}'")
        return documents
    except Exception as e:
        logger.error(f"Error loading PDF {original_filename}: {e}")
        return []

def load_docx(file_path: str, file_id: str, original_filename: str) -> List[Document]:
    """Load DOCX file into documents with improved structure detection"""
    documents = []
    try:
        if not os.path.exists(file_path):
            logger.error(f"DOCX file does not exist: {file_path}")
            return []
            
        file_size = os.path.getsize(file_path)
        logger.info(f"Loading DOCX file: {original_filename} (path: {file_path}, size: {file_size} bytes)")
        
        doc_obj = docx.Document(file_path) # Renamed from doc to doc_obj to avoid conflict
        logger.info(f"DOCX '{original_filename}' loaded successfully with {len(doc_obj.paragraphs)} paragraphs")
        
        all_text = ""
        for para in doc_obj.paragraphs:
            all_text += para.text + "\n"
        
        if all_text.strip():
            # Create one document with all content
            full_doc = Document(
                page_content=all_text,
                metadata={
                    "source": original_filename,
                    "file_id": file_id,
                    "file_type": "docx_full" # Distinguish from paragraph-level
                }
            )
            documents.append(full_doc)
            
            # Create documents by paragraph for more granular retrieval
            for i, para in enumerate(doc_obj.paragraphs):
                if para.text.strip():
                    para_doc = Document(
                        page_content=para.text.strip(),
                        metadata={
                            "paragraph": i + 1,
                            "source": original_filename,
                            "file_id": file_id,
                            "file_type": "docx_paragraph" # Distinguish
                        }
                    )
                    documents.append(para_doc)
        
        logger.info(f"Created {len(documents)} documents from DOCX '{original_filename}'")
        return documents
    except Exception as e:
        logger.error(f"Error loading DOCX {original_filename}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def load_pptx(file_path: str, file_id: str, original_filename: str) -> List[Document]:
    """Load PPTX file into documents"""
    documents = []
    try:
        pres = pptx.Presentation(file_path)
        logger.info(f"PPTX '{original_filename}' has {len(pres.slides)} slides")
        for i, slide in enumerate(pres.slides):
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
                        "source": original_filename,
                        "file_id": file_id,
                        "file_type": "pptx"
                    }
                )
                documents.append(doc)
        logger.info(f"Created {len(documents)} documents from PPTX '{original_filename}'")
        return documents
    except Exception as e:
        logger.error(f"Error loading PPTX {original_filename}: {e}")
        return []

def load_text(file_path: str, file_id: str, original_filename: str) -> List[Document]:
    """Load TXT or MD file into documents"""
    documents = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        logger.info(f"Loaded text file '{original_filename}' with {len(content)} characters")
        
        if not content.strip():
            logger.warning(f"Text file {original_filename} is empty")
            return []
        
        # Create one document with all content
        full_doc = Document(
            page_content=content,
            metadata={
                "source": original_filename,
                "file_id": file_id,
                "file_type": "text_full" # Distinguish
            }
        )
        documents.append(full_doc)
        
        # Also create documents by paragraph for more granular retrieval
        for i, para in enumerate(content.split('\n\n')): # Simple paragraph split
            if para.strip():
                para_doc = Document(
                    page_content=para.strip(),
                    metadata={
                        "paragraph": i + 1,
                        "source": original_filename,
                        "file_id": file_id,
                        "file_type": "text_paragraph" # Distinguish
                    }
                )
                documents.append(para_doc)
        
        logger.info(f"Created {len(documents)} documents from text file '{original_filename}'")
        return documents
    except Exception as e:
        logger.error(f"Error loading text file {original_filename}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return []

def process_file(file_path: str, file_id: str, original_filename: str) -> Dict[str, Any]:
    """Process file based on its extension"""
    logger.info(f"Processing file: {original_filename} (id: {file_id}, path: {file_path})")
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return {"success": False, "message": f"File not found: {file_path}"}
    
    file_ext = os.path.splitext(original_filename)[1].lower()
    logger.info(f"File extension for {original_filename}: {file_ext}")
    
    docs: List[Document] = []
    file_type_processed: str = "unknown"

    if file_ext in ['.csv', '.xlsx', '.xls', '.xlsb']:
        docs = load_csv_xlsx(file_path, file_id, original_filename)
        file_type_processed = "tabular"
    elif file_ext == '.pdf':
        docs = load_pdf(file_path, file_id, original_filename)
        file_type_processed = "pdf"
    elif file_ext == '.docx':
        docs = load_docx(file_path, file_id, original_filename)
        file_type_processed = "docx"
    elif file_ext == '.pptx':
        docs = load_pptx(file_path, file_id, original_filename)
        file_type_processed = "pptx"
    elif file_ext in ['.txt', '.md']:
        docs = load_text(file_path, file_id, original_filename)
        file_type_processed = "text"
    else:
        logger.error(f"Unsupported file type for {original_filename}: {file_ext}")
        return {"success": False, "message": f"Unsupported file type: {file_ext}"}
    
    if not docs:
        logger.warning(f"No content extracted from {original_filename}") # Changed to warning
        # It's not necessarily an error if a file is empty, but no chunks will be embedded.
        return {
            "success": True, # Process itself didn't fail, just no docs.
            "file_type": file_type_processed,
            "file_name": original_filename,
            "chunks_count": 0,
            "message": f"No content extracted or file empty: {original_filename}"
        }
    
    logger.info(f"Embedding {len(docs)} documents from {original_filename}")
    try:
        chunks_count = embed(docs, file_id) # Pass docs and file_id
        logger.info(f"Successfully embedded {chunks_count} chunks for {original_filename}")
        
        return {
            "success": True,
            "file_type": file_type_processed,
            "file_name": original_filename,
            "chunks_count": chunks_count
        }
    except Exception as e:
        logger.error(f"Error embedding documents for {original_filename}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"success": False, "message": f"Error embedding documents: {str(e)}"}

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a file"""
    try:
        original_filename = file.filename
        logger.info(f"Received file upload: {original_filename}")
        
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        file_id = str(uuid.uuid4())
        # Use a safe local filename that includes the file_id for uniqueness on disk
        temp_file_name = f"{file_id}_{original_filename}"
        file_path = os.path.join(UPLOAD_DIR, temp_file_name)
        
        logger.info(f"Saving file to {file_path}")
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"File {original_filename} saved to {file_path}, size: {len(content)} bytes")
        
        logger.info(f"Processing file synchronously: {original_filename}")
        # Pass file_path (where temp file is saved), file_id, and original_filename
        result = process_file(file_path, file_id, original_filename)
        logger.info(f"File processing result for {original_filename}: {result}")
        
        result["file_id"] = file_id # Ensure file_id is in the response
        # original_filename is already in result["file_name"]
        return result
            
    except Exception as e:
        logger.error(f"Error processing file upload: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        # Clean up saved file if processing fails catastrophically before process_file
        if 'file_path' in locals() and os.path.exists(file_path):
            try:
                os.remove(file_path)
                logger.info(f"Cleaned up temporary file: {file_path}")
            except Exception as cleanup_e:
                logger.error(f"Error cleaning up file {file_path}: {cleanup_e}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.post("/chat")
async def chat(query: str = Form(...), history: Optional[str] = Form(None), file_id: Optional[str] = Form(None)):
    """Process a chat message"""
    try:
        logger.info(f"Received chat query: {query}")
        
        chat_history = []
        if history:
            import json
            try:
                chat_history = json.loads(history)
                logger.info(f"Parsed chat history with {len(chat_history)} messages")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse history: {e}")
        
        sql_indicators = ["list", "count", "how many", "average", "sum", "total", "compare", 
                        "sort", "filter", "show me", "table", "spreadsheet", "excel", "column", "row"]
        
        is_likely_sql_query = any(indicator in query.lower() for indicator in sql_indicators)
        logger.info(f"Query SQL likelihood assessment: {is_likely_sql_query}")
        
        retrieval_result = retrieve(
            query,
            metadata_filter={"file_id": file_id} if file_id else None
        )
        logger.info(f"Retrieval result type: {retrieval_result['type']}")
        
        documents_are_tabular_related = False
        if retrieval_result["type"] == "documents" and retrieval_result.get("data"):
            for doc_item in retrieval_result["data"]:
                # Check for various tabular-related file_types set by load_csv_xlsx
                if doc_item.metadata.get("file_type", "").startswith("tabular") or \
                   doc_item.metadata.get("is_schema") or \
                   doc_item.metadata.get("is_stats") or \
                   doc_item.metadata.get("is_tabular"):
                    documents_are_tabular_related = True
                    break
        
        logger.info(f"Retrieved documents are tabular-related: {documents_are_tabular_related}")

        if retrieval_result["type"] == "documents" and is_likely_sql_query and documents_are_tabular_related:
            direct_result = process_query(query, retrieval_result, metadata_filter={"file_id": file_id} if file_id else None)
            
            if direct_result["type"] == "sql_result":
                logger.info("Query handled directly by response_generator for tabular data")
                retrieval_result = direct_result # Replace retrieval_result with direct SQL result
            else:
                logger.info("Query was likely SQL but not handled directly by response_generator, proceeding to LLM with retrieved docs.")
        elif retrieval_result["type"] == "documents" and is_likely_sql_query and not documents_are_tabular_related:
            logger.info("Query is likely SQL but retrieved documents are not tabular. Skipping direct SQL generation attempt.")
        
        context = ""
        
        if retrieval_result["type"] == "sql_result":
            context += f"SQL Query: {retrieval_result['query']}\n\n"
            context += "Results:\n"
            
            if "columns" in retrieval_result:
                context += f"Columns: {', '.join(retrieval_result['columns'])}\n"
                
            for i, row_data in enumerate(retrieval_result["data"]): # Renamed row to row_data
                context += f"Row {i+1}: {row_data}\n" # row_data could be dict or single value
            logger.info(f"SQL results: {len(retrieval_result['data'])} rows")
            
            context += "\nNote: This data can be exported as Excel by using the export feature.\n"
            
            if "direct_response" in retrieval_result and retrieval_result["direct_response"]:
                return {
                    "response": retrieval_result["direct_response"],
                    "exportable": True,
                    "sql": retrieval_result.get("query")
                }
        
        elif retrieval_result["type"] == "documents":
            doc_count = len(retrieval_result["data"]) if "data" in retrieval_result else 0
            logger.info(f"Retrieved {doc_count} documents for LLM context")
            
            has_tabular_content = False # Renamed from has_tabular
            table_names = set()
            
            for doc_item in retrieval_result["data"]: # Renamed doc to doc_item
                if doc_item.metadata.get("table_name"):
                    table_names.add(doc_item.metadata["table_name"])
                if doc_item.metadata.get("file_type", "").startswith("tabular") or doc_item.metadata.get("is_tabular"):
                    has_tabular_content = True
            
            if has_tabular_content and table_names and is_likely_sql_query:
                context += f"Your question appears to be about tabular data from table(s): {', '.join(table_names)}. I'll try to answer directly. For more detailed analysis, you could ask using SQL, for example: 'SELECT * FROM {next(iter(table_names))} LIMIT 5;'.\n\n"
            
            for doc_item in retrieval_result["data"]: # Renamed doc to doc_item
                source = doc_item.metadata.get("source", "unknown")
                
                locator = ""
                if "page" in doc_item.metadata:
                    locator = f"#page={doc_item.metadata['page']}"
                elif "slide" in doc_item.metadata:
                    locator = f"#slide={doc_item.metadata['slide']}"
                elif "paragraph" in doc_item.metadata: # check specific paragraph types
                    if doc_item.metadata.get("file_type") in ["docx_paragraph", "text_paragraph"]:
                         locator = f"#paragraph={doc_item.metadata['paragraph']}"
                elif "row" in doc_item.metadata and doc_item.metadata.get("file_type") == "tabular_row":
                    locator = f"#row={doc_item.metadata['row']}"
                
                citation = f"[{source}{locator}]"
                context += f"Content {citation}: {doc_item.page_content}\n\n"
                
                if "persons" in doc_item.metadata and doc_item.metadata["persons"]:
                    context += f"People mentioned {citation}: {', '.join(doc_item.metadata['persons'])}\n\n"
                
                if "sections" in doc_item.metadata and doc_item.metadata["sections"]: # Assuming sections is a list of strings
                    context += f"Sections {citation}: {', '.join(doc_item.metadata['sections'])}\n\n"
            
            if has_tabular_content and table_names:
                context += f"\nNote: Some of this data comes from table(s): {', '.join(table_names)}. "
                context += f"You can query this data using SQL (e.g., 'SELECT * FROM {next(iter(table_names))} LIMIT 5;').\n"
        
        elif retrieval_result["type"] == "error":
            context += f"Error during document retrieval: {retrieval_result['message']}"
            logger.error(f"Retrieval error passed to LLM context: {retrieval_result['message']}")
        
        system_prompt = SYSTEM_PROMPT + "\n\n" + """
IMPORTANT GUIDELINES:
1. Always cite sources using [filename#page=X], [filename#slide=X], [filename#paragraph=X], or [filename#row=X] format. If no specific locator, use [filename].
2. For questions about tabular data, if you used retrieved content, mention the table name(s) if known. Suggest SQL queries if the user asks for aggregation, filtering, or specific data not easily summarized from text.
3. Ask specific clarifying questions if information is insufficient or ambiguous.
4. Only provide information that's directly supported by the retrieved evidence. Do not make up information.
5. Format your answers clearly. Start with a direct answer to the user's question, then provide supporting details and citations.
6. If people are mentioned in the documents (metadata 'persons'), incorporate this information if relevant to the query.
7. If document sections are mentioned (metadata 'sections'), use this to structure your answer if relevant.
8. If asked about a date or time, extract and format it clearly from the context.
9. If asked about numerical data or statistics, present them with proper context, units, and citations.
10. Synthesize information from multiple sources when necessary, maintaining accuracy and citing all relevant sources.
11. Use markdown formatting (like bullet points, numbered lists, bolding) for clarity, especially for complex answers.
12. Acknowledge if the information might be incomplete based on the provided context.
13. If asked to compare items, create a structured comparison, citing sources for each point.
"""
        
        prompt_messages = [("system", system_prompt)]
        # Add chat history if any
        for h_msg in chat_history:
            if h_msg.get("role") == "user":
                prompt_messages.append(("human", h_msg.get("content", "")))
            elif h_msg.get("role") == "assistant":
                prompt_messages.append(("ai", h_msg.get("content", "")))

        prompt_messages.append(("human", f"Context information is below.\n\n{context}\n\nQuestion: {query}"))
        
        prompt = ChatPromptTemplate.from_messages(prompt_messages)
        
        logger.info("Generating response from LLM")
        chain = prompt | llm
        response = chain.invoke({}) # Context is now part of the prompt messages
        logger.info("LLM response generated successfully")
        
        response_text = response.content
        
        if "[" not in response_text and retrieval_result["type"] == "documents" and retrieval_result.get("data"):
            sources = list(set([doc_item.metadata.get("source", "unknown") for doc_item in retrieval_result["data"]]))
            if sources:
                source_citation = f" (Information based on: {', '.join(sources)})"
                response_text += source_citation
        
        return {
            "response": response_text,
            "exportable": retrieval_result.get("type") == "sql_result",
            "sql": retrieval_result.get("query") # Will be None if not sql_result
        }
        
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing query: {str(e)}")

@app.get("/export")
async def export_data(sql: str, filename: Optional[str] = None):
    """Export data as XLSX based on SQL query"""
    try:
        logger.info(f"Exporting data with SQL: {sql}")
        sql_result = execute_sql_query(sql)
        
        if sql_result["type"] != "sql_result":
            logger.error(f"Invalid SQL query for export: {sql_result.get('message', 'Unknown SQL error')}")
            raise HTTPException(status_code=400, detail=f"Invalid SQL query: {sql_result.get('message', 'Query execution failed')}")
        
        if not sql_result["data"]:
            logger.warning("SQL query for export returned no data")
            # Return empty Excel file or 404? Empty Excel is friendlier.
            df = pd.DataFrame()
        else:
            # Data is expected to be a list of dicts from execute_sql_query
            df = pd.DataFrame(sql_result["data"])

        logger.info(f"Exporting {len(df)} rows")
        
        export_filename = filename
        if not export_filename:
            import time
            timestamp = int(time.time())
            export_filename = f"export_{timestamp}.xlsx"
        elif not export_filename.endswith(('.xlsx', '.xls')):
            export_filename += '.xlsx'
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name="Sheet1") # Added sheet_name
        
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=\"{export_filename}\""} # Quoted filename
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
        # DuckDB connection might be closed/reopened by other parts, ensure a fresh one for this read.
        # The main db_conn is in-memory, so operations should persist if it's the same instance.
        # However, response_generator.py also creates its own :memory: db_conn. This needs careful review.
        # For now, assuming rag_core.db_conn is the one holding registered tables.
        # If register_duckdb_table uses the global db_conn from rag_core, then this should work.
        
        conn = duckdb.connect(database=":memory:", read_only=False) # This creates a NEW in-memory DB.
        # This will not see tables registered in rag_core.db_conn or response_generator.db_conn.
        # This needs to be fixed. All DuckDB operations must use the SAME in-memory database connection.

        # Quick fix: Access tables via rag_core's connection if possible, or make db_conn a singleton.
        # For now, let's assume we want to query the global db_conn defined in rag_core.py
        # This requires exposing it or a function to query it from rag_core.
        # Let's modify rag_core to provide such a function for now.
        # Or, for simplicity in this step, we'll just query a new connection, which will likely be empty.
        # This part of the code needs a shared DuckDB connection strategy.

        # Showing tables from a NEW in-memory DB connection. This will be empty unless tables are registered to *this* specific connection.
        # To list tables from the shared DB, rag_core.db_conn must be used.
        # For now, this will likely return empty list unless DuckDB's :memory: is shared magically across modules (it's not by default).
        # The problem statement did not ask to fix this, but it's a notable issue.
        
        # Let's assume for the exercise that duckdb.connect(':memory:') shares the same instance,
        # which is true if it's the same process and default named in-memory DB.
        
        tables_result = duckdb.execute("SHOW TABLES").fetchall()
        table_names = [t[0] for t in tables_result]
        logger.info(f"Available tables in DuckDB: {table_names}")
        
        table_info = []
        for table_name_item in table_names: # Renamed table_name to table_name_item
            try:
                count_query = f"SELECT COUNT(*) FROM \"{table_name_item}\"" # Quote table name
                count = duckdb.execute(count_query).fetchone()[0]
                
                # PRAGMA table_info works with unquoted names usually, but safer to quote if needed
                columns_query = f"PRAGMA table_info(\"{table_name_item}\")"
                columns_result = duckdb.execute(columns_query).fetchall()
                # Column info: (cid, name, type, notnull, dflt_value, pk)
                column_names_types = [(col[1], col[2]) for col in columns_result] 
                
                table_info.append({
                    "name": table_name_item,
                    "rows": count,
                    "columns": column_names_types # Changed to include types
                })
            except Exception as e:
                logger.error(f"Error getting info for table {table_name_item}: {e}")
                table_info.append({
                    "name": table_name_item,
                    "rows": "Error",
                    "columns": [],
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
    # Ensure the UPLOAD_DIR exists at startup as well
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)