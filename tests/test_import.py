"""Test imports and basic functionality."""

import pytest


def test_import_main_package():
    """Test that the main package can be imported."""
    import docuquery_ai
    assert hasattr(docuquery_ai, '__version__')
    assert hasattr(docuquery_ai, 'DocumentQueryClient')


def test_import_client():
    """Test that the client can be imported."""
    from docuquery_ai import DocumentQueryClient
    assert DocumentQueryClient is not None


def test_import_settings():
    """Test that settings can be imported."""
    from docuquery_ai import Settings
    assert Settings is not None


def test_import_models():
    """Test that models can be imported."""
    from docuquery_ai.models.pydantic_models import QueryRequest, QueryResponse
    assert QueryRequest is not None
    assert QueryResponse is not None


def test_version_format():
    """Test that version follows semantic versioning."""
    import docuquery_ai
    version = docuquery_ai.__version__
    parts = version.split('.')
    assert len(parts) >= 2  # At least major.minor
    assert all(part.isdigit() for part in parts[:2])  # Major and minor are digits


def test_cli_import():
    """Test that CLI can be imported."""
    from docuquery_ai.cli.main import main
    assert main is not None 