import os
import duckdb
import chromadb
import logging
from langchain_core.documents import Document
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings, FakeEmbeddings

# Configure logging
logger = logging.getLogger(__name__)

# Path to Chroma DB
CHROMA_DB_PATH = os.environ.get("CHROMA_DB_PATH", "./chroma_db")
logger.info(f"Using Chroma DB path: {CHROMA_DB_PATH}")

# Initialize embeddings model
try:
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        logger.warning("GOOGLE_API_KEY environment variable not set. Using local embeddings.")
        # Use a local embedding model that doesn't require API keys
        try:
            embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
            logger.info("Using HuggingFace embeddings model")
        except Exception as e:
            logger.error(f"Error initializing HuggingFace embeddings: {e}")
            # Fallback to fake embeddings
            embeddings = FakeEmbeddings(size=768)
            logger.info("Using fake embeddings as fallback")
    else:
        # Use Google embeddings if API key is available
        try:
            import google.generativeai as genai
            
            # For older versions of langchain-google-genai
            try:
                from langchain_google_genai import GoogleGenerativeAIEmbeddings
                genai.configure(api_key=api_key)
                embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001", google_api_key=api_key)
                logger.info("Using Google embeddings model (older version)")
            except ImportError:
                # For newer versions
                try:
                    from langchain_google_genai import GoogleGenerativeAIEmbeddings
                    embeddings = GoogleGenerativeAIEmbeddings(
                        model="models/embedding-001", 
                        google_api_key=api_key
                    )
                    logger.info("Using Google embeddings model (newer version)")
                except Exception as e1:
                    logger.error(f"Error initializing Google embeddings (newer version): {e1}")
                    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                    logger.info("Using HuggingFace embeddings model as fallback")
        except Exception as e:
            logger.error(f"Error initializing Google embeddings: {e}")
            # Fallback to local embeddings
            try:
                embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
                logger.info("Using HuggingFace embeddings model as fallback")
            except Exception as e2:
                logger.error(f"Error initializing HuggingFace embeddings: {e2}")
                # Final fallback to fake embeddings
                embeddings = FakeEmbeddings(size=768)
                logger.info("Using fake embeddings as final fallback")
except Exception as e:
    logger.error(f"Error initializing embeddings model: {e}")
    # Use a simple embedding function for testing
    embeddings = FakeEmbeddings(size=768)
    logger.info("Using fake embeddings due to error")

# Initialize Chroma client - We'll initialize it lazily in get_chroma_collection()
chroma_client = None
collection_name = "docuquery"

# Initialize DuckDB connection
try:
    db_conn = duckdb.connect(database=":memory:", read_only=False)
    logger.info("DuckDB connection established")
except Exception as e:
    logger.error(f"Error connecting to DuckDB: {e}")
    raise

def get_chroma_collection():
    """Get or create Chroma collection"""
    global chroma_client
    
    try:
        # Initialize client if not already initialized
        if chroma_client is None:
            # Ensure the chroma db directory exists
            os.makedirs(CHROMA_DB_PATH, exist_ok=True)
            logger.info(f"Initializing Chroma client with path: {CHROMA_DB_PATH}")
            
            # Clear any existing database files to prevent schema inconsistencies
            import glob
            import shutil
            
            # Only clear if it's a fresh start
            db_files = glob.glob(os.path.join(CHROMA_DB_PATH, "*.sqlite"))
            if db_files:
                logger.info(f"Found existing Chroma database files: {db_files}")
            else:
                logger.info(f"No existing Chroma database files found. Creating fresh database.")
            
            # Initialize client
            try:
                chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
                logger.info("Chroma client initialized successfully")
            except Exception as e:
                logger.error(f"Error initializing Chroma client: {e}")
                # Try with a clean database directory
                try:
                    logger.info("Attempting to clear database directory and reinitialize")
                    for item in glob.glob(os.path.join(CHROMA_DB_PATH, "*")):
                        if os.path.isdir(item):
                            shutil.rmtree(item)
                        else:
                            os.remove(item)
                    
                    # Reinitialize client
                    chroma_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
                    logger.info("Successfully reinitialized Chroma client after clearing directory")
                except Exception as e2:
                    logger.error(f"Failed to reinitialize Chroma client: {e2}")
                    return None
        
        # Direct collection handling (without Langchain wrapper)
        try:
            # Get or create collection directly with ChromaDB
            try:
                raw_collection = chroma_client.get_or_create_collection(name=collection_name)
                logger.info(f"Successfully got or created collection: {collection_name}")
            except Exception as e:
                logger.error(f"Error getting or creating collection: {e}")
                return None
            
            # Create a direct return of the raw collection (don't use Langchain wrapper)
            from langchain_community.vectorstores import Chroma
            chroma_collection = Chroma(
                client=chroma_client,
                collection_name=collection_name,
                embedding_function=embeddings
            )
            logger.info(f"Successfully created Chroma collection wrapper")
            
            # Return the collection
            return chroma_collection
            
        except Exception as e:
            logger.error(f"Error with Chroma collection operations: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    except Exception as e:
        logger.error(f"Error getting Chroma collection: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return None

def simple_text_splitter(text, chunk_size=1000, chunk_overlap=200):
    """Simple text splitter that breaks text into chunks of specified size with overlap"""
    if not text:
        return []
    
    # Split text into paragraphs first
    paragraphs = text.split("\n\n")
    chunks = []
    current_chunk = ""
    
    for para in paragraphs:
        if len(current_chunk) + len(para) <= chunk_size:
            # Add paragraph to current chunk
            if current_chunk:
                current_chunk += "\n\n" + para
            else:
                current_chunk = para
        else:
            # Current chunk is full, save it
            if current_chunk:
                chunks.append(current_chunk)
            
            # Start new chunk with overlap from previous chunk
            if len(current_chunk) > chunk_overlap:
                # Get the last part of the previous chunk for overlap
                words = current_chunk.split()
                overlap_text = " ".join(words[-int(chunk_overlap/10):])  # Approximate overlap
                current_chunk = overlap_text + "\n\n" + para
            else:
                current_chunk = para
    
    # Add the last chunk if not empty
    if current_chunk:
        chunks.append(current_chunk)
    
    # Convert chunks to Document objects
    documents = []
    for i, chunk in enumerate(chunks):
        if chunk.strip():  # Only add non-empty chunks
            doc = Document(
                page_content=chunk,
                metadata={"chunk": i}
            )
            documents.append(doc)
    
    return documents

def embed(file_path, documents, metadata=None):
    """
    Add document chunks to Chroma vector store
    
    Args:
        file_path: Path to the original file
        documents: List of Document objects
        metadata: Additional metadata to add to all documents
    """
    try:
        logger.info(f"Starting embedding process for {len(documents)} documents from {file_path}")
        if not documents:
            logger.warning("No documents provided to embed function")
            return 0
            
        # Validate document content
        valid_documents = []
        for i, doc in enumerate(documents):
            if not hasattr(doc, 'page_content') or not doc.page_content or len(doc.page_content.strip()) == 0:
                logger.warning(f"Document {i} has no content, skipping")
                continue
                
            # Ensure metadata is properly initialized
            if not hasattr(doc, 'metadata') or doc.metadata is None:
                doc.metadata = {}
                
            # Add source to metadata
            doc.metadata["source"] = os.path.basename(file_path)
            
            # Add additional metadata if provided
            if metadata:
                doc.metadata.update(metadata)
                
            # Sanitize metadata to ensure all values are valid types
            sanitized_metadata = {}
            for k, v in doc.metadata.items():
                if isinstance(v, (str, int, float, bool)):
                    sanitized_metadata[k] = v
                elif isinstance(v, list):
                    # Convert lists to strings
                    sanitized_metadata[k] = ", ".join(str(item) for item in v)
                elif v is None:
                    # Skip None values
                    continue
                else:
                    # Convert other types to strings
                    sanitized_metadata[k] = str(v)
            
            # Replace metadata with sanitized version
            doc.metadata = sanitized_metadata
                
            valid_documents.append(doc)
            
        logger.info(f"Found {len(valid_documents)} valid documents with content")
        if not valid_documents:
            logger.warning("No valid documents to embed")
            return 0
        
        # Skip chunking for simplicity, just use the documents as is
        logger.info(f"Using {len(valid_documents)} documents directly without chunking")
        valid_chunks = valid_documents
        
        # Use a direct ChromaDB approach without Langchain
        try:
            # Ensure the chroma db directory exists
            os.makedirs(CHROMA_DB_PATH, exist_ok=True)
            
            # Create a fresh ChromaDB client
            try:
                direct_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
                logger.info("Created direct ChromaDB client successfully")
            except Exception as e:
                logger.error(f"Failed to create ChromaDB client: {e}")
                return 0
                
            # Get or create collection directly
            try:
                direct_collection = direct_client.get_or_create_collection(name="docuquery")
                logger.info(f"Successfully got or created collection 'docuquery' with direct client")
            except Exception as e:
                logger.error(f"Failed to get or create collection: {e}")
                return 0
                
            # Extract content and metadata
            texts = [doc.page_content for doc in valid_chunks]
            metadatas = [doc.metadata for doc in valid_chunks]
            ids = [f"doc-{i}-{hash(doc.page_content)}" for i, doc in enumerate(valid_chunks)]
            
            # Use the embeddings model to create embeddings
            try:
                # Test embeddings
                test_embedding = embeddings.embed_query("Test embedding")
                logger.info(f"Test embedding dimension: {len(test_embedding)}")
                    
                # Generate embeddings for all texts
                try:
                    embedding_vectors = embeddings.embed_documents(texts)
                    logger.info(f"Created {len(embedding_vectors)} embeddings for documents")
                except Exception as e:
                    logger.error(f"Failed to create embeddings for documents: {e}")
                    embedding_vectors = None
                    
                # Add to collection
                if embedding_vectors:
                    # Add with explicit embeddings
                    direct_collection.add(
                        documents=texts,
                        embeddings=embedding_vectors,
                        metadatas=metadatas,
                        ids=ids
                    )
                    logger.info(f"Successfully added {len(texts)} documents with embeddings")
                else:
                    # Add without explicit embeddings (let ChromaDB handle it)
                    direct_collection.add(
                        documents=texts,
                        metadatas=metadatas,
                        ids=ids
                    )
                    logger.info(f"Successfully added {len(texts)} documents without explicit embeddings")
                    
                # Verify addition
                count = direct_collection.count()
                logger.info(f"Collection now has {count} documents")
                return len(valid_chunks)
                
            except Exception as e:
                logger.error(f"Error in embedding process: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return 0
                
        except Exception as e:
            logger.error(f"Error accessing ChromaDB: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return 0
    
    except Exception as e:
        logger.error(f"Error in embed function: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 0

def register_duckdb_table(df, table_name="doc"):
    """Register a pandas DataFrame as a DuckDB table"""
    try:
        # Sanitize table name to be SQL-friendly
        import re
        table_name = re.sub(r'[^a-zA-Z0-9_]', '_', table_name)
        if not table_name or table_name[0].isdigit():
            table_name = "t_" + table_name
            
        # Check if table exists and drop it if it does
        try:
            db_conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            logger.info(f"Dropped existing table '{table_name}'")
        except Exception as e:
            logger.warning(f"Error dropping table '{table_name}': {e}")
            
        logger.info(f"Registering DuckDB table '{table_name}' with {len(df)} rows")
        
        # Normalize column names for SQL compatibility
        df.columns = [re.sub(r'[^a-zA-Z0-9_]', '_', col) for col in df.columns]
        
        # Remove duplicate columns if any
        duplicate_cols = df.columns[df.columns.duplicated()].tolist()
        if duplicate_cols:
            logger.warning(f"Found duplicate columns: {duplicate_cols}")
            for col in duplicate_cols:
                # Rename duplicates
                col_indices = [i for i, c in enumerate(df.columns) if c == col]
                for i, idx in enumerate(col_indices[1:], 1):
                    df.columns.values[idx] = f"{col}_{i}"
            logger.info(f"Renamed duplicate columns to: {[c for c in df.columns if c.endswith('_1') or c.endswith('_2')]}")
        
        # Register the DataFrame as a table
        db_conn.register(table_name, df)
        
        # Verify registration by checking row count
        try:
            count = db_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            logger.info(f"Successfully registered DuckDB table '{table_name}' with {count} rows")
            
            # Log sample data for debugging
            if count > 0:
                sample = db_conn.execute(f"SELECT * FROM {table_name} LIMIT 1").fetchall()
                logger.info(f"Sample data from '{table_name}': {sample}")
                
                # Log column names
                columns = db_conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                logger.info(f"Columns in '{table_name}': {[col[1] for col in columns]}")
        except Exception as e:
            logger.error(f"Error verifying table '{table_name}': {e}")
            
        return True
    except Exception as e:
        logger.error(f"Error registering DuckDB table: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def retrieve(query, k=5):
    """
    Retrieve relevant documents based on query
    
    Args:
        query: User query string
        k: Number of documents to retrieve
        
    Returns:
        If SQL query: DuckDB result rows
        Otherwise: List of relevant documents
    """
    try:
        logger.info(f"Retrieving documents for query: {query[:50]}...")
        
        # Check if query is a SQL query (more comprehensive check)
        sql_keywords = ["SELECT", "FROM", "WHERE", "JOIN", "GROUP BY", "ORDER BY", "HAVING", "LIMIT"]
        is_likely_sql = False
        
        # Check if the query starts with SELECT or contains multiple SQL keywords
        if query.strip().upper().startswith("SELECT "):
            is_likely_sql = True
        else:
            keyword_count = sum(1 for keyword in sql_keywords if keyword in query.upper())
            is_likely_sql = keyword_count >= 2
            
        if is_likely_sql:
            logger.info("Processing as SQL query")
            try:
                # Get available tables to help with error messages
                tables = db_conn.execute("SHOW TABLES").fetchall()
                table_names = [t[0] for t in tables]
                logger.info(f"Available tables: {table_names}")
                
                # Execute the query
                result = db_conn.execute(query).fetchall()
                column_names = db_conn.execute(query).description
                columns = [col[0] for col in column_names]
                
                # Convert to list of dicts for easier handling
                results_list = []
                for row in result:
                    # Handle non-serializable types
                    processed_row = []
                    for val in row:
                        if hasattr(val, 'to_dict'):
                            processed_row.append(val.to_dict())
                        elif isinstance(val, (set, frozenset)):
                            processed_row.append(list(val))
                        else:
                            processed_row.append(val)
                    
                    results_list.append(dict(zip(columns, processed_row)))
                
                logger.info(f"SQL query returned {len(results_list)} results")
                return {
                    "type": "sql_result",
                    "data": results_list,
                    "query": query,
                    "columns": columns
                }
            except Exception as e:
                logger.error(f"SQL Error: {str(e)}")
                
                # Provide more helpful error message
                error_msg = str(e)
                suggestion = ""
                
                if "no such table" in error_msg.lower():
                    # Extract the table name from the error message
                    import re
                    match = re.search(r"table\s+(\w+)", error_msg.lower())
                    missing_table = match.group(1) if match else "unknown"
                    
                    if table_names:
                        suggestion = f" Available tables are: {', '.join(table_names)}."
                    else:
                        suggestion = " No tables are currently available. Try uploading some Excel or CSV files first."
                        
                    error_msg = f"Table '{missing_table}' not found.{suggestion}"
                
                return {
                    "type": "error",
                    "message": f"SQL Error: {error_msg}",
                    "query": query
                }
        else:
            # Semantic search
            logger.info("Processing as semantic search")
            
            # Use direct ChromaDB client for consistency with embed function
            try:
                # Create client
                direct_client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
                logger.info("Created direct ChromaDB client successfully for retrieval")
                
                # Get collection if it exists
                try:
                    direct_collection = direct_client.get_collection(name="docuquery")
                    logger.info("Successfully got collection 'docuquery' for retrieval")
                except Exception as e:
                    logger.error(f"Collection doesn't exist: {e}")
                    return {
                        "type": "error",
                        "message": "I am unable to answer your question as I do not have access to any documents. Please upload documents first."
                    }
                    
                # Check if collection has documents
                count = direct_collection.count()
                logger.info(f"Collection has {count} documents")
                
                if count == 0:
                    logger.warning("No documents found in the collection. Please upload documents first.")
                    return {
                        "type": "error",
                        "message": "I am unable to answer your question as I do not have access to any documents. Please upload documents first."
                    }
                
                # Generate query embedding
                query_embedding = embeddings.embed_query(query)
                logger.info(f"Created query embedding with dimension {len(query_embedding)}")
                
                # Query the collection
                results = direct_collection.query(
                    query_embeddings=[query_embedding],
                    n_results=k,
                    include=["documents", "metadatas", "distances"]
                )
                
                logger.info(f"Query returned {len(results['documents'][0])} documents")
                
                # Convert to Document objects for consistency
                docs = []
                if len(results['documents'][0]) > 0:
                    for i in range(len(results['documents'][0])):
                        doc = Document(
                            page_content=results['documents'][0][i],
                            metadata=results['metadatas'][0][i]
                        )
                        docs.append(doc)
                    
                    # Log the sources of retrieved documents
                    sources = []
                    for doc in docs:
                        source = doc.metadata.get("source", "unknown")
                        sources.append(source)
                    logger.info(f"Retrieved documents from sources: {sources}")
                    
                    # Check if all documents are from tabular data
                    all_tabular = all('table_name' in doc.metadata for doc in docs)
                    if all_tabular and len(docs) > 0:
                        # Get unique table names
                        table_names = list(set(doc.metadata.get('table_name') for doc in docs if 'table_name' in doc.metadata))
                        logger.info(f"All documents are from tabular data in tables: {table_names}")
                        
                        # Add table info in metadata
                        for doc in docs:
                            if 'table_name' in doc.metadata:
                                doc.metadata['is_tabular'] = True
                    
                    return {
                        "type": "documents",
                        "data": docs
                    }
                else:
                    logger.warning("No relevant documents found for the query.")
                    return {
                        "type": "error",
                        "message": "I could not find relevant information in the uploaded documents. Try a different query or upload more documents."
                    }
                    
            except Exception as e:
                logger.error(f"Error during similarity search: {e}")
                import traceback
                logger.error(traceback.format_exc())
                return {
                    "type": "error",
                    "message": f"Error during similarity search: {str(e)}"
                }
    
    except Exception as e:
        logger.error(f"Retrieval error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            "type": "error",
            "message": f"Retrieval error: {str(e)}"
        } 