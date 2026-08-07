class Models:
    """Model capability lookup built from provider-owned metadata."""

    DEFAULT_CONTEXT_WINDOW = 32_000

    @classmethod
    def table(cls):
        from .backends import Anthropic, Gemini, Ollama, OllamaCloud, OpenAI

        result = {}
        for backend in (Anthropic, OpenAI, Gemini, Ollama, OllamaCloud):
            result.update(backend.MODELS)
        return result

    @classmethod
    def context_window(cls, model):
        info = cls.table().get(str(model))
        return info["context_window"] if info else cls.DEFAULT_CONTEXT_WINDOW
