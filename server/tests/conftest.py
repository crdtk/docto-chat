"""Shared test fixtures and mocks."""

from unittest.mock import Mock
import threading

class FakeModelManager:
    """Fake ModelManager for testing without loading actual model."""

    def __init__(self):
        self.lock = threading.Lock()
        self.tokenizer = Mock()
        self.model = Mock()
        self.tokenizer.return_value = {"input_ids": [1, 2, 3]}
        self.model.generate = Mock(return_value="generated")
