"""Scheduled checks to compare aggregated usage against plan limits."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Dict, Iterable, List

from notification_service import NotificationService
from usage_plans import TenantContract, get_tenant_contract
from usage_tracker import UsageRecord, tracker

ALERT_THRESHOLDS = (0.8, 1.0)


@dataclass
class AlertEvent:
    tenantId: str
    metric: str
    value: float
    limit: float
    threshold: float
    period: str
    severity: str


def _evaluate_metric(record: UsageRecord, contract: TenantContract, notifier: NotificationService) -> Iterable[AlertEvent]:
    plan_limits = contract.plan.limits
    for metric in ("requests", "orders", "gmv"):
        limit = float(plan_limits.get(metric, 0))
        if limit <= 0:
            continue
        value = float(record.usage.get(metric, 0))
        if value <= 0:
            continue
        ratio = value / limit
        triggered = [threshold for threshold in ALERT_THRESHOLDS if ratio >= threshold]
        if not triggered:
            continue
        threshold = max(triggered)
        severity = "critical" if threshold >= 1.0 else "warning"
        notifier.notify_threshold(contract.adminContact, metric, value, limit, threshold)
        yield AlertEvent(
            tenantId=record.tenantId,
            metric=metric,
            value=value,
            limit=limit,
            threshold=threshold,
            period=record.period,
            severity=severity,
        )


def evaluate_usage_thresholds(record: UsageRecord, contract: TenantContract, notifier: NotificationService | None = None) -> List[AlertEvent]:
    notifier = notifier or NotificationService()
    return list(_evaluate_metric(record, contract, notifier))


def run_limit_checks(for_date: date | None = None, notifier: NotificationService | None = None) -> Dict[str, object]:
    notifier = notifier or NotificationService()
    target_date = for_date or date.today()
    period = target_date.isoformat()

    alerts: List[AlertEvent] = []
    evaluated = 0
    for record in tracker.get_aggregates():
        if record.period != period:
            continue
        contract = get_tenant_contract(record.tenantId)
        if not contract:
            continue
        evaluated += 1
        alerts.extend(evaluate_usage_thresholds(record, contract, notifier=notifier))

    return {
        "period": period,
        "evaluatedTenants": evaluated,
        "alerts": alerts,
        "notifications": notifier.sent_notifications,
        "checkedAt": datetime.utcnow().isoformat() + "Z",
    }
