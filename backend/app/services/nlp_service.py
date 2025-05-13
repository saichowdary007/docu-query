import requests
import json
import numpy as np
from typing import Dict, Any, List, Optional, Sequence
from langchain_google_vertexai import VertexAIEmbeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.embeddings import Embeddings
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_core.outputs import ChatGeneration
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from pydantic import Field, BaseModel
from app.core.config import settings

class ChatResult(BaseModel):
    generations: List[ChatGeneration]
    llm_output: Optional[Dict[str, Any]] = None

class SimpleEmbeddingsModel(Embeddings):
    """
    A simpler embeddings model that doesn't rely on Vertex AI auth
    Uses a simpler algorithm for development purposes
    """
    
    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed search documents."""
        # For simplicity, we'll implement a simple embedding function
        # This is not suitable for production, but will work for our demo
        print(f"Creating embeddings for {len(texts)} documents")
        embeddings = []
        for text in texts:
            # Create a simple embedding based on character frequencies
            # (for demo only, production should use a real embedding model)
            embedding = self._simple_embedding(text)
            embeddings.append(embedding)
        return embeddings
    
    def embed_query(self, text: str) -> List[float]:
        """Embed query text."""
        print(f"Creating embedding for query: {text[:50]}...")
        return self._simple_embedding(text)
    
    def _simple_embedding(self, text: str) -> List[float]:
        """
        Creates a simplified embedding vector based on character counts.
        This is NOT a substitute for proper embeddings, but works for demo purposes.
        """
        # Initialize a vector of 384 dimensions (common size)
        vec = [0.0] * 384
        
        # Fill the first 128 positions with ASCII character frequencies
        chars = {}
        for c in text.lower():
            chars[c] = chars.get(c, 0) + 1
        
        for c, count in chars.items():
            if ord(c) < 128:
                vec[ord(c)] = count / len(text)
        
        # Fill remaining positions with some derived values
        word_count = len(text.split())
        if word_count > 0:
            vec[128] = word_count / 100  # normalized word count
            
        # Average word length
        avg_word_len = sum(len(w) for w in text.split()) / max(1, word_count)
        vec[129] = avg_word_len / 10  # normalized average word length
        
        # Normalize the vector
        norm = np.sqrt(sum(x*x for x in vec))
        if norm > 0:
            vec = [x/norm for x in vec]
            
        return vec

class GeminiChatModel(BaseChatModel):
    api_key: str = Field(...)
    model_name: str = Field(default="gemini-2.0-flash")
    temperature: float = Field(default=0.1)
    max_tokens: int = Field(default=1024)
    base_url: str = Field(default="https://generativelanguage.googleapis.com/v1beta")
    
    @property
    def _llm_type(self) -> str:
        """Return the type of LLM."""
        return "gemini"
    
    class Config:
        arbitrary_types_allowed = True
    
    def _generate(self, 
                 messages: List[BaseMessage], 
                 stop: Optional[List[str]] = None,
                 run_manager: Optional[CallbackManagerForLLMRun] = None, 
                 **kwargs) -> ChatResult:
        response = self._call_api(messages)
        return self._create_chat_result(response)
    
    def _convert_messages_to_gemini_format(self, messages: List[BaseMessage]) -> List[Dict[str, Any]]:
        gemini_messages = []
        content = {"parts": []}
        
        for message in messages:
            if isinstance(message, SystemMessage):
                # Add system message as a user message with a special prefix
                content["role"] = "user"
                content["parts"].append({"text": f"SYSTEM: {message.content}"})
            elif isinstance(message, HumanMessage):
                content["role"] = "user"
                content["parts"].append({"text": message.content})
                gemini_messages.append(content)
                content = {"parts": []}
            elif isinstance(message, AIMessage):
                content["role"] = "model"
                content["parts"].append({"text": message.content})
                gemini_messages.append(content)
                content = {"parts": []}
        
        # If there's a pending content (e.g., only system message)
        if content["parts"]:
            gemini_messages.append(content)
        
        return gemini_messages
    
    def _call_api(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        url = f"{self.base_url}/models/{self.model_name}:generateContent?key={self.api_key}"
        
        gemini_messages = self._convert_messages_to_gemini_format(messages)
        
        payload = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens
            }
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            if hasattr(e, 'response'):
                print(f"Response content: {e.response.text}")
            raise
    
    def _create_chat_result(self, response: Dict[str, Any]) -> ChatResult:
        try:
            text = response["candidates"][0]["content"]["parts"][0]["text"]
            generation = ChatGeneration(message=AIMessage(content=text))
            return ChatResult(generations=[generation])
        except (KeyError, IndexError) as e:
            print(f"Failed to parse Gemini API response: {response}")
            raise ValueError(f"Failed to parse Gemini API response: {e}")
    
    async def _agenerate(self, 
                        messages: List[BaseMessage], 
                        stop: Optional[List[str]] = None,
                        run_manager: Optional[CallbackManagerForLLMRun] = None, 
                        **kwargs) -> ChatResult:
        # For simplicity, reuse the sync implementation
        # In a production environment, use an async HTTP client like aiohttp
        return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)

def get_embeddings_model():
    # Use our simple embeddings model instead of VertexAI
    return SimpleEmbeddingsModel()

def get_llm():
    return GeminiChatModel(
        api_key=settings.GOOGLE_API_KEY,
        model_name="gemini-2.0-flash",  # Using the model from your curl example
        temperature=0.1,
        max_tokens=1024
    )
