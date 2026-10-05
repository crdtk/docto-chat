"""Integration tests for full request/response cycle."""

import unittest
import json
from server.llm_server import app
from server.tests.conftest import FakeModelManager
from server import llm_server

class TestChatEndpoint(unittest.TestCase):
    """Integration tests for /v1/chat/completions endpoint."""

    def setUp(self):
        """Set up Flask test client."""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_health_endpoint(self):
        """Test /health endpoint."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'ok')
        self.assertIn('model', data)
        self.assertIn('device', data)

    def test_metrics_endpoint(self):
        """Test /metrics endpoint."""
        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn('rate_limit_per_minute', data)

    def test_chat_request_validation_missing_messages(self):
        """Test validation: missing messages."""
        response = self.client.post(
            '/v1/chat/completions',
            json={},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['code'], 'VALIDATION_ERROR')

    def test_chat_request_validation_empty_messages(self):
        """Test validation: empty messages."""
        response = self.client.post(
            '/v1/chat/completions',
            json={"messages": []},
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertIn('error', data)

    def test_chat_request_validation_invalid_max_tokens(self):
        """Test validation: invalid max_tokens."""
        response = self.client.post(
            '/v1/chat/completions',
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": -1
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'VALIDATION_ERROR')

    def test_chat_request_validation_message_too_long(self):
        """Test validation: message content exceeds limit."""
        response = self.client.post(
            '/v1/chat/completions',
            json={
                "messages": [{"role": "user", "content": "x" * 20000}],
                "max_tokens": 50
            },
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data['code'], 'VALIDATION_ERROR')

    def test_chat_request_valid(self):
        """Test valid chat request."""
        response = self.client.post(
            '/v1/chat/completions',
            json={
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 50
            },
            content_type='application/json'
        )
        # Should return 200 with SSE stream
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/event-stream')

    def test_request_id_header(self):
        """Test X-Request-ID header in response."""
        response = self.client.get('/health')
        self.assertIn('X-Request-ID', response.headers)
        request_id = response.headers['X-Request-ID']
        self.assertTrue(len(request_id) > 0)

class TestRateLimit(unittest.TestCase):
    """Integration tests for rate limiting."""

    def setUp(self):
        """Set up Flask test client."""
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def test_rate_limit_not_exceeded(self):
        """Test that requests under limit succeed."""
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)

    def test_rate_limit_status_ok(self):
        """Test that rate limit endpoint returns info."""
        response = self.client.get('/metrics')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertGreater(data['rate_limit_per_minute'], 0)

if __name__ == '__main__':
    unittest.main()
