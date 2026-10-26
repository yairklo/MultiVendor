from datetime import datetime, timedelta, timezone

import pytest

from app.services.ai_tool_executor import execute_tool
from app.services.order_service import PAID_ORDER_STATUSES
from app.services.tenant_service import get_tenant_analytics_service


def _range():
    now = datetime.now(timezone.utc)
    return (now - timedelta(days=60)).isoformat(), (now + timedelta(days=1)).isoformat()


def test_shipped_counts_as_paid():
    assert {"processing", "shipped", "completed"} <= set(PAID_ORDER_STATUSES)
    assert "pending" not in PAID_ORDER_STATUSES


@pytest.mark.asyncio
async def test_chart_is_ascending_and_matches_kpi_totals(db_session):
    await execute_tool("update_order_status", {"order_id": 1, "status": "processing"}, "tenant-a", db_session)
    start, end = _range()
    result = await get_tenant_analytics_service("tenant-a", start, end, db_session)
    data = result["data"] if isinstance(result, dict) else result.data
    total = result["total_revenue"] if isinstance(result, dict) else result.total_revenue

    dates = [d["date"] for d in data]
    assert dates == sorted(dates)
    assert len(dates) == len(set(dates))
    assert total > 0
    assert sum(d["total_sales"] for d in data) == pytest.approx(total)


@pytest.mark.asyncio
async def test_chart_excludes_unpaid_orders(db_session):
    await execute_tool("update_order_status", {"order_id": 1, "status": "pending"}, "tenant-a", db_session)
    start, end = _range()
    result = await get_tenant_analytics_service("tenant-a", start, end, db_session)
    data = result["data"] if isinstance(result, dict) else result.data
    assert sum(d["total_sales"] for d in data) == 0
    assert sum(d["order_count"] for d in data) == 0
