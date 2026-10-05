"""Tests for ChatService."""

import unittest
from unittest.mock import Mock
from server.service import ChatService
from server.tests.conftest import FakeModelManager

class TestChatService(unittest.TestCase):
    """Test chat service with injected fake dependencies."""

    def setUp(self):
        """Inject fake model manager instead of loading real model."""
        self.fake_model = FakeModelManager()
        self.service = ChatService(self.fake_model)

    def test_generate_returns_generator(self):
        messages = [{"role": "user", "content": "Hello"}]
        result = self.service.generate(messages, max_tokens=10)
        # Should be a generator
        self.assertTrue(hasattr(result, '__iter__'))

    def test_generate_yields_completion_marker(self):
        """Test that generation yields completion marker."""
        messages = [{"role": "user", "content": "Hello"}]
        gen = self.service.generate(messages, max_tokens=10)
        output = list(gen)

        # Should end with completion marker
        self.assertGreater(len(output), 0)
        self.assertIn("[DONE]", output[-1])

if __name__ == '__main__':
    unittest.main()
