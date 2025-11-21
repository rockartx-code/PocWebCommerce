from datetime import date

import usage_aggregator
from usage_tracker import tracker


def setup_function():
    tracker.reset()


def test_usage_events_are_stored_with_schema():
    record = tracker.record_usage(tenant_id="t-001", requests=2, orders=1, gmv=49.9, bytes_consumed=512)

    assert record.tenantId == "t-001"
    assert record.period
    assert record.usage["requests"] == 2
    assert record.usage["orders"] == 1
    assert record.usage["gmv"] == 49.9
    assert record.usage["bytes"] == 512


def test_daily_aggregation_rolls_up_usage():
    tracker.record_usage(tenant_id="t-001", requests=1, orders=1, gmv=20, bytes_consumed=100)
    tracker.record_usage(tenant_id="t-001", requests=2, orders=0, gmv=5, bytes_consumed=50)

    aggregated = list(usage_aggregator.aggregate_daily_usage(for_date=date.today()))

    assert len(aggregated) == 1
    assert aggregated[0].usage["requests"] == 3
    assert aggregated[0].usage["orders"] == 1
    assert aggregated[0].usage["gmv"] == 25
    assert aggregated[0].usage["bytes"] == 150
