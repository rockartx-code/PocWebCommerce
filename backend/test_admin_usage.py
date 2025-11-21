import json
from datetime import date

from app import handler
from usage_tracker import UsageRecord, tracker


def setup_function():
    tracker.reset()


def build_admin_event(path: str, query: dict | None = None, claims: dict | None = None) -> dict:
    return {
        "path": path,
        "httpMethod": "GET",
        "headers": {},
        "body": None,
        "queryStringParameters": query or {},
        "requestContext": {"authorizer": {"claims": claims or {}}},
    }


def test_route_requires_super_admin_role():
    event = build_admin_event("/v1/admin/tenants/usage")

    response = handler(event, {})

    assert response["statusCode"] == 403
    assert "Super admin" in json.loads(response["body"]).get("message", "")


def test_usage_listing_applies_filters_and_pagination():
    tracker.append_aggregate(
        UsageRecord(
            tenantId="t-1",
            period=date(2024, 5, 1).isoformat(),
            usage={"requests": 5, "orders": 1, "gmv": 100.0, "bytes": 1024},
            createdAt="2024-05-01T00:00:00Z",
        )
    )
    tracker.append_aggregate(
        UsageRecord(
            tenantId="t-2",
            period=date(2024, 5, 2).isoformat(),
            usage={"requests": 8, "orders": 2, "gmv": 250.0, "bytes": 2048},
            createdAt="2024-05-02T00:00:00Z",
        )
    )

    event = build_admin_event(
        "/v1/admin/tenants/usage",
        query={"startDate": "2024-05-01", "endDate": "2024-05-02", "metrics": "requests,gmv", "pageSize": "1"},
        claims={"roles": ["super_admin"]},
    )

    response = handler(event, {})
    body = json.loads(response["body"])

    assert response["statusCode"] == 200
    assert body["page"] == 1
    assert body["pageSize"] == 1
    assert body["total"] == 2
    assert body["items"][0]["usage"].keys() == {"requests", "gmv"}
    assert body["items"][0]["tenantId"] in {"t-1", "t-2"}
