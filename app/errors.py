"""Application-specific errors."""


class TranslationError(RuntimeError):
    """Raised when translation fails validation or Ollama is unavailable."""


class ProcessingCancelled(RuntimeError):
    """Raised when shutdown requests cancellation of active processing."""
