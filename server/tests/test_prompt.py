"""Tests for PromptBuilder."""

import unittest
from server.prompt import PromptBuilder

class TestPromptBuilder(unittest.TestCase):
    """Test prompt construction — no dependencies."""

    def test_format_message_user(self):
        msg = {"role": "user", "content": "Define aspirin"}
        result = PromptBuilder.format_message(msg)
        self.assertEqual(result, "User: Define aspirin\n")

    def test_format_message_assistant(self):
        msg = {"role": "assistant", "content": "Aspirin is a painkiller"}
        result = PromptBuilder.format_message(msg)
        self.assertEqual(result, "Assistant: Aspirin is a painkiller\n")

    def test_build_prompt_single_message(self):
        messages = [{"role": "user", "content": "Hello"}]
        prompt = PromptBuilder.build(messages)
        self.assertIn("System: Answer concisely", prompt)
        self.assertIn("User: Hello", prompt)
        self.assertIn("Assistant: ", prompt)

    def test_build_prompt_truncates_to_context_window(self):
        messages = [
            {"role": "user", "content": f"Message {i}"}
            for i in range(10)
        ]
        prompt = PromptBuilder.build(messages)
        # Only last 5 should be in history
        self.assertIn("Message 9", prompt)
        self.assertNotIn("Message 0", prompt)

if __name__ == '__main__':
    unittest.main()
