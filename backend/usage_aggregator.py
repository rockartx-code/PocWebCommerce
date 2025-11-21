"""Daily aggregation job for raw usage metrics."""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, Iterable

from usage_tracker import UsageRecord, tracker


def aggregate_daily_usage(for_date: date | None = None) -> Iterable[UsageRecord]:
    """Aggregate raw events for a given day into per-tenant totals.

    The job is meant to be executed daily (e.g., via Lambda + EventBridge)
    to consolidate the usage table into a reporting-friendly format for
    the super administrator dashboard.
    """

    target_date = for_date or (datetime.utcnow().date() - timedelta(days=0))
    period = target_date.isoformat()

    totals: Dict[str, Dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for event in tracker.get_raw_events(for_period=period):
        usage = event.usage
        for key in ("requests", "orders", "gmv", "bytes"):
            totals[event.tenantId][key] += float(usage.get(key, 0))

    aggregated_records: list[UsageRecord] = []
    for tenant_id, usage_totals in totals.items():
        record = UsageRecord(
            tenantId=tenant_id,
            period=period,
            usage={
                "requests": usage_totals.get("requests", 0.0),
                "orders": usage_totals.get("orders", 0.0),
                "gmv": usage_totals.get("gmv", 0.0),
                "bytes": usage_totals.get("bytes", 0.0),
            },
            createdAt=datetime.utcnow().isoformat() + "Z",
        )
        tracker.append_aggregate(record)
        aggregated_records.append(record)

    return aggregated_records


def lambda_handler(event: dict, context: object | None = None) -> Dict[str, str]:
    period = (event or {}).get("period")
    for_date = date.fromisoformat(period) if period else None
    aggregated = list(aggregate_daily_usage(for_date=for_date))
    return {"message": f"Aggregated {len(aggregated)} tenants for period {aggregated[0].period if aggregated else period or date.today().isoformat()}"}
