from pydantic import BaseModel, Field
from typing import List, Dict, Any

class Document(BaseModel):
    id: str
    title: str
    content: str
    metadata: Dict[str, Any]
    embeddings: List[float]
    entities: List[Any]  # Replace with specific Entity model later
    relationships: List[Any]  # Replace with specific Relationship model later
    knowledge_triples: List[Any]  # Replace with specific Triple model later

class HybridQuery(BaseModel):
    text: str
    vector_weight: float = 0.7
    keyword_weight: float = 0.3
    filters: Dict[str, Any] = Field(default_factory=dict)
    databases: List[str] = Field(default_factory=list)
