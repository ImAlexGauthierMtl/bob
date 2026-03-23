"""LLM Client — placeholder."""


class LLMClient:
    """Placeholder for LLM integration."""
    
    def chat(self, prompt: str, system_prompt: str = None, json_mode: bool = False, temperature: float = 0.0, max_tokens: int = 500) -> str:
        """Chat with LLM."""
        raise NotImplementedError()


llm_client = LLMClient()
