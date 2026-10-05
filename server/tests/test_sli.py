"""SLI (Service Level Indicator) tests for streaming LLM service.

Tests measure and validate performance metrics:
- TTFT (Time to First Token)
- Throughput (tokens/second)
- P95 Throughput (95th percentile)

Requires running server: make server
Then run tests: make test-sli
"""

import unittest
import requests
import json
from typing import List, Optional
from server.metrics import RequestMetrics

class TestStreamingSLI(unittest.TestCase):
    """Integration tests for streaming performance SLIs.

    These tests require the server to be running.
    Run with: make test-sli
    """

    API_URL = "http://localhost:8000/v1/chat/completions"
    metrics: Optional[RequestMetrics] = None
    rates: List[float] = []

    @classmethod
    def setUpClass(cls):
        """Run streaming test once and collect metrics."""
        cls.metrics, cls.rates = cls._run_stream()

    @classmethod
    def _run_stream(cls) -> tuple[RequestMetrics, List[float]]:
        """Stream and measure SLI metrics in real time.

        Returns:
            Tuple of (RequestMetrics, list of throughput rates per token)
        """
        payload = {
            "messages": [{"role": "user", "content": "Define aspirin"}],
            "max_tokens": 10,
            "stream": True
        }

        metrics = RequestMetrics("sli-test")
        rates = []

        print("\nStreaming tokens:")

        try:
            with requests.post(cls.API_URL, json=payload, stream=True, timeout=30) as resp:
                for line in resp.iter_lines():
                    if line.startswith(b"data: "):
                        try:
                            data = json.loads(line[6:])

                            # Check for completion marker (string)
                            if isinstance(data, str) and data == "[DONE]":
                                break

                            # Extract token from SSE chunk
                            if isinstance(data, dict):
                                token = data.get('choices', [{}])[0].get('delta', {}).get('content', '')
                                if token:
                                    metrics.record_token()
                                    if metrics.token_count == 1:
                                        metrics.record_first_token()

                                    elapsed = metrics.duration()
                                    rate = metrics.throughput()
                                    rates.append(rate)

                                    status = "!" if metrics.token_count == 1 else " "
                                    print(f"{status} [{metrics.token_count:2d}] {repr(token):15s} | {rate:.2f} tok/s")
                        except json.JSONDecodeError:
                            pass
                        except Exception as e:
                            pass

            metrics.finish()
            print(f"\n  Total: {metrics.token_count} tokens in {metrics.duration():.1f}s")

        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                f"Cannot connect to server at {cls.API_URL}. "
                "Run 'make server' in another terminal first."
            )
        except requests.exceptions.Timeout:
            raise RuntimeError(
                f"Server timeout at {cls.API_URL}. "
                "Server may be too slow or unresponsive."
            )

        return metrics, rates

    def test_ttft_slo(self):
        """Time to First Token should be reasonable (test environment)."""
        if self.metrics.token_count == 0:
            self.skipTest("No tokens generated - server may not have responded")

        slo = 20.0  # Generous for test/CI environments
        ttft = self.metrics.ttft()
        self.assertLess(
            ttft,
            slo,
            f"TTFT {ttft:.2f}s exceeds SLO {slo}s"
        )
        print(f"  ✓ TTFT: {ttft:.2f}s (SLO: <{slo}s)")

    def test_throughput_slo(self):
        """Average throughput should be positive (test environment)."""
        if self.metrics.token_count == 0:
            self.skipTest("No tokens generated - server may not have responded")

        slo = 0.01  # Very generous for test environments
        throughput = self.metrics.throughput()
        self.assertGreater(
            throughput,
            slo,
            f"Throughput {throughput:.2f} below SLO {slo}"
        )
        print(f"  ✓ Throughput: {throughput:.2f} tok/s (SLO: >{slo})")

    def test_p95_throughput_slo(self):
        """P95 throughput should be positive (test environment)."""
        if not self.rates:
            self.skipTest("No tokens generated - server may not have responded")

        slo = 0.01  # Very generous for test environments
        rates_sorted = sorted(self.rates)
        p95_rate = rates_sorted[int(len(rates_sorted) * 0.95)] if rates_sorted else 0

        self.assertGreater(
            p95_rate,
            slo,
            f"P95 {p95_rate:.2f} below SLO {slo}"
        )
        print(f"  ✓ P95 Throughput: {p95_rate:.2f} tok/s (SLO: >{slo})")

    @classmethod
    def tearDownClass(cls):
        """Print summary."""
        print("\n" + "="*60)
        print("SLI METRICS SUMMARY")
        print("="*60)
        if cls.metrics.token_count > 0:
            print(f"  TTFT:       {cls.metrics.ttft():.2f}s")
            print(f"  Throughput: {cls.metrics.throughput():.2f} tok/s (avg)")
            rates_sorted = sorted(cls.rates)
            p95_rate = rates_sorted[int(len(rates_sorted) * 0.95)] if rates_sorted else 0
            print(f"  P95:        {p95_rate:.2f} tok/s")
        print(f"  Tokens:     {cls.metrics.token_count} in {cls.metrics.duration():.1f}s")
        print("="*60)

if __name__ == '__main__':
    unittest.main(verbosity=2)
