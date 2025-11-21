from datetime import date

from notification_service import NotificationService
from usage_monitor import run_limit_checks
from usage_plans import register_contract, reset_registry
from usage_tracker import UsageRecord, tracker


def setup_function():
    tracker.reset()
    reset_registry()


def test_alerts_are_triggered_at_thresholds():
    register_contract(
        tenant_id="t-001",
        plan_id="starter",
        admin_contact={"email": "ops@t-001.example.com", "webhookUrl": "https://hooks.example.com/t-001"},
    )
    tracker.append_aggregate(
        UsageRecord(
            tenantId="t-001",
            period=date.today().isoformat(),
            usage={"requests": 850, "orders": 50, "gmv": 9000.0},
            createdAt="2024-06-01T00:00:00Z",
        )
    )

    notifier = NotificationService()
    result = run_limit_checks(for_date=date.today(), notifier=notifier)

    assert result["evaluatedTenants"] == 1
    alert_metrics = {alert.metric for alert in result["alerts"]}
    assert alert_metrics == {"requests", "gmv"}
    assert any(alert.threshold == 0.8 for alert in result["alerts"])
    assert len(notifier.sent_notifications) >= 2


def test_no_alerts_when_no_contract():
    tracker.append_aggregate(
        UsageRecord(
            tenantId="unknown",
            period=date.today().isoformat(),
            usage={"requests": 5000, "orders": 200, "gmv": 100000.0},
            createdAt="2024-06-01T00:00:00Z",
        )
    )

    notifier = NotificationService()
    result = run_limit_checks(for_date=date.today(), notifier=notifier)

    assert result["evaluatedTenants"] == 0
    assert result["alerts"] == []
    assert notifier.sent_notifications == []
