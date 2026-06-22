"""
conftest.py — pytest fixtures shared across all tests.
Unit tests use these sparingly; integration tests depend on them heavily.
"""

import pytest


# ── Basic markers ─────────────────────────────────────────────────────────────
# Usage: @pytest.mark.unit   @pytest.mark.integration
def pytest_configure(config):
    config.addinivalue_line("markers", "unit: fast tests, no external services")
    config.addinivalue_line("markers", "integration: requires live postgres + redis")
