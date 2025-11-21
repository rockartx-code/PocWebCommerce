import json
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, Tuple

from usage_tracker import tracker


Headers = Dict[str, str]
LambdaResponse = Tuple[int, Dict[str, Any], Headers]
Route = Tuple[str, re.Pattern[str], Callable[[Dict[str, Any], Dict[str, str]], LambdaResponse], bool]


def build_response(status_code: int, body: Dict[str, Any], extra_headers: Headers | None = None) -> Dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Authorization,Content-Type,X-Tenant-Id",
        "Access-Control-Allow-Methods": "GET,POST,OPTIONS",
    }
    if extra_headers:
        headers.update(extra_headers)
    return {
        "statusCode": status_code,
        "headers": headers,
        "body": json.dumps(body),
    }


def parse_body(event: Dict[str, Any]) -> Dict[str, Any]:
    raw_body = event.get("body")
    if not raw_body:
        return {}
    try:
        return json.loads(raw_body)
    except (json.JSONDecodeError, TypeError):
        return {}


def record_usage_event(
    event: Dict[str, Any],
    tenant_id: str,
    *,
    requests: int = 0,
    orders: int = 0,
    gmv: float = 0.0,
) -> None:
    body_size = len((event.get("body") or "").encode())
    tracker.record_usage(
        tenant_id=tenant_id,
        requests=requests,
        orders=orders,
        gmv=gmv,
        bytes_consumed=body_size,
    )


def create_tenant(event: Dict[str, Any], _: Dict[str, str]) -> LambdaResponse:
    payload = parse_body(event)
    tenant_id = payload.get("tenantId") or f"t-{uuid.uuid4().hex[:8]}"
    admin_email = payload.get("adminEmail") or f"admin@{tenant_id}.example.com"
    onboarding_token = uuid.uuid4().hex
    backoffice_url = f"https://admin.poc-web-commerce.example/?tenantId={tenant_id}&token={onboarding_token}"
    tenant = {
        "tenantId": tenant_id,
        "name": payload.get("name", "Nueva tienda"),
        "industry": payload.get("industry", "retail"),
        "status": "active",
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "preferredCurrency": payload.get("currency", "USD"),
        "paymentProvider": payload.get("paymentProvider", "mercadopago"),
        "branding": payload.get("branding", {}),
    }
    admin_user = {
        "userId": f"{tenant_id}#adm-{uuid.uuid4().hex[:6]}",
        "email": admin_email,
        "role": "admin",
        "temporaryPassword": payload.get("temporaryPassword") or uuid.uuid4().hex[:12],
        "loginUrl": backoffice_url,
    }
    urls = {
        "storefront": f"https://{tenant_id}.poc-web-commerce.example",
        "backoffice": backoffice_url,
        "apiBase": f"https://api.poc-web-commerce.example/v1/{tenant_id}",
    }
    body = {
        "tenant": tenant,
        "adminUser": admin_user,
        "urls": urls,
        "onboardingToken": onboarding_token,
    }
    headers = {"X-Tenant-Id": tenant_id}
    record_usage_event(event, tenant_id, requests=1)
    return 201, body, headers


def create_tenant_user(event: Dict[str, Any], params: Dict[str, str]) -> LambdaResponse:
    tenant_id = params.get("tenantId") or "public"
    payload = parse_body(event)
    user = {
        "userId": payload.get("userId") or f"{tenant_id}#usr-{uuid.uuid4().hex[:8]}",
        "email": payload.get("email", "owner@example.com"),
        "role": payload.get("role", "admin"),
        "status": "invited",
        "temporaryPassword": payload.get("temporaryPassword") or uuid.uuid4().hex[:12],
        "createdAt": datetime.utcnow().isoformat() + "Z",
    }
    response = {
        "tenantId": tenant_id,
        "user": user,
        "loginUrl": f"https://admin.poc-web-commerce.example/?tenantId={tenant_id}",
        "support": "onboarding@poc-web-commerce.example",
    }
    headers = {"X-Tenant-Id": tenant_id}
    record_usage_event(event, tenant_id, requests=1)
    return 201, response, headers


def get_products(_: Dict[str, Any], params: Dict[str, str]) -> LambdaResponse:
    tenant_id = params.get("tenantId", "public")
    products = [
        {
            "tenantId": tenant_id,
            "productId": f"{tenant_id}#prd-001",
            "name": "Camiseta Tech",
            "price": 19.99,
            "currency": "USD",
            "stock": 42,
            "category": "apparel",
            "assetPrefix": f"s3://commerce-assets/{tenant_id}/products/prd-001",
        },
        {
            "tenantId": tenant_id,
            "productId": f"{tenant_id}#prd-002",
            "name": "Zapatillas Runner",
            "price": 89.9,
            "currency": "USD",
            "stock": 12,
            "category": "footwear",
            "assetPrefix": f"s3://commerce-assets/{tenant_id}/products/prd-002",
        },
    ]
    record_usage_event({}, tenant_id, requests=1)
    return 200, {"items": products, "count": len(products)}, {}


def get_product_by_id(event: Dict[str, Any], params: Dict[str, str]) -> LambdaResponse:
    product_id = params.get("productId") or (event.get("pathParameters") or {}).get("id")
    tenant_id = params.get("tenantId", "public")
    product = {
        "tenantId": tenant_id,
        "productId": product_id,
        "name": "Producto Demo",
        "description": "Detalle del producto solicitado",
        "price": 49.5,
        "currency": "USD",
        "stock": 8,
        "assetPrefix": f"s3://commerce-assets/{tenant_id}/products/{product_id}",
    }
    record_usage_event(event, tenant_id, requests=1)
    return 200, product, {}


def create_cart(event: Dict[str, Any], params: Dict[str, str]) -> LambdaResponse:
    payload = parse_body(event)
    tenant_id = params.get("tenantId", "public")
    items = payload.get("items", [])
    cart_id = payload.get("cartId") or f"{tenant_id}#cart-{uuid.uuid4().hex[:8]}"
    totals = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
    expires_at = (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z"
    cart = {
        "tenantId": tenant_id,
        "cartId": cart_id,
        "items": items,
        "totals": {"amount": round(totals, 2), "currency": payload.get("currency", "USD")},
        "expiresAt": expires_at,
    }
    record_usage_event(event, tenant_id, requests=1, gmv=totals)
    return 201, cart, {}


def get_cart(event: Dict[str, Any], params: Dict[str, str]) -> LambdaResponse:
    user_id = (event.get("queryStringParameters") or {}).get("userId", "guest")
    tenant_id = params.get("tenantId", "public")
    cart = {
        "tenantId": tenant_id,
        "cartId": f"{tenant_id}#cart-{user_id}",
        "items": [
            {"productId": "prd-001", "quantity": 1, "price": 19.99},
            {"productId": "prd-002", "quantity": 2, "price": 89.9},
        ],
        "totals": {"amount": 199.79, "currency": "USD"},
        "userId": user_id,
    }
    record_usage_event(event, tenant_id, requests=1)
    return 200, cart, {}


def create_order(event: Dict[str, Any], params: Dict[str, str]) -> LambdaResponse:
    payload = parse_body(event)
    tenant_id = params.get("tenantId", "public")
    order_id = f"{tenant_id}#ord-{uuid.uuid4().hex[:10]}"
    preference_id = f"{tenant_id}#pref-{uuid.uuid4().hex[:6]}"
    order = {
        "tenantId": tenant_id,
        "orderId": order_id,
        "amount": payload.get("amount", 0),
        "currency": payload.get("currency", "USD"),
        "items": payload.get("items", []),
        "paymentPreferenceId": preference_id,
        "paymentStatus": "pending",
        "status": "created",
    }
    headers = {"X-MercadoPago-Preference": preference_id}
    record_usage_event(event, tenant_id, requests=1, orders=1, gmv=payload.get("amount", 0))
    return 201, order, headers


def handle_mercadopago_webhook(event: Dict[str, Any], params: Dict[str, str]) -> LambdaResponse:
    payload = parse_body(event)
    tenant_id = params.get("tenantId", "public")
    notification_type = payload.get("type", "payment")
    resource_id = payload.get("data", {}).get("id", "unknown")
    receipt = {
        "receivedAt": datetime.utcnow().isoformat() + "Z",
        "resourceId": resource_id,
        "notificationType": notification_type,
        "status": "acknowledged",
        "tenantId": tenant_id,
    }
    record_usage_event(event, tenant_id, requests=1)
    return 200, receipt, {}


def get_sales_analytics(_: Dict[str, Any], params: Dict[str, str]) -> LambdaResponse:
    now = datetime.utcnow()
    tenant_id = params.get("tenantId", "public")
    metrics = {
        "period": now.strftime("%Y-%m-%d"),
        "tenantId": tenant_id,
        "totals": {"revenue": 15230.75, "currency": "USD", "orders": 178},
        "topProducts": [
            {"productId": "prd-002", "name": "Zapatillas Runner", "orders": 54},
            {"productId": "prd-001", "name": "Camiseta Tech", "orders": 39},
        ],
        "paymentStatus": {"approved": 162, "pending": 9, "rejected": 7},
    }
    record_usage_event({}, tenant_id, requests=1)
    return 200, metrics, {}


def extract_tenant_id(event: Dict[str, Any]) -> str | None:
    authorizer = (event.get("requestContext") or {}).get("authorizer") or {}
    claims = authorizer.get("claims") or {}
    tenant_id = claims.get("custom:tenantId") or claims.get("tenantId")
    if not tenant_id:
        return None
    return str(tenant_id)


def inject_tenant(event: Dict[str, Any], params: Dict[str, str]) -> Tuple[str | None, Dict[str, Any], Dict[str, str], str | None]:
    tenant_id = extract_tenant_id(event)
    if not tenant_id:
        return None, event, params, None
    path_tenant = (
        params.get("tenantId")
        or (event.get("pathParameters") or {}).get("tenantId")
        or (event.get("queryStringParameters") or {}).get("tenantId")
        or (event.get("headers") or {}).get("x-tenant-id")
    )
    event_with_tenant = {**event, "tenantId": tenant_id}
    params_with_tenant = {**params, "tenantId": tenant_id}
    return tenant_id, event_with_tenant, params_with_tenant, path_tenant


ROUTES: Iterable[Route] = (
    ("POST", re.compile(r"^/v1/tenants$"), create_tenant, False),
    ("POST", re.compile(r"^/v1/tenants/(?P<tenantId>[^/]+)/users$"), create_tenant_user, False),
    ("GET", re.compile(r"^/v1/(?P<tenantId>[^/]+)/products$"), get_products, True),
    ("GET", re.compile(r"^/v1/(?P<tenantId>[^/]+)/products/(?P<productId>[^/]+)$"), get_product_by_id, True),
    ("POST", re.compile(r"^/v1/(?P<tenantId>[^/]+)/cart$"), create_cart, True),
    ("GET", re.compile(r"^/v1/(?P<tenantId>[^/]+)/cart$"), get_cart, True),
    ("POST", re.compile(r"^/v1/(?P<tenantId>[^/]+)/orders$"), create_order, True),
    ("POST", re.compile(r"^/v1/(?P<tenantId>[^/]+)/webhooks/mercadopago$"), handle_mercadopago_webhook, False),
    ("GET", re.compile(r"^/v1/(?P<tenantId>[^/]+)/analytics/sales$"), get_sales_analytics, True),
)


def route_event(event: Dict[str, Any]) -> Dict[str, Any]:
    path = event.get("path", "")
    http_method = event.get("httpMethod", "")

    for method, pattern, handler, requires_tenant in ROUTES:
        if http_method != method:
            continue
        match = pattern.match(path)
        if not match:
            continue
        params = match.groupdict()
        if requires_tenant:
            tenant_id, event, params, path_tenant = inject_tenant(event, params)
            if not tenant_id:
                return build_response(401, {"message": "Missing tenantId claim"})
            if path_tenant and path_tenant != tenant_id:
                return build_response(403, {"message": "Tenant mismatch"})
        status_code, payload, headers = handler(event, params)
        return build_response(status_code, payload, headers)

    return build_response(404, {"message": "Resource not found", "path": path})


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        if event.get("httpMethod") == "OPTIONS":
            return build_response(200, {"message": "OK"})
        return route_event(event)
    except Exception as exc:  # noqa: BLE001
        return build_response(500, {"message": "Internal server error", "error": str(exc)})
