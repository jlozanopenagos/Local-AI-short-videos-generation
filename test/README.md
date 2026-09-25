# Test Layer: Senior QA Testing Suite

An isolated, enterprise-grade automated testing layer for the `shorts_automation` pipeline.

---

## Directory Architecture

```
test/
├── README.md               # Test documentation & execution manual
├── run_tests.py            # Standalone test runner (zero external dependencies needed)
├── pytest.ini              # Pytest configuration & markers (contained inside test directory)
├── requirements-test.txt   # Optional test tooling (pytest, pytest-mock)
├── conftest.py             # Shared fixtures and mock helpers
│
├── unit/                   # Layer 1: Fast deterministic unit tests (0 network/GPU calls)
│                           # Audio processor, chalkboard, ID generator, JSON parser, metadata,
│                           # music jam matcher, prompt rules, roleplay lens, subtitles, watchdog, thumbnail builder
│
├── integration/            # Layer 2: Component interaction, schemas & security tests
│                           # Database gates, health checks, pipeline status tracker, verbatim ingestion,
│                           # CSV/JSON schema contracts, system prompt editor, privacy & secret leak prevention
│
└── connectivity/           # Layer 3: Google Sheets integration & data contract tests
                            # Sheets fetcher, corrections extractor, reconciliation, poster, ready scripts scanner
```

---

## Quick Start & Execution

### 1. Run All Tests (Native Python Runner - Recommended)
Executes all **192 automated tests** across all QA layers with zero external dependencies in ~1.5 seconds:
```bash
py test/run_tests.py
```
Or using ComfyUI's embedded Python runtime:
```bash
& C:/AI/ComfyUI_windows_portable/python_embeded/python.exe test/run_tests.py
```

### 2. Run Specific Test Layers
```bash
# Unit tests only
py test/run_tests.py --unit

# Integration, schema & security tests only
py test/run_tests.py --integration

# Google Sheets connectivity tests only
py test/run_tests.py --connectivity
```

### 3. Run via Standard Python Unittest
```bash
py -m unittest discover -s test -p "test_*.py"
```

---

## QA Engineering Principles

1. **Deterministic & Isolated**: Tests run in-memory or inside temporary isolated folders (`tempfile`). No real LLM credits, ComfyUI server connections, or GPU VRAM are consumed.
2. **Zero Main Project Pollution**: All testing tools, runners, and configs live strictly inside `test/`. Root project files (`main.py`, `requirements.txt`, etc.) remain clean.
3. **100% Quiet Output**: Standard test runner stdout is completely clean of unmocked prompt banners or console noise.
4. **Comprehensive Coverage**: Covers data transformation, LLM response resilience, audio token math, typography parsing, master database gates, schema validation, music bank resolution, thumbnail prompt generation, and git privacy.
