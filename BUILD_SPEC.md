# Streaming LLM Chat Server - Build Specification

Instructions for Claude or another AI to build this project from scratch.
Start with SLI metrics requirement and work down through architecture.

## SLI Metrics (Top-Level Requirement)

- Create `test_sli.py` that validates performance
- TTFT (Time to First Token): < 20s
- Throughput (average): > 0.01 tok/s
- P95 Throughput: > 0.01 tok/s
- Requires running server with model loaded
- Report metrics to stdout during test execution

## API Specification

- Endpoint: `POST /v1/chat/completions`
- Request body: `{messages: [...], max_tokens: int}`
- Response: Server-Sent Events stream
- Token chunk format: `{"choices": [{"delta": {"content": "token"}}]}`
- Final chunk: `[DONE]`
- GET /health: return `{status, model, device}`
- GET /metrics: return `{rate_limit_per_minute, active_ips}`

## Core Architecture Classes

**ModelManager**
- Load/warmup model on init
- Thread-safe access via threading.Lock
- Attributes: tokenizer, model, lock, model_name, device
- Methods: load(), warmup()

**PromptBuilder**
- Format messages as "Role: content\n"
- Build prompt with system instruction + last 5 messages
- Constants: SYSTEM_PROMPT, ASSISTANT_PREFIX, CONTEXT_WINDOW=5

**RequestValidator**
- Validate messages format, types, non-empty
- Sanitize: max 10,000 chars per message, max 20 messages
- Return (is_valid, error_response) tuple
- Error codes: VALIDATION_ERROR, MODEL_ERROR, INTERNAL_ERROR, RATE_LIMIT

**ChatService**
- Orchestrate model generation with streaming
- Accept messages, max_tokens
- Yield SSE-formatted tokens: `data: {...}\n\n`
- Send `[DONE]` marker at completion
- Handle errors gracefully

**RequestMetrics**
- Track TTFT, token count, duration, throughput
- Methods: record_token(), record_first_token(), ttft(), throughput(), duration(), summary()

**ChatServer** (main class)
- Encapsulate Flask app + all dependencies
- Methods: __init__, _register_routes(), _register_hooks(), _rate_limit_decorator(), run()
- Handle SIGTERM/SIGINT for graceful shutdown
- Return 503 if shutdown_requested during new requests

## Features to Implement

**Logging**
- Structured JSON logging via JSONFormatter class
- Format: `{"timestamp": "...", "level": "...", "logger": "...", "message": "..."}`
- Setup function: `setup_logging(name, level)`

**Request Handling**
- Correlation IDs: 8-char UUID per request
- Before request hook: initialize request context (ID, metrics)
- After request hook: add X-Request-ID header, log metrics
- Response header: `X-Request-ID: <correlation-id>`

**Rate Limiting**
- Per-IP decorator: track request timestamps
- Default: 60 requests per minute
- Configurable via RATE_LIMIT_PER_MINUTE env var
- Return 429 if exceeded

**Graceful Shutdown**
- Register signal handlers for SIGTERM, SIGINT
- Set shutdown_requested flag
- Check flag before accepting new requests
- Return 503 Service Unavailable if shutting down

**Error Handling**
- Structured error responses with machine-readable codes
- Format: `{"error": "message", "code": "ERROR_CODE"}`
- Error codes: VALIDATION_ERROR, MODEL_ERROR, INTERNAL_ERROR, RATE_LIMIT

**Health Checks**
- GET /health endpoint
- Return model name, device, status
- GET /metrics endpoint
- Return rate limit config and active IPs

## Configuration Management

**config.py**
- Load all config from environment variables
- Use python-dotenv for .env file support
- Variables: HOST, PORT, DEBUG, MODEL_NAME, DEVICE, LOG_LEVEL, RATE_LIMIT_PER_MINUTE, etc.
- Provide defaults for all variables

**.env.example**
- Template showing all configurable variables
- Document defaults
- Never commit .env (actual secrets)

## Testing Strategy

**Unit Tests** (no mocking, dependency injection)
- test_models.py: ModelManager lifecycle
- test_prompt.py: Message formatting, prompt construction
- test_validation.py: Input validation scenarios
- test_service.py: ChatService with FakeModelManager

**Integration Tests**
- test_integration.py: Flask endpoints, status codes, headers
- Use Flask test client
- Test validation errors, health endpoint, metrics

**SLI Tests** (performance validation)
- test_sli.py: TTFT, throughput, P95
- Requires running server (make server in another terminal)
- Measures real model performance

**Test Fixtures**
- conftest.py: FakeModelManager (mock without mocking libraries)
- FakeModelManager returns fixed-length token stream
- Allows testing without loading real model

**Coverage**
- Target: 90%+ overall
- Unit/integration tests only (no external API mocking)
- Exclude model loading, hard-to-trigger error paths

## Documentation

**README.md**
- Quick start guide
- Features list
- Architecture (UML diagrams)
- API specification with examples
- Performance metrics (CPU baseline: TTFT 3.75s, throughput 0.86 tok/s)
- Testing guide
- Model quantization documentation
- Limitations & disclaimers section
- 4-phase roadmap

**CLAUDE.md**
- Code style rules (SRP, absolute imports, type hints)
- Architecture overview
- Production features
- Code quality guidelines
- Workflow commands

**UML Diagrams** (Mermaid format)
- Class diagram: ChatServer, ModelManager, PromptBuilder, etc.
- Sequence diagram: request flow
- Component architecture: layers
- Module dependency graph
- Logging architecture

## Optional Enhancements

**Model Quantization**
- Add QUANTIZE env var (default: false)
- Use BitsAndBytesConfig for 8-bit quantization
- Graceful fallback if bitsandbytes unavailable
- 75% memory reduction (4.4GB → 1.1GB)
- Results: negligible throughput impact (-1%)

**Benchmarking**
- compare_quantization.py script
- Benchmark quantized vs non-quantized
- Measure load time, memory, throughput
- Generate comparison table

**Build System**
- Makefile targets: server, server-quantized, test, test-sli, clean
- Dependencies: uv sync, pyproject.toml
- Python 3.12+ requirement

## Key Constraints & Decisions

- **No mocking libraries**: Use dependency injection and test doubles (FakeModelManager)
- **No async/await**: Flask synchronous (model access already serialized)
- **Serialized model access**: Lock prevents true concurrency (acceptable for this constraint)
- **Generator context issue**: Capture metrics before yield (outside Flask context)
- **CPU baseline metrics**: GPU will be 3-5x faster
- **Honest positioning**: Learning/prototyping tool, not production service
- **No authentication**: Suitable for internal/trusted use only
- **Type hints everywhere**: Full type annotations on all functions

## Project Structure

```
.
├── README.md              # Complete documentation
├── CLAUDE.md              # Development guide
├── BUILD_SPEC.md          # This file
├── Makefile               # Build targets
├── pyproject.toml         # Dependencies
├── .env.example           # Configuration template
├── .gitignore             # Git settings
├── .coveragerc            # Coverage config
├── benchmarks/
│   └── compare_quantization.py
├── client/
│   └── index.html         # Frontend
└── server/
    ├── llm_server.py      # ChatServer (Flask app)
    ├── models.py          # ModelManager
    ├── service.py         # ChatService
    ├── prompt.py          # PromptBuilder
    ├── validation.py      # RequestValidator
    ├── metrics.py         # RequestMetrics
    ├── errors.py          # Error codes
    ├── config.py          # Configuration
    ├── logging_config.py  # JSONFormatter
    └── tests/
        ├── conftest.py
        ├── test_models.py
        ├── test_prompt.py
        ├── test_validation.py
        ├── test_service.py
        ├── test_integration.py
        └── test_sli.py
```

## Getting Started

1. Create Python 3.12+ environment
2. Install uv: `pip install uv`
3. Sync dependencies: `uv sync`
4. Run server: `make server`
5. Run tests: `make test`
6. Run SLI metrics: `make test-sli` (requires server running)
7. See README.md for complete guide

---

**Purpose**: These specs enable Claude or another AI to build a production-grade streaming LLM server with comprehensive testing, observability, and documentation from scratch.

**Key metric**: SLI test validates TTFT < 20s, throughput > 0.01 tok/s on CPU baseline.
