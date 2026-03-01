"""LLM handler - unified interface for language model providers."""

from src import config
from .client import chat_completion, check_llm


class LLMHandler:
    """Handler for interacting with LLM using direct HTTP requests."""

    def __init__(self):
        """ Initialize LLM handler. """

        # Ollama doesn't require API key
        if not config.LLM_API_KEY and config.LLM_PROVIDER.lower() != "ollama":
            raise ValueError("LLM_API_KEY must be set in .env")

    @staticmethod
    async def check() -> bool:
        """Check if LLM service is configured and reachable.

        Returns:
            True if LLM is available, False otherwise
        """
        return await check_llm()

    def generate_response_sync(
        self,
        conversation_history: list[dict],
        user_message: str
    ) -> str:
        """Generate AI response (sync).

        Args:
            conversation_history: Previous messages as list of {"role": str, "content": str}
                                 where role is "human" or "ai"
            user_message: New user input message

        Returns:
            AI response text
        """
        # Build messages list including history and new message
        messages = list(conversation_history) + [{"role": "user", "content": user_message}]

        return chat_completion(
            messages=messages,
            system_prompt=config.SYSTEM_PROMPT,
            model=config.LLM_MODEL,
            provider=config.LLM_PROVIDER,
            api_key=config.LLM_API_KEY,
            api_base_url=config.LLM_API_BASE_URL,
        )

    async def generate_response(
        self,
        conversation_history: list[dict],
        user_message: str
    ) -> str:
        """Async wrapper for generate_response_sync.

        Args:
            conversation_history: Previous messages as list of {"role": str, "content": str}
            user_message: New user input message

        Returns:
            AI response text
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.generate_response_sync,
            conversation_history,
            user_message
        )
