Agent instructions for web browser engineering book project
===========================================================

This document contains instructions for AI agents (like Claude Code) working on
this project.


Python execution
----------------

When running Python commands in this project, always use `uv run python`
instead of direct `python` or `python3` commands.

### Examples:

~~~~ bash
# Running scripts
uv run python script.py

# Running modules
uv run python -m pytest

# Running the browser CLI
uv run python -m browser "http://example.com"
~~~~

### Rationale:

This project uses `uv` for dependency management and virtual environment
handling. Using `uv run python` ensures:

 -  The correct Python version is used
 -  All dependencies are available
 -  Consistent execution environment across different machines
 -  No need to manually activate virtual environments


Project structure
-----------------

 -  `browser/` - Main browser implementation
     -  `__main__.py` - CLI entry point using Typer
     -  `url.py` - URL parsing (HTTP, HTTPS, file, data schemes)
     -  `tab.py` - Tab abstraction
     -  `protocols/` - Protocol handlers (HTTP, HTTPS, file, data)
 -  `tests/` - Test suite
     -  `test_url.py` - URL parsing tests
     -  `test_cli_e2e.py` - E2E CLI tests with snapshot testing
     -  `fixtures/` - Test fixtures (sample files)


Testing
-------

Run tests using:

~~~~ bash
# Run all tests
uv run python -m pytest

# Run specific test file
uv run python -m pytest tests/test_cli_e2e.py

# Update snapshots (for syrupy snapshot tests)
uv run python -m pytest --snapshot-update

# Verbose output
uv run python -m pytest -v
~~~~


Dependencies
------------

 -  **Runtime**: `typer>=0.20.0`
 -  **Dev**: `pytest>=8.4.2`, `syrupy>=5.0.0`


CLI usage
---------

The browser CLI accepts a URL as an argument:

~~~~ bash
uv run python -m browser "http://example.com"
uv run python -m browser "file:///path/to/file.html"
uv run python -m browser "data:text/html,<h1>Hello</h1>"
~~~~
