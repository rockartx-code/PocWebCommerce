import json
from datetime import datetime, timedelta

from app import handler


def build_event(
    path: str,
    http_method: str = "GET",
    tenant_claim: str = "t-123",
    extra_claims: dict | None = None,
    exp: datetime | None = None,
) -> dict:
    exp_time = exp or datetime.utcnow() + timedelta(minutes=5)
    claims = {"custom:tenantId": tenant_claim, "exp": exp_time.timestamp()}
    if extra_claims:
        claims.update(extra_claims)
    return {
        "path": path,
        "httpMethod": http_method,
        "headers": {},
        "body": None,
        "requestContext": {"authorizer": {"jwt": {"claims": claims}}},
    }


def test_tenant_mismatch_returns_403():
    event = build_event(
        "/v1/foreign-tenant/products",
        extra_claims={"allowedTenants": "t-123"},
    )
    response = handler(event, {})

    assert response["statusCode"] == 403
    assert "Tenant not allowed" in json.loads(response["body"]).get("message", "")


def test_unknown_route_masks_cross_tenant_access():
    event = build_event("/v1/other-tenant/secret-area")
    response = handler(event, {})

    assert response["statusCode"] == 404
    assert "Resource not found" in json.loads(response["body"]).get("message", "")


def test_expired_token_requests_refresh():
    expired_time = datetime.utcnow() - timedelta(minutes=1)
    event = build_event("/v1/t-123/products", exp=expired_time)

    response = handler(event, {})

    assert response["statusCode"] == 401
    assert "expired" in json.loads(response["body"]).get("message", "")
