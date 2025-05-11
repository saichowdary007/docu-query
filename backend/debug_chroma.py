import os
import chromadb
import logging
import traceback
from langchain_community.embeddings import FakeEmbeddings
from langchain_community.vectorstores import Chroma

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize embeddings
embeddings = FakeEmbeddings(size=768)

try:
    # Initialize Chroma client
    logger.info("Initializing Chroma client...")
    chroma_client = chromadb.PersistentClient(path="./chroma_db")
    collection_name = "docuquery"
    
    # List collections
    logger.info("Listing collections...")
    collections = chroma_client.list_collections()
    logger.info(f"Found {len(collections)} collections:")
    for coll in collections:
        logger.info(f"Collection: {coll.name}, count: {coll.count()}")
    
    # Try to get or create collection
    logger.info(f"Getting/creating collection: {collection_name}")
    try:
        collection = chroma_client.get_collection(name=collection_name)
        logger.info(f"Existing collection retrieved: {collection.name}, count: {collection.count()}")
    except Exception as e:
        logger.info(f"Collection not found, creating new: {str(e)}")
        collection = chroma_client.create_collection(name=collection_name)
        logger.info(f"New collection created: {collection.name}")
    
    # Try to create Langchain wrapper
    logger.info("Creating Langchain Chroma wrapper...")
    langchain_collection = Chroma(
        client=chroma_client,
        collection_name=collection_name,
        embedding_function=embeddings
    )
    logger.info("Langchain wrapper created successfully")
    
    # Try to query the collection
    logger.info("Trying a test query...")
    if collection.count() > 0:
        results = langchain_collection.similarity_search("test query", k=1)
        logger.info(f"Query successful, found {len(results)} results")
    else:
        logger.info("No documents in collection to query")
    
    # Try to add a simple document
    logger.info("Adding test document...")
    from langchain_core.documents import Document
    test_doc = Document(
        page_content="This is a test document",
        metadata={"source": "debug_test"}
    )
    try:
        langchain_collection.add_documents([test_doc])
        logger.info("Test document added successfully")
        count = collection.count()
        logger.info(f"Collection now has {count} documents")
    except Exception as e:
        logger.error(f"Error adding test document: {str(e)}")
        logger.error(traceback.format_exc())
    
except Exception as e:
    logger.error(f"Error in debug script: {str(e)}")
    logger.error(traceback.format_exc()) 