"""Flask app for chat completions API with request tracking and metrics."""

from flask import Flask, request, Response, send_from_directory, jsonify, g
from flask_cors import CORS
import os, uuid, signal, sys
from typing import Tuple, Dict, Any, Callable
from functools import wraps
from collections import defaultdict
import time

from server.models import ModelManager
from server.service import ChatService
from server.validation import RequestValidator
from server.metrics import RequestMetrics
from server.errors import ErrorCode, error_response
from server.logging_config import setup_logging
from server.config import HOST, PORT, DEBUG, LOG_LEVEL, RATE_LIMIT_PER_MINUTE

class ChatServer:
    """HTTP server for chat completions with streaming, metrics, and rate limiting."""

    def __init__(self,
                 model_name: str = None,
                 device: str = "cpu",
                 rate_limit_per_minute: int = 60,
                 log_level: str = "INFO"):
        """Initialize chat server.

        Args:
            model_name: HuggingFace model ID
            device: PyTorch device ("cpu", "cuda", etc.)
            rate_limit_per_minute: Max requests per IP per minute
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.logger = setup_logging("llm-server", log_level)
        self.model_manager = ModelManager(model_name, device)
        self.chat_service = ChatService(self.model_manager)
        self.rate_limit_per_minute = rate_limit_per_minute
        self.rate_limit_store: Dict[str, list] = defaultdict(list)
        self.shutdown_requested = False

        # Create Flask app
        self.app = Flask(__name__, static_folder="../client", static_url_path="")
        CORS(self.app)

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        # Register routes and hooks
        self._register_routes()
        self._register_hooks()

    def _handle_shutdown(self, signum: int, frame: Any) -> None:
        """Handle SIGTERM/SIGINT for graceful shutdown."""
        self.shutdown_requested = True
        sig_name = "SIGTERM" if signum == signal.SIGTERM else "SIGINT"
        self.logger.info(f"Received {sig_name}, gracefully shutting down...")

    def _rate_limit_decorator(self) -> Callable:
        """Rate limit decorator based on client IP.

        Returns:
            Decorator function
        """
        def decorator(f: Callable) -> Callable:
            @wraps(f)
            def wrapped(*args: Any, **kwargs: Any) -> Any:
                client_ip = request.remote_addr or "unknown"
                now = time.time()
                minute_ago = now - 60

                # Clean old requests
                self.rate_limit_store[client_ip] = [
                    t for t in self.rate_limit_store[client_ip] if t > minute_ago
                ]

                # Check limit
                if len(self.rate_limit_store[client_ip]) >= self.rate_limit_per_minute:
                    self.logger.warning(f"Rate limit exceeded for {client_ip}")
                    return jsonify(error_response(
                        "Rate limit exceeded",
                        ErrorCode.RATE_LIMIT
                    )), 429

                self.rate_limit_store[client_ip].append(now)
                return f(*args, **kwargs)
            return wrapped
        return decorator

    def _register_hooks(self) -> None:
        """Register Flask before/after request hooks."""
        @self.app.before_request
        def before_request() -> None:
            """Initialize request context."""
            g.request_id = str(uuid.uuid4())[:8]
            g.metrics = RequestMetrics(g.request_id)
            self.logger.info(f"Request: {request.method} {request.path}")

        @self.app.after_request
        def after_request(response: Response) -> Response:
            """Add request ID to response and log metrics."""
            response.headers["X-Request-ID"] = g.request_id
            if hasattr(g, 'metrics') and g.metrics.end_time:
                self.logger.info(f"Metrics: {g.metrics.summary()}")
            return response

    def _register_routes(self) -> None:
        """Register HTTP routes."""
        @self.app.route("/")
        def index() -> Response:
            """Serve index.html."""
            return send_from_directory(self.app.static_folder, "index.html")

        @self.app.route("/health", methods=["GET"])
        def health() -> Tuple[Dict[str, Any], int]:
            """Health check endpoint."""
            return jsonify({
                "status": "ok",
                "model": self.model_manager.model_name,
                "device": self.model_manager.device
            }), 200

        @self.app.route("/metrics", methods=["GET"])
        def metrics() -> Tuple[Dict[str, Any], int]:
            """Metrics endpoint."""
            return jsonify({
                "rate_limit_per_minute": self.rate_limit_per_minute,
                "active_ips": len(self.rate_limit_store)
            }), 200

        @self.app.route("/v1/chat/completions", methods=["POST"])
        @self._rate_limit_decorator()
        def chat() -> Tuple[Response | Dict[str, Any], int]:
            """Chat completion endpoint with streaming."""
            # Check if shutdown requested
            if self.shutdown_requested:
                return jsonify(error_response(
                    "Server is shutting down",
                    ErrorCode.INTERNAL_ERROR
                )), 503

            data = request.json
            valid, err_response = RequestValidator.validate(data)
            if not valid:
                self.logger.warning(f"Validation failed: {err_response['error']}")
                g.metrics.finish()
                return err_response, 400

            messages = data.get("messages", [])
            max_tokens = data.get("max_tokens", 50)
            self.logger.info(f"Chat: {len(messages)} messages, max_tokens={max_tokens}")

            # Capture metrics reference before generator (outside Flask context)
            metrics = g.metrics
            request_id = g.request_id

            def generate_with_metrics() -> Any:
                """Wrap generator to track metrics."""
                for chunk in self.chat_service.generate(messages, max_tokens):
                    if 'content' in chunk and 'delta' in chunk:
                        metrics.record_token()
                        if metrics.token_count == 1:
                            metrics.record_first_token()
                    yield chunk
                metrics.finish()
                self.logger.info(f"Chat complete: {metrics.summary()}")

            return Response(generate_with_metrics(), mimetype="text/event-stream"), 200

    def run(self, host: str = None, port: int = None, debug: bool = None) -> None:
        """Start the server.

        Args:
            host: Host to bind to (default from config)
            port: Port to bind to (default from config)
            debug: Enable Flask debug mode (default from config)
        """
        _host = host or HOST
        _port = port or PORT
        _debug = debug if debug is not None else DEBUG

        self.logger.info(f"Starting server on http://{_host}:{_port}")
        self.logger.info("Press Ctrl+C to shutdown gracefully")

        try:
            self.app.run(host=_host, port=_port, debug=_debug, use_reloader=False)
        except KeyboardInterrupt:
            self.logger.info("Shutdown complete")
            sys.exit(0)

def _create_server() -> ChatServer:
    """Create ChatServer with config from environment."""
    return ChatServer(
        log_level=LOG_LEVEL,
        rate_limit_per_minute=RATE_LIMIT_PER_MINUTE
    )

# Module-level app instance for WSGI compatibility
def create_app() -> Flask:
    """Factory function to create Flask app."""
    return _create_server().app

app = create_app()

if __name__ == "__main__":
    _create_server().run()
