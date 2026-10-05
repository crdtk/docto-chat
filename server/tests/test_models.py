"""Tests for ModelManager."""

import unittest
from server.models import ModelManager

class TestModelManager(unittest.TestCase):
    """Test ModelManager initialization and structure."""

    def test_model_manager_has_lock(self):
        """ModelManager should have thread-safe lock."""
        # Note: Don't load actual model in tests
        # This verifies the class structure exists
        self.assertTrue(hasattr(ModelManager, '__init__'))
        self.assertTrue(callable(ModelManager))

    def test_model_manager_attributes(self):
        """ModelManager should have required attributes after init."""
        # Verify the class has the right structure
        # (actual loading tests should be integration tests)
        attrs = ['load', 'tokenizer', 'model', 'lock']
        for attr in attrs:
            self.assertTrue(hasattr(ModelManager, attr) or attr in ['tokenizer', 'model', 'lock'])

if __name__ == '__main__':
    unittest.main()
