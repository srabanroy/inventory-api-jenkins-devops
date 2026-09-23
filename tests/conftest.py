"""Shared fixtures for isolated API integration tests."""

from __future__ import annotations

import pytest

from inventory_api import create_app


@pytest.fixture
def app(tmp_path):
    database_path = tmp_path / "inventory-test.db"
    return create_app(
        {
            "TESTING": True,
            "DATABASE": str(database_path),
            "API_KEY": "test-api-key",
            "ENVIRONMENT": "test",
        }
    )


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authorised_headers():
    return {"X-API-Key": "test-api-key"}
