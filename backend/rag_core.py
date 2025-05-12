import os
import duckdb
import chromadb
import logging
import re
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings, FakeEmbeddings
import pandas as pd
from pathlib import Path
import json
import uuid
from langchain.retrievers import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import LLMChainExtractor
from typing import Optional, Dict, Any, List, TYPE_CHECKING

# Configure logging
logger = logging.getLogger(__name__)

# Conditional import for spacy to avoid errors if not installed
try:
    import spacy # type: ignore
    nlp = spacy.load("en_core_web_sm")
    spacy_available = True
    logger.info("spaCy NER model loaded successfully")
except (ImportError, OSError) as e: # Catch OSError for model loading issues
    spacy_available = False
    nlp = None # Ensure nlp is defined
    logger.warning(f"spaCy or en_core_web_sm model not available: {e}. NER features might be limited.")


# Path to Chroma DB
CHROMA_DB_PATH = os.environ.get("CHROMA_DB_PATH", "./chroma_db")
logger.info(f"Using Chroma DB path: {CHROMA_DB_PATH}")

# Initialize embeddings model
embeddings: Any # Define type for embeddings
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_API_KEY environment variable not set. Using local HuggingFace embeddings.")
        try:
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            logger.info("Using HuggingFace embeddings model (all-MiniLM-L6-v2)")
        except Exception as hf_error:
            logger.error(f"Error initializing HuggingFace embeddings: {hf_error}. Using FakeEmbeddings.")
            embeddings = FakeEmbeddings(size=384) # all-MiniLM-L6-v2 dim is 384
    else:
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
            logger.info("Using Google Generative AI Embeddings model (models/embedding-001)")
        except Exception as google_error:
            logger.error(f"Error initializing Google embeddings: {google_error}. Falling back to HuggingFace.")
            try:
                embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                logger.info("Using HuggingFace embeddings model as fallback.")
            except Exception as hf_fallback_error:
                logger.error(f"Error initializing HuggingFace fallback embeddings: {hf_fallback_error}. Using FakeEmbeddings.")
                embeddings = FakeEmbeddings(size=384)
except Exception as e_init_error:
    logger.error(f"Critical error initializing embeddings model: {e_init_error}. Using FakeEmbeddings.")
    embeddings = FakeEmbeddings(size=384)


# --- DuckDB Connection Management ---
# Initialize DuckDB connection - THIS IS THE SHARED CONNECTION
# It's crucial that this is the *only* place where duckdb.connect(':memory:') is called
# to ensure all operations use the same in-memory database.
try:
    shared_db_conn = duckdb.connect(database=":memory:", read_only=False)
    logger.info("RAG Core: Shared DuckDB connection established to :memory:")
except Exception as e:
    logger.error(f"RAG Core: CRITICAL Error connecting to shared DuckDB: {e}")
    # Depending on the application's needs, you might want to exit or use a fallback
    # For now, we'll let it raise, as a non-functional DB is a major issue.
    raise

def get_shared_db_connection() -> duckdb.DuckDBPyConnection:
    """Returns the shared DuckDB connection."""
    global shared_db_conn
    if shared_db_conn is None or shared_db_conn.closed: # Check if connection was closed
        logger.warning("Shared DuckDB connection was closed or None. Re-initializing.")
        shared_db_conn = duckdb.connect(database=":memory:", read_only=False)
    return shared_db_conn
# --- End DuckDB Connection Management ---


# Initialize Chroma client - lazily in get_chroma_collection()
chroma_client: Optional[chromadb.PersistentClient] = None
collection_name = "docuquery"


def get_chroma_collection():
    """Get or create Chroma collection, ensuring client is initialized."""
    global chroma_client
    try:
        if chroma_client is None:
            os.makedirs(CHROMA_DB_PATH, exist_ok=True)
            logger.info(f"Initializing Chroma client with path: {CHROMA_DB_PATH}")
            try:
                chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
                logger.info("Chroma client initialized successfully.")
            except Exception as client_init_error:
                logger.error(f"Error initializing Chroma PersistentClient: {client_init_error}")
                return None
            
        langchain_chroma_collection = Chroma(
                client=chroma_client,
                collection_name=collection_name,
                embedding_function=embeddings
            )
        logger.info(f"Chroma collection '{collection_name}' accessed/created via Langchain wrapper.")
        return langchain_chroma_collection
    
    except Exception as e:
        logger.error(f"Error getting Chroma collection: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def extract_entities_and_sections(text: str, metadata: Optional[Dict[str, Any]] = None) -> tuple[Dict[str, List[str]], Dict[str, str]]:
    """Extract named entities (PERSON) and potential sections from text."""
    entities: Dict[str, List[str]] = {"PERSON": []}
    sections: Dict[str, str] = {} 
    
    if not text: return entities, sections

    section_patterns = [
        (r"^\s*#{1,6}\s+(.+?)\s*#*\s*$", "markdown"),
        (r"^\s*([A-Z0-9][A-Z0-9\s]{3,48}[A-Z0-9])\s*(?::|\n)", "uppercase"),
        (r"^\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,5})\s*:", "title_case_colon")
    ]
    for line in text.splitlines():
        for pattern, p_type in section_patterns:
            match = re.match(pattern, line.strip())
            if match:
                section_name = match.group(1).strip()
                if section_name and 2 < len(section_name) < 100:
                    sections[section_name] = p_type
                    break 

    if not spacy_available or nlp is None: # Check if nlp is loaded
        if metadata and ("resume" in metadata.get("source", "").lower() or "cv" in metadata.get("source", "").lower()):
            for line in text.split('\n')[:5]: 
                name_match = re.match(r"^\s*([A-Z][a-z'-]+(?:\s+[A-Z][a-z'-]*\.?){1,3})\s*$", line.strip())
                if name_match:
                    potential_name = name_match.group(1).strip()
                    if len(potential_name.split()) >= 2:
                        entities["PERSON"].append(potential_name)
                        break 
        return entities, sections

    try:
        doc_spacy = nlp(text)
        for ent in doc_spacy.ents:
            if ent.label_ == "PERSON" and ent.text.strip() not in entities["PERSON"]:
                if len(ent.text.strip().split()) > 1 and len(ent.text.strip()) > 3:
                     entities["PERSON"].append(ent.text.strip())
    except Exception as e_spacy:
        logger.warning(f"Error during spaCy entity extraction: {e_spacy}")
        
    return entities, sections


def register_duckdb_table(df: pd.DataFrame, table_name_base: str) -> Optional[str]:
    """Register a pandas DataFrame as a DuckDB table using the shared db_conn."""
    db_conn = get_shared_db_connection() # Get the shared connection
    sanitized_name = table_name_base # Initialize for logging in case of early failure
    try:
        sanitized_name = re.sub(r'[^a-zA-Z0-9_]', '_', table_name_base)
        if not re.match(r'^[a-zA-Z_]', sanitized_name):
            sanitized_name = "_" + sanitized_name
        
        # Basic SQL keyword check
        sql_keywords = {"SELECT", "TABLE", "FROM", "WHERE", "UPDATE", "DELETE", "INSERT", "CREATE", "ALTER", "DROP", "INDEX", "VIEW"}
        if sanitized_name.upper() in sql_keywords:
            sanitized_name += "_data"
        
        # Check if table already exists with this name to avoid errors or silent replacement
        # Depending on desired behavior, you might want to rename, drop, or skip.
        # For now, let's make it unique if it exists to avoid conflicts.
        temp_sanitized_name = sanitized_name
        counter = 1
        existing_tables_df = db_conn.execute("SHOW TABLES").fetchdf()
        existing_tables = list(existing_tables_df['name']) if not existing_tables_df.empty else []

        while temp_sanitized_name in existing_tables:
            logger.warning(f"Table '{temp_sanitized_name}' already exists. Attempting to rename.")
            temp_sanitized_name = f"{sanitized_name}_{counter}"
            counter += 1
        sanitized_name = temp_sanitized_name


        # Data type sanitization for DuckDB
        for col in df.columns:
            if df[col].dtype.name == 'object':
                # Attempt to convert mixed-type object columns more carefully
                try:
                    # If all non-NaN are strings, keep as string
                    if all(isinstance(x, str) for x in df[col].dropna()):
                        pass # Already suitable or will be cast by astype(str) if needed
                    # If it contains lists, dicts, or other complex objects, convert to string
                    elif any(isinstance(x, (list, dict, set)) for x in df[col].dropna()):
                        df[col] = df[col].astype(str)
                        logger.info(f"Converted complex object column '{col}' to string for DuckDB.")
                except Exception as e: # Broad exception if introspection fails
                     logger.warning(f"Could not reliably inspect object column '{col}', converting to string. Error: {e}")
                     df[col] = df[col].astype(str)
            
            if pd.api.types.is_datetime64_any_dtype(df[col]) and getattr(df[col].dt, 'tz', None) is not None:
                try:
                    df[col] = df[col].dt.tz_localize(None) # Convert to timezone-naive by removing tz info
                    logger.info(f"Converted timezone-aware column '{col}' to naive for DuckDB.")
                except TypeError: # Already naive
                    pass
                except Exception as tz_err:
                    logger.warning(f"Could not convert timezone for column '{col}': {tz_err}. Converting to string.")
                    df[col] = df[col].astype(str)
        
        db_conn.register(sanitized_name, df)
        result = db_conn.execute(f"SELECT COUNT(*) FROM \"{sanitized_name}\"").fetchone()
        if result is None or result[0] != len(df): # Check count matches DataFrame length
            logger.error(f"Failed to verify table registration for '{sanitized_name}' (count mismatch or None)")
            return None
        logger.info(f"Successfully registered table '{sanitized_name}' with {result[0]} rows in shared DuckDB.")
        return sanitized_name
            
    except Exception as e:
        logger.error(f"Error registering DuckDB table '{table_name_base}' (sanitized to '{sanitized_name}'): {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def embed(documents: List[Document], file_id: str) -> int:
    """Process documents (enrich metadata) and add them to Chroma vector store."""
    try:
        logger.info(f"Embedding: Processing {len(documents)} documents for file_id: {file_id}")
        if not documents:
            logger.warning(f"Embedding: No documents provided for file_id: {file_id}")
            return 0
            
        valid_documents_for_chroma = []
        
        for i, doc in enumerate(documents):
            if not hasattr(doc, 'page_content') or not doc.page_content or not doc.page_content.strip():
                doc_source = doc.metadata.get('source', 'unknown_source') if hasattr(doc, 'metadata') and doc.metadata else 'unknown_source_no_meta'
                logger.warning(f"Embedding: Document {i} from '{doc_source}' (file_id: {file_id}) has no content, skipping.")
                continue
                
            if not hasattr(doc, 'metadata') or doc.metadata is None:
                doc.metadata = {}
            
            doc.metadata['file_id'] = file_id
            
            entities, sections_dict = extract_entities_and_sections(doc.page_content, doc.metadata)
            doc.metadata['persons'] = entities.get("PERSON", [])
            doc.metadata['sections'] = list(sections_dict.keys())

            sanitized_meta = {}
            for k, v in doc.metadata.items():
                if isinstance(v, (str, int, float, bool)) or v is None:
                    sanitized_meta[k] = v
                elif isinstance(v, list): 
                    sanitized_meta[k] = [str(item) if not isinstance(item, (str, int, float, bool, type(None))) else item for item in v]
                else: 
                    sanitized_meta[k] = str(v)
            doc.metadata = sanitized_meta
            
            valid_documents_for_chroma.append(doc)
        
        if not valid_documents_for_chroma:
            logger.warning(f"Embedding: No valid documents to add to Chroma for file_id: {file_id}")
            return 0

        collection = get_chroma_collection()
        if collection is None:
            logger.error(f"Embedding: Failed to get Chroma collection for file_id: {file_id}. Documents not embedded.")
            return 0
        
        # Consider batching for very large lists of documents
        collection.add_documents(valid_documents_for_chroma)
        total_chunks_embedded = len(valid_documents_for_chroma)
        logger.info(f"Embedding: Successfully added {total_chunks_embedded} chunks to Chroma for file_id: {file_id}")
        
        return total_chunks_embedded
    
    except Exception as e:
        logger.error(f"Error in embed function for file_id {file_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

def execute_sql_query_rag(query: str) -> Dict[str, Any]:
    """Execute a SQL query against the shared DuckDB in-memory database.
       This function is intended to be called from rag_core or by modules
       that have access to the shared DB connection via get_shared_db_connection().
    """
    db_conn = get_shared_db_connection()
    try:
        logger.info(f"RAG Core executing SQL: {query}")
        query_result = db_conn.execute(query)
        result_data = query_result.fetchall()
        columns = [desc[0] for desc in query_result.description]
        
        output_data = [dict(zip(columns, row)) for row in result_data]

        logger.info(f"SQL query '{query}' executed by RAG core returned {len(output_data)} results.")
        return {
            "type": "sql_result",
            "data": output_data,
            "query": query,
            "columns": columns
        }
    except Exception as e:
        logger.error(f"RAG Core SQL Error for query '{query}': {str(e)}")
        error_msg = str(e)
        suggestion = ""
        
        missing_table_match = re.search(r"Table with name (\w+|\".*?\") does not exist", error_msg, re.IGNORECASE)
        if not missing_table_match:
            missing_table_match = re.search(r"Catalog Error: Table with name (.*?) does not exist!", error_msg, re.IGNORECASE)

        if missing_table_match:
            missing_table = missing_table_match.group(1).replace("\"", "")
            try:
                tables_fetch_df = db_conn.execute("SHOW TABLES").fetchdf()
                available_tables = list(tables_fetch_df['name']) if not tables_fetch_df.empty else []
                if available_tables:
                    suggestion = f" Did you mean one of these? {', '.join(available_tables)}."
                else:
                    suggestion = " No tables are currently registered in the shared DB. Try uploading a CSV or Excel file."
            except Exception as list_table_err:
                logger.error(f"Could not list tables for error suggestion: {list_table_err}")
            error_msg = f"Table '{missing_table}' not found.{suggestion}"
        
        return {
            "type": "error",
            "message": f"SQL Error: {error_msg}",
            "query": query
        }

def original_retrieve(query: str, k=5, metadata_filter=None):
    """Original retrieve function - retrieves relevant documents or execute SQL query"""
    try:
        logger.info(f"Retrieval: Processing query: '{query}' with filter: {metadata_filter}")
        
        if query.strip().lower().startswith("select") and " from " in query.lower():
            logger.info("Retrieval: Query identified as SQL, executing directly via RAG core.")
            return execute_sql_query_rag(query) # Use the RAG core's SQL executor
        
        collection = get_chroma_collection()
        if collection is None:
            logger.error("Retrieval: Failed to get Chroma collection.")
            return {"type": "error", "message": "Failed to access vector database"}
        
        docs = collection.similarity_search(query=query, k=k, filter=metadata_filter)
        logger.info(f"Retrieval: Similarity search returned {len(docs)} documents.")
        
        return {"type": "documents", "data": docs}
        
    except Exception as e:
        logger.error(f"Error in original_retrieve function: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {"type": "error", "message": f"Error retrieving results: {str(e)}"}

def retrieve_with_compression(query: str, metadata_filter: Optional[Dict[str, Any]] = None, k: int = 5) -> Dict[str, Any]:
    """Enhanced retrieval with contextual compression."""
    try:
        initial_k = k * 2 
        result = original_retrieve(query, k=initial_k, metadata_filter=metadata_filter)
        
        if result["type"] != "documents" or not result.get("data"):
            logger.info("Compression: No documents from original retrieval or error. Skipping compression.")
            return result 
            
        docs = result["data"]
        logger.info(f"Compression: Retrieved {len(docs)} documents for potential compression.")
        
        comp_llm = None
        api_key = os.getenv("GOOGLE_API_KEY")
        if api_key:
            from langchain_google_genai import ChatGoogleGenerativeAI
            comp_llm = ChatGoogleGenerativeAI(
                model="gemini-pro", 
                temperature=0,
                google_api_key=api_key
            )
            logger.info("Compression: Using Google Gemini-Pro for LLMChainExtractor.")
        else:
            from langchain_core.language_models.fake import FakeListLLM
            comp_llm = FakeListLLM(responses=["No specific relevant context found."]) 
            logger.warning("Compression: No Google API key. LLMChainExtractor using FakeListLLM; compression may be limited.")
        
        compressor = LLMChainExtractor.from_llm(comp_llm)
        
        from langchain.schema import BaseRetriever # Moved import here
        class ListRetriever(BaseRetriever):
            documents: List[Document]
            def _get_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
                return self.documents
            async def _aget_relevant_documents(self, query: str, *, run_manager=None) -> List[Document]:
                return self.documents

        base_retriever = ListRetriever(documents=docs)

        compression_retriever = ContextualCompressionRetriever(
            base_compressor=compressor,
            base_retriever=base_retriever
        )
        
        compressed_docs = compression_retriever.get_relevant_documents(query)
        logger.info(f"Compression: Retrieved {len(compressed_docs)} compressed documents.")
        
        final_docs = compressed_docs if compressed_docs else docs 
        return {"type": "documents", "data": final_docs[:k]}
            
    except Exception as compression_error:
        logger.warning(f"Error during document compression: {compression_error}. Falling back to standard retrieval.")
        return original_retrieve(query, k=k, metadata_filter=metadata_filter)

def retrieve(query: str, k=5, metadata_filter=None):
    """Main retrieval function, attempting compression if feasible."""
    if query.strip().lower().startswith("select") and " from " in query.lower():
        logger.info("Retrieve: SQL query detected. Using original_retrieve (which calls RAG SQL executor).")
        return original_retrieve(query, k, metadata_filter)
    
    use_compression = bool(os.getenv("GOOGLE_API_KEY"))

    if use_compression:
        logger.info("Retrieve: Attempting retrieval with compression.")
        try:
            comp_result = retrieve_with_compression(query, metadata_filter, k)
            if comp_result["type"] == "documents" and comp_result.get("data"):
                return comp_result
            else:
                logger.warning("Retrieve: Compression did not yield results or failed. Falling back to standard retrieval.")
        except Exception as e:
            logger.error(f"Retrieve: Error in retrieve_with_compression: {e}. Falling back.")
    else:
        logger.info("Retrieve: Compression not enabled. Using standard retrieval.")
    
    return original_retrieve(query, k, metadata_filter)
