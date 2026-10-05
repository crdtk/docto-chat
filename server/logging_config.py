"""Structured JSON logging configuration."""

import logging
import json
from datetime import datetime, timezone
from typing import Any

class JSONFormatter(logging.Formatter):
    """Format logs as JSON for machine parsing."""

    def format(self, record: logging.LogRecord) -> str:
        """Convert log record to JSON.

        Args:
            record: LogRecord from logging module

        Returns:
            JSON string with timestamp, level, logger, message, and extras
        """
        log_obj = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add custom fields if present
        if hasattr(record, "request_id"):
            log_obj["request_id"] = record.request_id
        if hasattr(record, "status_code"):
            log_obj["status_code"] = record.status_code
        if hasattr(record, "duration_ms"):
            log_obj["duration_ms"] = record.duration_ms
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_obj)

def setup_logging(name: str, level: str = "INFO") -> logging.Logger:
    """Configure structured JSON logging.

    Args:
        name: Logger name
        level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level.upper())

    # Remove existing handlers
    logger.handlers.clear()

    # JSON handler (stdout)
    handler = logging.StreamHandler()
    formatter = JSONFormatter()
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
