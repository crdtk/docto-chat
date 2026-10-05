"""Chat generation service: orchestrates model + streaming."""

from transformers import TextIteratorStreamer
from server.models import ModelManager
from server.prompt import PromptBuilder
import threading, json, logging
from typing import Generator, List, Dict, Any

logger = logging.getLogger(__name__)

class ChatService:
    """Orchestrates chat generation with model and streaming.

    Coordinates:
    - Prompt building from message history
    - Thread-safe model access via ModelManager
    - Token streaming with Server-Sent Events format
    - Error handling and completion markers

    Attributes:
        model_manager: ModelManager instance for model access
    """

    def __init__(self, model_manager: ModelManager) -> None:
        """Initialize with model manager (dependency injection).

        Args:
            model_manager: ModelManager instance (usually singleton)
        """
        self.model_manager = model_manager

    def generate(self, messages: List[Dict[str, str]], max_tokens: int) -> Generator[str, None, None]:
        """Generate chat response with streaming.

        Yields SSE (Server-Sent Events) formatted chunks:
        - Token deltas as JSON: {"choices": [{"delta": {"content": token}}]}
        - Completion marker: [DONE]
        - Errors as JSON: {"error": "message"}

        Args:
            messages: Conversation history
            max_tokens: Maximum tokens to generate

        Yields:
            SSE-formatted strings (data: <json>\n\n)
        """
        try:
            prompt = PromptBuilder.build(messages)

            with self.model_manager.lock:
                inputs = self.model_manager.tokenizer(prompt, return_tensors="pt")
                streamer = TextIteratorStreamer(
                    self.model_manager.tokenizer,
                    skip_prompt=True,
                    skip_special_tokens=True
                )
                thread = threading.Thread(
                    target=self.model_manager.model.generate,
                    kwargs={
                        **inputs,
                        "streamer": streamer,
                        "max_new_tokens": max_tokens,
                        "max_length": None
                    }
                )
                thread.start()

            token_count = 0
            for token in streamer:
                yield f"data: {json.dumps({'choices': [{'delta': {'content': token}}]})}\n\n"
                token_count += 1

            thread.join()
            yield f"data: [DONE]\n\n"
            logger.info(f"Chat completed: {token_count} tokens generated")

        except Exception as e:
            logger.error(f"Error during generation: {e}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
