import chromadb
import os

# Initialize Chroma client
chroma_client = chromadb.PersistentClient(path="./chroma_db")

# List collections
print(f"Collections: {chroma_client.list_collections()}")

# Check each collection
for coll in chroma_client.list_collections():
    print(f"Collection {coll.name} has {coll.count()} documents")
    
    # If there are documents, get some samples
    if coll.count() > 0:
        results = coll.get(limit=2)
        print(f"Sample documents: {results}") 