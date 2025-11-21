import json

from app import handler


def build_event(
    path: str, http_method: str = "GET", tenant_claim: str = "t-123", extra_claims: dict | None = None
) -> dict:
    claims = {"custom:tenantId": tenant_claim}
    if extra_claims:
        claims.update(extra_claims)
    return {
        "path": path,
        "httpMethod": http_method,
        "headers": {},
        "body": None,
        "requestContext": {"authorizer": {"claims": claims}},
    }


def test_tenant_mismatch_returns_403():
    event = build_event("/v1/foreign-tenant/products")
    response = handler(event, {})

    assert response["statusCode"] == 403
    assert "Tenant mismatch" in json.loads(response["body"]).get("message", "")


def test_unknown_route_masks_cross_tenant_access():
    event = build_event("/v1/other-tenant/secret-area")
    response = handler(event, {})

    assert response["statusCode"] == 404
    assert "Resource not found" in json.loads(response["body"]).get("message", "")


def test_super_admin_can_operate_cross_tenant():
    event = build_event(
        "/v1/foreign-tenant/products",
        extra_claims={"roles": ["admin", "super_admin"], "tenantId": "t-origin"},
    )

    response = handler(event, {})

    assert response["statusCode"] == 200
