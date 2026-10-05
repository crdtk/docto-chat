"""Error definitions with structured codes."""

from typing import Dict, Any

class ErrorCode:
    """Standard error codes for API responses."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    MODEL_ERROR = "MODEL_ERROR"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    RATE_LIMIT = "RATE_LIMIT"

def error_response(message: str, code: str) -> Dict[str, Any]:
    """Create structured error response.

    Args:
        message: Human-readable error message
        code: Machine-readable error code

    Returns:
        JSON-serializable error dict
    """
    return {"error": message, "code": code}
