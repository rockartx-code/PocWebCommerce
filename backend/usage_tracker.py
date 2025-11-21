"""Lightweight usage tracking service for multi-tenant metrics."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List


@dataclass
class UsageRecord:
    tenantId: str
    period: str
    usage: Dict[str, float]
    createdAt: str
    metadata: Dict[str, str] = field(default_factory=dict)


class UsageTracker:
    """In-memory tracker that simulates persistence in a metrics store.

    Records are shaped for storage in DynamoDB or RDS tables with
    composite keys `(tenantId, period)` and a nested `usage` payload
    including the counters requested by the platform stakeholders.
    """

    def __init__(self) -> None:
        self._raw_events: List[UsageRecord] = []
        self._aggregated: List[UsageRecord] = []

    def record_usage(
        self,
        tenant_id: str,
        requests: int = 0,
        orders: int = 0,
        gmv: float = 0.0,
        bytes_consumed: int = 0,
        timestamp: datetime | None = None,
        metadata: Dict[str, str] | None = None,
    ) -> UsageRecord:
        ts = timestamp or datetime.utcnow()
        period = ts.strftime("%Y-%m-%d")
        record = UsageRecord(
            tenantId=tenant_id,
            period=period,
            usage={
                "requests": float(requests),
                "orders": float(orders),
                "gmv": float(gmv),
                "bytes": float(bytes_consumed),
            },
            createdAt=ts.isoformat() + "Z",
            metadata=metadata or {},
        )
        self._raw_events.append(record)
        return record

    def append_aggregate(self, record: UsageRecord) -> None:
        self._aggregated.append(record)

    def get_raw_events(self) -> List[UsageRecord]:
        return list(self._raw_events)

    def get_aggregates(self) -> List[UsageRecord]:
        return list(self._aggregated)

    def reset(self) -> None:
        self._raw_events.clear()
        self._aggregated.clear()


tracker = UsageTracker()
