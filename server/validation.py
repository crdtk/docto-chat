"""Request validation for chat completion endpoints."""

from typing import Tuple, Optional, Dict, Any
from server.errors import ErrorCode, error_response

class RequestValidator:
    """Validates chat completion requests.

    Checks:
    - Request body is not empty
    - messages is a list
    - messages is not empty
    - Each message has "role" and "content"
    - Message content length within limits
    - max_tokens is a positive integer
    """

    MAX_CONTENT_LENGTH = 10000  # characters
    MAX_MESSAGES = 20

    @staticmethod
    def validate(data: Optional[Dict[str, Any]]) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """Validate request data.

        Args:
            data: Request JSON data

        Returns:
            Tuple of (is_valid: bool, response: Optional[Dict])
            If valid, returns (True, None)
            If invalid, returns (False, error_response_dict)
        """
        if not data:
            return False, error_response("Request body is empty", ErrorCode.VALIDATION_ERROR)

        messages = data.get("messages")
        if not isinstance(messages, list):
            return False, error_response("messages must be a list", ErrorCode.VALIDATION_ERROR)

        if not messages:
            return False, error_response("messages cannot be empty", ErrorCode.VALIDATION_ERROR)

        if len(messages) > RequestValidator.MAX_MESSAGES:
            return False, error_response(
                f"messages exceeds limit of {RequestValidator.MAX_MESSAGES}",
                ErrorCode.VALIDATION_ERROR
            )

        for i, msg in enumerate(messages):
            if not isinstance(msg, dict) or "role" not in msg or "content" not in msg:
                return False, error_response(
                    f"message {i}: must have role and content",
                    ErrorCode.VALIDATION_ERROR
                )

            content = msg.get("content", "")
            if not isinstance(content, str):
                return False, error_response(
                    f"message {i}: content must be string",
                    ErrorCode.VALIDATION_ERROR
                )

            if len(content) > RequestValidator.MAX_CONTENT_LENGTH:
                return False, error_response(
                    f"message {i}: content exceeds {RequestValidator.MAX_CONTENT_LENGTH} chars",
                    ErrorCode.VALIDATION_ERROR
                )

        max_tokens = data.get("max_tokens", 50)
        if not isinstance(max_tokens, int) or max_tokens <= 0:
            return False, error_response(
                "max_tokens must be a positive integer",
                ErrorCode.VALIDATION_ERROR
            )

        return True, None
