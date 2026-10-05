"""Request metrics tracking."""

import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)

class RequestMetrics:
    """Track metrics for a single request.

    Attributes:
        request_id: Unique request identifier
        start_time: Request start timestamp
        first_token_time: Time of first token generated
        end_time: Request end timestamp
        token_count: Total tokens generated
    """

    def __init__(self, request_id: str) -> None:
        """Initialize metrics tracker.

        Args:
            request_id: Unique identifier for this request
        """
        self.request_id: str = request_id
        self.start_time: float = time.time()
        self.first_token_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.token_count: int = 0

    def record_first_token(self) -> None:
        """Record time of first token generation."""
        if self.first_token_time is None:
            self.first_token_time = time.time()

    def record_token(self) -> None:
        """Increment token count."""
        self.token_count += 1

    def finish(self) -> None:
        """Mark request as finished."""
        self.end_time = time.time()

    def ttft(self) -> float:
        """Time to first token in seconds."""
        if self.first_token_time is None:
            return 0
        return self.first_token_time - self.start_time

    def duration(self) -> float:
        """Total request duration in seconds."""
        end = self.end_time or time.time()
        return end - self.start_time

    def throughput(self) -> float:
        """Tokens per second."""
        duration = self.duration()
        if duration == 0:
            return 0
        return self.token_count / duration

    def summary(self) -> str:
        """Log-friendly summary of metrics."""
        return (
            f"request_id={self.request_id} "
            f"ttft={self.ttft():.2f}s "
            f"tokens={self.token_count} "
            f"duration={self.duration():.1f}s "
            f"throughput={self.throughput():.2f} tok/s"
        )
