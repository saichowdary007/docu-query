from ..services.nlp_service import get_llm
from langchain_core.messages import HumanMessage

class ResponseGenerator:
    """
    Generates a natural language response based on a query and provided context
    using a large language model.
    """
    def __init__(self):
        """
        Initializes the ResponseGenerator with a language model.
        """
        self.llm = get_llm()

    async def generate(self, query: str, context: str) -> str:
        """
        Generates a response to a query given a context.

        Args:
            query: The user's query.
            context: The retrieved context relevant to the query.

        Returns:
            A string containing the generated response.
        """
        prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return response.content
