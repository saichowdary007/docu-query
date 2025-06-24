import json
from typing import Any, Dict, List, Optional

import numpy as np
import requests
from langchain_core.callbacks.manager import CallbackManagerForLLMRun
from langchain_core.embeddings import Embeddings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration
from pydantic import BaseModel, Field

from docuquery_ai.core.config import settings


class ChatResult(BaseModel):
    generations: List[ChatGeneration]
    llm_output: Optional[Dict[str, Any]] = None


class GeminiChatModel(BaseChatModel):
    api_key: str = Field(...)
    model_name: str = Field(default="gemini-1.5-flash")
    temperature: float = Field(default=0.1)
    max_tokens: int = Field(default=1024)
    base_url: str = Field(default="https://generativelanguage.googleapis.com/v1beta")

    @property
    def _llm_type(self) -> str:
        """Return the type of LLM."""
        return "gemini"

    model_config = {"arbitrary_types_allowed": True}

    def _generate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs,
    ) -> ChatResult:
        response = self._call_api(messages)
        return self._create_chat_result(response)

    def _convert_messages_to_gemini_format(
        self, messages: List[BaseMessage]
    ) -> List[Dict[str, Any]]:
        # This implementation seems to have issues with system messages.
        # A simpler approach that follows Gemini's recommended format is better.
        # Gemini API prefers [user, model, user, model, ...] sequence.
        # A system message can be the first part of the first user message.

        gemini_messages = []
        current_parts: List[str] = []

        system_prompt = ""
        user_prompts = []

        for msg in messages:
            if isinstance(msg, SystemMessage):
                system_prompt += msg.content + "\n"
            elif isinstance(msg, HumanMessage):
                user_prompts.append(msg.content)
            elif isinstance(msg, AIMessage):
                # If we have user prompts, we should create a user message first
                if user_prompts:
                    full_user_prompt = system_prompt + "\n".join(user_prompts)
                    gemini_messages.append(
                        {"role": "user", "parts": [{"text": full_user_prompt}]}
                    )
                    system_prompt = ""  # System prompt is only used once
                    user_prompts = []

                # Add the model's response
                gemini_messages.append(
                    {"role": "model", "parts": [{"text": msg.content}]}
                )

        # Add any remaining user prompts at the end
        if user_prompts:
            full_user_prompt = system_prompt + "\n".join(user_prompts)
            gemini_messages.append(
                {"role": "user", "parts": [{"text": full_user_prompt}]}
            )

        return gemini_messages

    def _call_api(self, messages: List[BaseMessage]) -> Dict[str, Any]:
        url = f"{self.base_url}/models/{self.model_name}:generateContent?key={self.api_key}"

        gemini_messages = self._convert_messages_to_gemini_format(messages)

        payload = {
            "contents": gemini_messages,
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_tokens,
            },
        }

        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"API request error: {e}")
            if hasattr(e, "response") and e.response is not None:
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

    async def _agenerate(
        self,
        messages: List[BaseMessage],
        stop: Optional[List[str]] = None,
        run_manager: Optional[CallbackManagerForLLMRun] = None,
        **kwargs,
    ) -> ChatResult:
        # For simplicity, reuse the sync implementation
        # In a production environment, use an async HTTP client like aiohttp
        return self._generate(messages, stop=stop, run_manager=run_manager, **kwargs)


class MockEmbeddings(Embeddings):
    """Mock embeddings model for testing when Google credentials are not available."""

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generate mock embeddings for documents."""
        # Generate consistent but meaningless embeddings for testing
        embeddings = []
        for i, text in enumerate(texts):
            # Create a simple hash-based embedding
            embedding = (
                np.random.RandomState(hash(text) % 2**32).normal(0, 1, 768).tolist()
            )
            embeddings.append(embedding)
        return embeddings

    def embed_query(self, text: str) -> List[float]:
        """Generate mock embedding for a query."""
        return np.random.RandomState(hash(text) % 2**32).normal(0, 1, 768).tolist()


def get_embeddings_model() -> Embeddings:
    """Returns the configured embeddings model for the application."""
    # Check if we're using test credentials
    if (
        settings.GOOGLE_API_KEY == "test-api-key"
        or settings.GOOGLE_PROJECT_ID == "test-project-id"
    ):
        print(
            "⚠️  Using mock embeddings model for testing. Set real Google credentials for production."
        )
        return MockEmbeddings()

    try:
        # Use lazy import to avoid TypeAlias issues during model initialization
        from langchain_google_vertexai import VertexAIEmbeddings

        # This uses the official Google Vertex AI embeddings, which requires
        # GOOGLE_APPLICATION_CREDENTIALS or gcloud auth to be configured.
        # The project_id is automatically picked up from the environment.
        return VertexAIEmbeddings(model_name="textembedding-gecko@latest")
    except Exception as e:
        print(f"⚠️  Failed to initialize Vertex AI embeddings: {e}")
        print("⚠️  Falling back to mock embeddings model.")
        return MockEmbeddings()


def get_llm() -> BaseChatModel:
    """Returns the configured large language model for the application."""
    return GeminiChatModel(
        api_key=settings.GOOGLE_API_KEY,
        model_name="gemini-1.5-flash",
        temperature=0.1,
        max_tokens=2048,  # Increased for better summary capabilities
    )
