# Streaming LLM Chat Server — Development Guide

Well-engineered streaming LLM chat interface for learning and prototyping. Real-time token streaming, performance metrics, structured logging, comprehensive testing. Not intended as drop-in production service.

## Code Style Constitutional Rules

### Architecture

1. **Package organization — absolute imports only**
   - Use absolute imports: `from server.models import ModelManager`
   - Never relative imports: `from .models import ...`
   - Run as module: `python -m server.llm_server`, not `cd server && python llm_server.py`
   - Allows package to be imported anywhere without directory changes

2. **Single Responsibility Principle — one class per file**
   - Each file contains one class with one responsibility
   - ModelManager handles model lifecycle
   - PromptBuilder constructs prompts
   - RequestValidator validates requests
   - ChatService orchestrates generation
   - llm_server.py provides HTTP interface
   - Easy to test, extend, and maintain independently

3. **Composition over monolithic classes**
   - ChatService uses ModelManager, not inheriting or duplicating
   - Flask app uses RequestValidator, not embedding logic
   - Each class does one thing; compose them for complex workflows

### Python

1. **Favor comprehensions and functional operations over imperative mutations**
   - Use generator expressions with `join()` for building strings
   - Use list comprehensions for transformations
   - Prefer immutable assignments over loop-based mutations
   - Example: `history = "".join(format_message(msg) for msg in messages)`
   - Not: `history = ""; for msg in messages: history += format_message(msg)`

2. **Extract complex expressions into named variables**
   - If a comprehension or f-string expression exceeds ~80 chars, extract to a variable
   - Named variables document intent better than inline expressions
   - Example: `history = "".join(...); prompt = f"...{history}..."`
   - Not: `prompt = f"...{''.join(...)}..."`

3. **Single assignment for multi-part string construction**
   - Combine system prompt, history, and assistant prefix in one assignment
   - Use f-strings with extracted variables for readability
   - Not: `prompt = "..."; prompt += history; prompt += "Assistant: "`

### Makefile

See `Makefile` for constitutional rules on build targets, dependencies, and sentinels.

## SLI Metrics

Test suite validates streaming performance under realistic CPU constraints:
- **TTFT (Time to First Token):** <12.0s
- **Throughput:** >0.06 tok/s average
- **P95 Throughput:** >0.05 tok/s

Run with `make test-sli`.

## Production Features

### Structured Error Responses

All errors return machine-readable codes for programmatic handling:
```json
{
    "error": "messages cannot be empty",
    "code": "VALIDATION_ERROR"
}
```

Error codes: `VALIDATION_ERROR`, `MODEL_ERROR`, `INTERNAL_ERROR`, `RATE_LIMIT`

### Request ID Tracking

Every request gets a unique ID for tracing:
- Response header: `X-Request-ID: a1b2c3d4`
- Logged with every message: `[a1b2c3d4] Chat: 1 messages, max_tokens=50`
- Helps debug multi-step flows

### Request Metrics

Per-request tracking of:
- **TTFT** (Time to First Token): latency until first token
- **Throughput**: tokens/second during generation
- **Duration**: total request time
- Logged at completion: `request_id=a1b2c3d4 ttft=2.34s tokens=42 duration=15.2s throughput=2.76 tok/s`

### Input Validation & Sanitization

Validation checks:
- Message content ≤ 10,000 characters
- ≤ 20 messages per request
- max_tokens is positive integer
- All message fields are strings

Prevents abuse and oversized requests.

### Rate Limiting

Per-IP rate limits (configurable):
- Default: 60 requests per minute
- Returns `429 Too Many Requests` with error code
- Resets per minute per IP
- Set via `RATE_LIMIT_PER_MINUTE` env var

### Model Warm-up

Model is pre-warmed on startup:
- Eliminates slow first request
- Pre-populates GPU/CPU caches
- Logged: `✓ Model warmed up`

### Model Quantization (Optional)

8-bit quantization reduces memory footprint by ~50% with minimal accuracy loss:
- Set `QUANTIZE=true` in `.env` to enable
- Requires `bitsandbytes` package: `pip install -e ".[quantization]"`
- Automatically falls back to full precision if bitsandbytes unavailable
- Improves inference speed on memory-constrained systems
- Logged: `✓ Model loaded with 8-bit quantization`

### Health & Metrics Endpoints

- `GET /health` → model status and device
- `GET /metrics` → system metrics and rate limit config
- Useful for monitoring and load balancers

## Code Quality

### Type Hints

All functions and methods include type annotations:
- Parameter types: `messages: List[Dict[str, str]]`
- Return types: `-> str`
- Optional types: `Optional[str]`
- Callable types: `-> Generator[str, None, None]`

Catches errors at dev time, improves IDE support.

### Docstrings

Comprehensive module and class documentation:
- Module docstring: brief description
- Class docstring: purpose, attributes, usage
- Method docstring: parameters, returns, raises

Example:
```python
def generate(self, messages: List[Dict[str, str]], max_tokens: int) -> Generator[str, None, None]:
    """Generate chat response with streaming.
    
    Args:
        messages: Conversation history
        max_tokens: Maximum tokens to generate
    
    Yields:
        SSE-formatted strings (data: <json>\n\n)
    """
```

### Health Check Endpoint

`GET /health` returns model status:
```json
{
    "status": "ok",
    "model": "prav-974/medical-qa-tinyllama",
    "device": "cpu"
}
```

Useful for monitoring and load balancers.

## Server Architecture

### File Structure

Independent, single-responsibility modules:

- **`models.py`** — `ModelManager` class
  - Loads tokenizer and model from HuggingFace
  - Manages lifecycle (initialization, device placement)
  - Provides thread-safe access via lock

- **`prompt.py`** — `PromptBuilder` class
  - Formats messages as "Role: content\n"
  - Constructs system prompt + conversation history
  - Constants: system prompt, context window (5 messages), assistant prefix

- **`validation.py`** — `RequestValidator` class
  - Validates message format and types
  - Checks messages non-empty, max_tokens positive
  - Returns (is_valid, error_message) tuple

- **`service.py`** — `ChatService` class
  - Orchestrates model generation with streaming
  - Uses ModelManager, PromptBuilder
  - Yields SSE-formatted tokens with error handling

- **`llm_server.py`** — Flask application
  - HTTP endpoints (GET /, POST /v1/chat/completions)
  - Uses RequestValidator, ChatService
  - Environment configuration (HOST, PORT, DEBUG)

- **`__init__.py`** — package exports
  - Exports public classes and app

### Improvements

✓ **Class-based design** — encapsulates model/tokenizer/lock, easier to test
✓ **Logging** — replaced print() with logging module (timestamps, log levels)
✓ **Request validation** — validates message format, types, non-empty payloads
✓ **Error handling** — try/except in generate(), returns error SSE chunks
✓ **Response markers** — sends `[DONE]` chunk when generation completes
✓ **Configuration** — MODEL_NAME, HOST, PORT, DEBUG from environment variables
✓ **Thread safety** — instance lock serializes model access across concurrent requests

### Request/Response Format

**Request** (JSON POST to `/v1/chat/completions`):
```json
{
  "messages": [
    {"role": "user", "content": "Define aspirin"},
    {"role": "assistant", "content": "Aspirin is..."}
  ],
  "max_tokens": 50
}
```

**Response** (Server-Sent Events):
```
data: {"choices": [{"delta": {"content": "Aspirin"}}]}

data: {"choices": [{"delta": {"content": " is"}}]}

data: [DONE]
```

## Testing

See **TESTING.md** for comprehensive testing guide.

### Test Coverage

```bash
make test            # Run all tests with coverage report (~3s)
make test-sli        # Run performance metrics (~20s, requires server)
```

Coverage targets:
- **prompt.py:** 95% (pure logic)
- **validation.py:** 95% (all paths tested)
- **models.py:** 90% (excludes external API)
- **service.py:** 85% (excludes hard-to-trigger errors)
- **errors.py:** 100% (simple utility)

HTML report: `make coverage` generates `htmlcov/index.html`

### Test Structure

Tests are co-located with code in `server/tests/`:

```
server/
  models.py
  prompt.py
  validation.py
  service.py
  metrics.py
  errors.py
  tests/
    __init__.py
    conftest.py          # Shared fixtures (FakeModelManager)
    test_models.py       # Tests for ModelManager
    test_prompt.py       # Tests for PromptBuilder
    test_validation.py   # Tests for RequestValidator
    test_service.py      # Tests for ChatService
    test_integration.py  # Full request/response cycle tests
    test_sli.py          # Service Level Indicator (performance) tests
```

### Test Types

1. **Unit tests** (`test_*.py`) — test individual classes with dependency injection
   - No mocking/patching
   - Fast (~1s total)
   - Run with: `make test`

2. **Integration tests** (`test_integration.py`) — test Flask endpoints
   - Uses Flask test client
   - Tests validation, headers, endpoints
   - Run with: `make test`

3. **SLI tests** (`test_sli.py`) — test performance metrics
   - Requires running server: `make server`
   - Measures TTFT, throughput, P95 latency
   - Uses `RequestMetrics` infrastructure
   - Run with: `make test-sli`

### Unit Tests with Dependency Injection

Tests use **dependency injection** instead of mocking/patching:

- **PromptBuilder tests** — no dependencies, test logic directly
- **RequestValidator tests** — no dependencies, test validation logic
- **ChatService tests** — inject `FakeModelManager` instead of loading real model
- **ModelManager tests** — structure validation (actual model loading not tested)

`conftest.py` provides shared fixtures: `FakeModelManager` with Mock tokenizer/model.

No `@patch` or `@mock` decorators. Real code path, fake dependencies.

```bash
make test            # Run unit tests (fast, ~1s)
make test-sli        # Run SLI metrics (slow, ~20s)
```

## Workflow

```bash
make server          # Run Flask app + streaming chat on http://localhost:8000
make test            # Run unit tests
make test-sli        # Validate SLI metrics (runs once, ~20s)
make clean           # Clean __pycache__ and venv
```

## Environment Configuration

Override defaults with environment variables:

```bash
MODEL_NAME=prav-974/medical-qa-tinyllama  # HuggingFace model ID
HOST=0.0.0.0                               # Bind address
PORT=8000                                  # Port
DEBUG=false                                # Flask debug mode
```
