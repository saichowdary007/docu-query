import os
from typing import List

from langchain_community.vectorstores import FAISS  # or Chroma
from langchain_core.documents import Document

from docuquery_ai.core.config import settings
from docuquery_ai.services.nlp_service import get_embeddings_model

# Ensure vector_db_data directory exists
os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)
FAISS_INDEX_PATH = os.path.join(settings.VECTOR_STORE_PATH, "faiss_index")

# Global variable for simplicity, consider a class-based manager for more complex state
vector_store = None


def initialize_vector_store(documents: List[Document] = None):
    global vector_store
    embeddings = get_embeddings_model()
    if os.path.exists(FAISS_INDEX_PATH) and os.listdir(
        FAISS_INDEX_PATH
    ):  # Check if directory is not empty
        print(f"Loading existing FAISS index from {FAISS_INDEX_PATH}")
        vector_store = FAISS.load_local(
            FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True
        )
        if documents:  # If new documents are provided, add them
            print(f"Adding {len(documents)} new documents to existing index.")
            vector_store.add_documents(documents)
            vector_store.save_local(FAISS_INDEX_PATH)
    elif documents:
        print(f"Creating new FAISS index with {len(documents)} documents.")
        vector_store = FAISS.from_documents(documents, embeddings)
        vector_store.save_local(FAISS_INDEX_PATH)
    else:
        # Create an empty store if no documents and no existing store
        # This might happen on first run before any uploads
        print(
            "No documents provided and no existing index. Initializing empty FAISS store."
        )
        # FAISS needs at least one document to initialize, so this path needs careful handling.
        # Or, ensure initialize_vector_store is only called with documents.
        # For now, we'll assume it's called after first upload.
        # A placeholder document could be used:
        # placeholder_doc = [Document(page_content="init")]
        # vector_store = FAISS.from_documents(placeholder_doc, embeddings)
        # vector_store.save_local(FAISS_INDEX_PATH)
        # Better: Only initialize when there are documents.
        print(
            "Vector store not initialized as no documents were provided and no index exists."
        )
        return


def add_documents_to_store(documents: List[Document]):
    global vector_store  # noqa: F824
    if not vector_store:
        initialize_vector_store(documents)  # This will create and save
        # Note: initialize_vector_store modifies the global vector_store
    else:
        vector_store.add_documents(documents)
        vector_store.save_local(FAISS_INDEX_PATH)
    print(f"Saved FAISS index to {FAISS_INDEX_PATH}")


def remove_documents_by_source(source: str):
    """
    Removes all documents from the vector store that have the given source.

    Args:
        source: The source identifier (usually the filename) to remove
    """
    global vector_store
    if not vector_store:
        # Try to load the vector store if it exists
        if os.path.exists(FAISS_INDEX_PATH) and os.listdir(FAISS_INDEX_PATH):
            embeddings = get_embeddings_model()
            vector_store = FAISS.load_local(
                FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True
            )
            print(f"Loaded vector store to remove documents from source: {source}")
        else:
            print(f"No vector store found to remove documents from source: {source}")
            return

    # FAISS doesn't have direct metadata filtering for deletion, so we need to:
    # 1. Get all documents
    # 2. Filter out the ones with the matching source
    # 3. Create a new index with the remaining documents
    if hasattr(vector_store, "docstore") and hasattr(vector_store.docstore, "_dict"):
        # Get all documents currently in the store
        all_docs = []
        kept_docs = []

        # Collect documents that don't match the source to keep
        for doc_id, doc in vector_store.docstore._dict.items():
            all_docs.append(doc)
            if not hasattr(doc, "metadata") or doc.metadata.get("source") != source:
                kept_docs.append(doc)

        removed_count = len(all_docs) - len(kept_docs)
        print(f"Removing {removed_count} documents with source '{source}'")

        if kept_docs:
            # If we have documents to keep, create a new vector store
            embeddings = get_embeddings_model()
            new_vector_store = FAISS.from_documents(kept_docs, embeddings)
            new_vector_store.save_local(FAISS_INDEX_PATH)
            vector_store = new_vector_store
            print(f"Saved updated vector store with {len(kept_docs)} documents")
        else:
            # If no documents left, remove the index
            print("No documents left in vector store after removal, cleaning up index")
            import shutil

            if os.path.exists(FAISS_INDEX_PATH):
                shutil.rmtree(FAISS_INDEX_PATH)
            vector_store = None
    else:
        print("Vector store doesn't have the expected structure for document removal")


def get_retriever(k_results=5):
    global vector_store
    if not vector_store:
        # Attempt to load if not initialized (e.g. server restart)
        if os.path.exists(FAISS_INDEX_PATH) and os.listdir(FAISS_INDEX_PATH):
            embeddings = get_embeddings_model()
            vector_store = FAISS.load_local(
                FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True
            )
            print("Successfully loaded vector store on demand.")
        else:
            print(
                "Vector store not initialized and no index found. Upload files first."
            )
            return None  # Or raise an error
    return vector_store.as_retriever(search_kwargs={"k": k_results})


# Call initialize_vector_store() on app startup if index exists
# This can be done in web server initialization if using FastAPI
