# Development Guide

## Prerequisites

- Python 3.14+
- [uv](https://github.com/astral-sh/uv) package manager
- [gitleaks](https://github.com/gitleaks/gitleaks) for secret detection (`brew install gitleaks`)

## Setup

```bash
git clone https://github.com/dnvriend/gemini-ocr-tool.git
cd gemini-ocr-tool
make install
```

## Make Commands

```bash
make install              # Install dependencies
make format               # Format code with ruff
make lint                 # Run linting
make typecheck            # Type check with mypy
make test                 # Run tests
make security-bandit      # Python security linter
make security-pip-audit   # Dependency CVE scanner
make security-gitleaks    # Secret detection
make security             # All security checks
make check                # Full check (lint, typecheck, test, security)
make pipeline             # Full CI pipeline
make build                # Build package
make run ARGS="..."       # Run locally
make clean                # Remove build artifacts
```

## Project Structure

```
gemini-ocr-tool/
├── gemini_ocr_tool/
│   ├── __init__.py
│   ├── cli.py              # CLI entry point
│   ├── client.py           # Gemini client management
│   ├── file_handler.py     # File discovery and sorting
│   ├── ocr_processor.py    # OCR extraction logic
│   ├── logging_config.py   # Logging configuration
│   └── completion.py       # Shell completion
├── tests/
├── pyproject.toml
├── Makefile
└── LICENSE
```

## Testing

```bash
make test                              # Run all tests
uv run pytest tests/ -v                # Verbose output
uv run pytest tests/ --cov=gemini_ocr_tool  # With coverage
```

## Security Tools

| Tool | Purpose | Speed |
|------|---------|-------|
| bandit | Python security linting | ~2-3s |
| pip-audit | Dependency CVE scanning | ~2-3s |
| gitleaks | Secret detection | ~1s |

## Multi-Level Verbosity

| Flag | Level | Output |
|------|-------|--------|
| (none) | WARNING | Errors only |
| `-v` | INFO | Operations |
| `-vv` | DEBUG | Detailed info |
| `-vvv` | TRACE | Library internals |

## Troubleshooting

| Error | Solution |
|-------|----------|
| `No files match pattern` | Check glob pattern |
| `API key is required` | Set `GEMINI_API_KEY` env var |
| `OCR extraction failed` | Check API quota at [AI Studio](https://aistudio.google.com/app/apikey) |
| `GOOGLE_CLOUD_PROJECT required` | Set project via env or `--project` |
