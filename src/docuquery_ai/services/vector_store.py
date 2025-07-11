import os
from typing import List

from langchain_community.vectorstores import FAISS  # or Chroma
from langchain_core.documents import Document
from rank_bm25 import BM25Okapi
import pickle
from sentence_transformers import CrossEncoder

from docuquery_ai.core.config import settings
from docuquery_ai.services.nlp_service import get_embeddings_model

# Ensure vector_db_data directory exists
os.makedirs(settings.VECTOR_STORE_PATH, exist_ok=True)
FAISS_INDEX_PATH = os.path.join(settings.VECTOR_STORE_PATH, "faiss_index")
BM25_INDEX_PATH = os.path.join(settings.VECTOR_STORE_PATH, "bm25_index.pkl")




def initialize_vector_store(documents: List[Document] = None):
    embeddings = get_embeddings_model()
    vector_store = None
    bm25_retriever = None

    # Initialize/Load FAISS
    if os.path.exists(FAISS_INDEX_PATH) and os.listdir(FAISS_INDEX_PATH):
        print(f"Loading existing FAISS index from {FAISS_INDEX_PATH}")
        vector_store = FAISS.load_local(
            FAISS_INDEX_PATH, embeddings, allow_dangerous_deserialization=True
        )
    
    # Initialize/Load BM25
    if os.path.exists(BM25_INDEX_PATH):
        print(f"Loading existing BM25 index from {BM25_INDEX_PATH}")
        with open(BM25_INDEX_PATH, "rb") as f:
            bm25_retriever = pickle.load(f)

    if documents:
        if vector_store:
            print(f"Adding {len(documents)} new documents to existing FAISS index.")
            vector_store.add_documents(documents)
            vector_store.save_local(FAISS_INDEX_PATH)
        else:
            print(f"Creating new FAISS index with {len(documents)} documents.")
            vector_store = FAISS.from_documents(documents, embeddings)
            vector_store.save_local(FAISS_INDEX_PATH)

        # Update BM25 index
        corpus = [doc.page_content for doc in documents]
        if bm25_retriever:
            # For simplicity, re-indexing BM25 with new documents. 
            # For large datasets, consider incremental updates if BM25 library supports it.
            print(f"Re-creating BM25 index with {len(documents)} new documents.")
            bm25_retriever = BM25Okapi(corpus)
        else:
            print(f"Creating new BM25 index with {len(documents)} documents.")
            bm25_retriever = BM25Okapi(corpus)
        with open(BM25_INDEX_PATH, "wb") as f:
            pickle.dump(bm25_retriever, f)

    if not vector_store and not bm25_retriever:
        print(
            "Vector store not initialized as no documents were provided and no index exists."
        )
        return None, None
    
    return vector_store, bm25_retriever


def add_documents_to_store(vector_store, bm25_retriever, documents: List[Document]):
    if not vector_store:
        raise ValueError("Vector store not initialized.")
    vector_store.add_documents(documents)
    vector_store.save_local(FAISS_INDEX_PATH)
    print(f"Saved FAISS index to {FAISS_INDEX_PATH}")

    # Rebuild BM25 index with all documents from the updated FAISS store
    all_docs_content = [doc.page_content for doc in vector_store.docstore._dict.values()]
    bm25_retriever = BM25Okapi([doc.split(" ") for doc in all_docs_content]) # BM25 expects tokenized text
    with open(BM25_INDEX_PATH, "wb") as f:
        pickle.dump(bm25_retriever, f)
    print(f"Saved BM25 index to {BM25_INDEX_PATH}")
    return vector_store, bm25_retriever


def remove_documents_by_source(vector_store, bm25_retriever, source: str):
    """
    Removes all documents from the vector store that have the given source.

    Args:
        vector_store: The FAISS vector store instance.
        bm25_retriever: The BM25 retriever instance.
        source: The source identifier (usually the filename) to remove
    """
    # PROBLEM: FAISS does not natively support metadata-based deletion.
    # The current approach rebuilds the entire index, which is inefficient for large stores.
    # For more efficient deletion, consider vector databases that support metadata filtering
    # and targeted deletion (e.g., Chroma, Pinecone, Weaviate).
    if not vector_store:
        print(f"No vector store provided to remove documents from source: {source}")
        return None, None

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

            # Rebuild BM25 index from kept documents
            corpus = [doc.page_content for doc in kept_docs]
            new_bm25_retriever = BM25Okapi([doc.split(" ") for doc in corpus])
            with open(BM25_INDEX_PATH, "wb") as f:
                pickle.dump(new_bm25_retriever, f)
            print(f"Saved updated BM25 index to {BM25_INDEX_PATH}")

            return new_vector_store, new_bm25_retriever
        else:
            # If no documents left, remove the index
            print("No documents left in vector store after removal, cleaning up index")
            import shutil

            if os.path.exists(FAISS_INDEX_PATH):
                shutil.rmtree(FAISS_INDEX_PATH)
            if os.path.exists(BM25_INDEX_PATH):
                os.remove(BM25_INDEX_PATH)
            return None, None
    else:
        print("Vector store doesn't have the expected structure for document removal")
        return vector_store, bm25_retriever


def reciprocal_rank_fusion(ranked_lists: List[List[Document]], k=60) -> List[Document]:
    """
    Performs Reciprocal Rank Fusion (RRF) on a list of ranked document lists.
    """
    fused_scores = {}
    for ranked_list in ranked_lists:
        for rank, doc in enumerate(ranked_list):
            doc_id = doc.metadata.get("source", "") + "_" + str(doc.page_content.__hash__())
            if doc_id not in fused_scores:
                fused_scores[doc_id] = 0.0
            fused_scores[doc_id] += 1.0 / (k + rank)

    reranked_docs = sorted(
        fused_scores.items(), key=lambda item: item[1], reverse=True
    )

    # Reconstruct documents from the original lists based on fused scores
    final_documents = []
    unique_docs = set()
    for doc_id, _ in reranked_docs:
        for ranked_list in ranked_lists:
            for doc in ranked_list:
                current_doc_id = doc.metadata.get("source", "") + "_" + str(doc.page_content.__hash__())
                if current_doc_id == doc_id and current_doc_id not in unique_docs:
                    final_documents.append(doc)
                    unique_docs.add(current_doc_id)
                    break # Move to next doc_id once found
            if current_doc_id == doc_id and current_doc_id in unique_docs: # Break outer loop if doc found
                break

    return final_documents

def rerank_documents(query: str, documents: List[Document], top_n: int = 5) -> List[Document]:
    """
    Re-ranks documents using a Cross-Encoder model.
    """
    if not documents:
        return []

    cross_encoder_model = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
    pairs = [[query, doc.page_content] for doc in documents]
    scores = cross_encoder_model.predict(pairs)

    # Sort documents by score in descending order
    doc_scores = sorted(zip(documents, scores), key=lambda x: x[1], reverse=True)

    # Return top_n documents
    return [doc for doc, score in doc_scores[:top_n]]

def get_retriever(vector_store, bm25_retriever, llm, embeddings, knowledge_graph, k_results=5):
    if not vector_store or not bm25_retriever or not knowledge_graph:
        print(
            "Vector store, BM25 retriever, or knowledge graph not initialized. Upload files first."
        )
        return None  # Or raise an error

    class HybridRetriever:
        def __init__(self, vector_store, bm25_retriever, llm, embeddings, knowledge_graph, k_results):
            self.vector_store = vector_store
            self.bm25_retriever = bm25_retriever
            self.llm = llm
            self.embeddings = embeddings
            self.knowledge_graph = knowledge_graph
            self.k_results = k_results

        def get_relevant_documents(self, query: str) -> List[Document]:
            # HyDE: Generate a hypothetical answer
            hyde_prompt = f"Please write a concise, hypothetical answer to the question: {query}"
            hypothetical_answer = self.llm.invoke(hyde_prompt).content

            # Embed the hypothetical answer
            hypothetical_embedding = self.embeddings.embed_query(hypothetical_answer)

            # Semantic search using hypothetical embedding
            faiss_docs = self.vector_store.similarity_search_by_vector(hypothetical_embedding, k=self.k_results)

            # Keyword search
            tokenized_query = query.lower().split(" ")
            bm25_docs = self.bm25_retriever.retrieve(tokenized_query)

            # Graph-based search (simple for now)
            graph_docs = []
            found_nodes = self.knowledge_graph.search_nodes(query)
            for node in found_nodes:
                # Create a document from node properties
                doc_content = f"Node: {node['properties'].get('name')} (Type: {node['properties'].get('type')})"
                # Add connected nodes/edges as context if available
                connected_info = []
                for u, v, data in self.knowledge_graph.get_edges(node['id']):
                    target_node = self.knowledge_graph.get_node(v)
                    if target_node:
                        connected_info.append(f"{node['properties'].get('name')} -[{data.get('type')}]-> {target_node.get('name')}")
                if connected_info:
                    doc_content += "\nRelated: " + "; ".join(connected_info)
                graph_docs.append(Document(page_content=doc_content, metadata={"source": "knowledge_graph", "node_id": node['id']}))

            # Combine and re-rank using RRF
            combined_results = reciprocal_rank_fusion([faiss_docs, bm25_docs, graph_docs])
            
            # Re-rank combined results using Cross-Encoder
            reranked_results = rerank_documents(query, combined_results, top_n=self.k_results)

            return reranked_results

    return HybridRetriever(vector_store, bm25_retriever, llm, embeddings, knowledge_graph, k_results)


# Call initialize_vector_store() on app startup if index exists
# This can be done in web server initialization if using FastAPI
