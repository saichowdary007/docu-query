class ResponseGenerator:
    """
    Generates a natural language response based on a query and provided context
    using a large language model.
    """

    def __init__(self):
        """Attempt to initialise a language model for response generation.

        The heavy language model stack is optional during testing; if it isn't
        available we simply skip initialisation and return empty responses.
        """
        try:  # pragma: no cover - optional dependency
            from ..services.nlp_service import get_llm

            self.llm = get_llm()
        except Exception:
            self.llm = None

    async def generate(self, query: str, context: str) -> str:
        """
        Generates a response to a query given a context.

        Args:
            query: The user's query.
            context: The retrieved context relevant to the query.

        Returns:
            A string containing the generated response.
        """
        if self.llm is None:
            return ""

        from langchain_core.messages import HumanMessage

        prompt = f"Context:\n{context}\n\nQuestion: {query}\n\nAnswer:"
        response = await self.llm.ainvoke([HumanMessage(content=prompt)])
        return response.content
