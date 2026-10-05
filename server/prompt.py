"""Prompt construction from message history."""

from typing import List, Dict

class PromptBuilder:
    """Constructs LLM prompts from message history.

    Formats message history into a prompt that includes:
    - System instruction (answer concisely in 2-3 sentences)
    - Recent conversation history (last 5 messages)
    - Assistant prefix (ready for model completion)

    Constants:
        SYSTEM_PROMPT: System instruction for the model
        ASSISTANT_PREFIX: Prefix marking assistant's turn
        CONTEXT_WINDOW: Number of recent messages to include
    """

    SYSTEM_PROMPT: str = "System: Provide clear, concise responses.\n\n"
    ASSISTANT_PREFIX: str = "Assistant: "
    CONTEXT_WINDOW: int = 5

    @staticmethod
    def format_message(msg: Dict[str, str]) -> str:
        """Format a single message for the prompt.

        Args:
            msg: Message dict with "role" and "content" keys

        Returns:
            Formatted message string: "Role: content\n"
        """
        role = "User" if msg["role"] == "user" else "Assistant"
        return f"{role}: {msg['content']}\n"

    @classmethod
    def build(cls, messages: List[Dict[str, str]]) -> str:
        """Build complete prompt from message history.

        Args:
            messages: List of message dicts with "role" and "content"

        Returns:
            Complete prompt ready for model generation
        """
        history = "".join(cls.format_message(msg) for msg in messages[-cls.CONTEXT_WINDOW:])
        return cls.SYSTEM_PROMPT + history + cls.ASSISTANT_PREFIX
