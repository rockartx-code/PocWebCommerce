"""Lightweight usage tracking service for multi-tenant metrics."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List

import boto3
try:  # pragma: no cover - compatibility with stubs in repo
    from botocore.exceptions import BotoCoreError, ClientError
except ImportError:  # pragma: no cover
    from botocore.exceptions import ClientError

    class BotoCoreError(Exception):
        ...


@dataclass
class UsageRecord:
    tenantId: str
    period: str
    usage: Dict[str, float]
    createdAt: str
    metadata: Dict[str, str] = field(default_factory=dict)

    def as_item(self) -> Dict[str, object]:
        return {
            "tenantId": self.tenantId,
            "period": self.period,
            "usage": self.usage,
            "createdAt": self.createdAt,
            "metadata": self.metadata,
        }


class UsagePersistence:
    """Optional persistence layer for raw and aggregated events.

    The tracker keeps in-memory copies for fast tests while also
    persisting into DynamoDB or Firehose/S3 when the respective
    environment variables are present.
    """

    def __init__(self) -> None:
        self.raw_table = os.getenv("USAGE_EVENTS_TABLE")
        self.aggregate_table = os.getenv("USAGE_AGGREGATES_TABLE")
        self.firehose_stream = os.getenv("USAGE_FIREHOSE_STREAM")
        self._dynamodb = None
        self._firehose = None

    def _dynamodb_resource(self):
        if self._dynamodb is None:
            self._dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))
        return self._dynamodb

    def _firehose_client(self):
        if self._firehose is None:
            self._firehose = boto3.client("firehose", region_name=os.getenv("AWS_REGION", "us-east-1"))
        return self._firehose

    def persist_raw(self, record: UsageRecord) -> None:
        if self.raw_table:
            try:
                table = self._dynamodb_resource().Table(self.raw_table)
                table.put_item(Item=record.as_item())
            except (ClientError, BotoCoreError):  # pragma: no cover - defensive
                pass
        if self.firehose_stream:
            try:
                payload = json.dumps(record.as_item()) + "\n"
                self._firehose_client().put_record(DeliveryStreamName=self.firehose_stream, Record={"Data": payload})
            except (ClientError, BotoCoreError):  # pragma: no cover - defensive
                pass

    def persist_aggregate(self, record: UsageRecord) -> None:
        if self.aggregate_table:
            try:
                table = self._dynamodb_resource().Table(self.aggregate_table)
                table.put_item(Item=record.as_item())
            except (ClientError, BotoCoreError):  # pragma: no cover - defensive
                pass

    def fetch_events(self, period: str) -> Iterable[UsageRecord]:
        if not self.raw_table:
            return []
        try:
            table = self._dynamodb_resource().Table(self.raw_table)
            response = table.scan(
                FilterExpression="period = :period",
                ExpressionAttributeValues={":period": period},
            )
            items = response.get("Items", [])
            return [UsageRecord(**item) for item in items]
        except (ClientError, BotoCoreError):  # pragma: no cover - defensive
            return []

    def fetch_aggregates(self) -> Iterable[UsageRecord]:
        if not self.aggregate_table:
            return []
        try:
            table = self._dynamodb_resource().Table(self.aggregate_table)
            response = table.scan()
            items = response.get("Items", [])
            return [UsageRecord(**item) for item in items]
        except (ClientError, BotoCoreError):  # pragma: no cover - defensive
            return []


class UsageTracker:
    """In-memory tracker that simulates persistence in a metrics store.

    Records are shaped for storage in DynamoDB or RDS tables with
    composite keys `(tenantId, period)` and a nested `usage` payload
    including the counters requested by the platform stakeholders.
    """

    def __init__(self) -> None:
        self._raw_events: List[UsageRecord] = []
        self._aggregated: List[UsageRecord] = []
        self.persistence = UsagePersistence()
        self._aggregates_hydrated = False

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
        self.persistence.persist_raw(record)
        return record

    def append_aggregate(self, record: UsageRecord) -> None:
        self._aggregated.append(record)
        self.persistence.persist_aggregate(record)

    def get_raw_events(self, for_period: str | None = None) -> List[UsageRecord]:
        if for_period and self.persistence.raw_table:
            persisted = list(self.persistence.fetch_events(for_period))
            if persisted:
                return persisted
        if not for_period:
            return list(self._raw_events)
        return [record for record in self._raw_events if record.period == for_period]

    def get_aggregates(self) -> List[UsageRecord]:
        if not self._aggregates_hydrated and self.persistence.aggregate_table:
            self._aggregated.extend(list(self.persistence.fetch_aggregates()))
            self._aggregates_hydrated = True
        return list(self._aggregated)

    def reset(self) -> None:
        self._raw_events.clear()
        self._aggregated.clear()
        self._aggregates_hydrated = False

    def default_schedule(self) -> str:
        """Describe the default EventBridge schedule for documentation."""

        return "cron(5 0 * * ? *)"  # every day at 00:05 UTC


tracker = UsageTracker()
