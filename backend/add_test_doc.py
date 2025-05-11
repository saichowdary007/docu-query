import chromadb
import os
from langchain_community.embeddings import FakeEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# Initialize embeddings
embeddings = FakeEmbeddings(size=768)

# Initialize Chroma client
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection_name = "docuquery"

# Get or create collection
try:
    chroma_client.get_collection(name=collection_name)
    print(f"Found existing collection: {collection_name}")
except:
    chroma_client.create_collection(name=collection_name)
    print(f"Created new collection: {collection_name}")

# Initialize Langchain Chroma wrapper
collection = Chroma(
    client=chroma_client,
    collection_name=collection_name,
    embedding_function=embeddings
)

# Create test document
test_doc = Document(
    page_content="John Smith is a software engineer with experience in Python and JavaScript.",
    metadata={
        "source": "test_resume.txt",
        "file_type": "text"
    }
)

# Add document to collection
print("Adding document to collection...")
collection.add_documents([test_doc])

# Verify document was added
print("Checking collection...")
results = collection.similarity_search("John Smith", k=1)
print(f"Found {len(results)} documents")
for doc in results:
    print(f"Document content: {doc.page_content}")
    print(f"Document metadata: {doc.metadata}") 