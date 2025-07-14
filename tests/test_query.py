import pytest

from docuquery_ai.db.models import HybridQuery
from docuquery_ai.query.engine import QueryEngine


@pytest.fixture
def query_engine():
    return QueryEngine()


@pytest.mark.asyncio
async def test_execute_query(query_engine):
    results = await query_engine.execute_query(HybridQuery(text="test query"))
    assert results == []
