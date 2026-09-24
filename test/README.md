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
├── integration/            # Layer 2: Component interaction & workflow integration tests
├── contracts/              # Layer 3: Data contract & schema conformance tests
├── security/               # Layer 4: Privacy, leak detection & security regression tests
└── connectivity/           # Layer 5: Google Sheets integration & data contract tests
```

---

## Quick Start & Execution

### 1. Run All Tests (Native Python Runner - Recommended)
Executes all **167 automated tests** across all 5 QA layers with zero external dependencies in ~4 seconds:
```bash
py test/run_tests.py
```

### 2. Run Specific Test Layers
```bash
# Unit tests only
py test/run_tests.py --unit

# Integration tests only
py test/run_tests.py --integration

# Contract & schema tests only
py test/run_tests.py --contract

# Security & privacy regression tests only
py test/run_tests.py --security

# Connectivity tests only
py test/run_tests.py --connectivity
```

### 3. Run via Standard Python Unittest
```bash
py -m unittest discover -s test -p "test_*.py"
```

### 4. Run via Pytest (Optional)
If you have `pytest` installed:
```bash
py -m pytest test/ -c test/pytest.ini
```

---

## QA Engineering Principles

1. **Deterministic & Isolated**: Tests run in-memory or inside temporary isolated folders (`tempfile`). No real LLM credits, ComfyUI server connections, or GPU VRAM are consumed.
2. **Zero Main Project Pollution**: All testing tools, runners, and configs live strictly inside `test_layer/`. Root project files (`main.py`, `requirements.txt`, etc.) remain clean.
3. **Comprehensive Coverage**: Covers data transformation, LLM response resilience, audio token math, typography parsing, master database gates, schema validation, and git security.
