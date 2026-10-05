"""Tests for RequestValidator."""

import unittest
from server.validation import RequestValidator

class TestRequestValidator(unittest.TestCase):
    """Test request validation — no dependencies."""

    def test_validate_empty_data(self):
        valid, error = RequestValidator.validate(None)
        self.assertFalse(valid)
        self.assertIn("empty", error)

    def test_validate_missing_messages(self):
        valid, error = RequestValidator.validate({})
        self.assertFalse(valid)
        self.assertIn("messages", error)

    def test_validate_messages_not_list(self):
        valid, error = RequestValidator.validate({"messages": "not a list"})
        self.assertFalse(valid)
        self.assertIn("list", error)

    def test_validate_empty_messages(self):
        valid, error = RequestValidator.validate({"messages": []})
        self.assertFalse(valid)
        self.assertIn("empty", error)

    def test_validate_message_missing_role(self):
        valid, error = RequestValidator.validate({
            "messages": [{"content": "test"}]
        })
        self.assertFalse(valid)
        self.assertIn("role", error)

    def test_validate_invalid_max_tokens(self):
        valid, error = RequestValidator.validate({
            "messages": [{"role": "user", "content": "test"}],
            "max_tokens": -1
        })
        self.assertFalse(valid)
        self.assertIn("positive", error)

    def test_validate_success(self):
        valid, error = RequestValidator.validate({
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 50
        })
        self.assertTrue(valid)
        self.assertIsNone(error)

if __name__ == '__main__':
    unittest.main()
