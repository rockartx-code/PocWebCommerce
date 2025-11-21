import json
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Tuple

from usage_tracker import tracker


Headers = Dict[str, str]
LambdaResponse = Tuple[int, Dict[str, Any], Headers]
Route = Tuple[str, re.Pattern[str], Callable[[Dict[str, Any], Dict[str, str]], LambdaResponse], bool]


MAX_PAYMENT_RETRIES = 3
subscription_registry: Dict[str, Dict[str, Any]] = {}
payment_registry: List[Dict[str, Any]] = []


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


def extract_claims(event: Dict[str, Any]) -> Dict[str, Any]:
    request_context = event.get("requestContext") or {}
    authorizer = request_context.get("authorizer") or {}
    return authorizer.get("claims") or {}


def is_super_admin(event: Dict[str, Any]) -> bool:
    claims = extract_claims(event)
    role_claim = claims.get("role") or claims.get("custom:role") or claims.get("cognito:groups")
    if not role_claim:
        return False
    if isinstance(role_claim, str):
        normalized = {part.strip().lower() for part in re.split(r"[,\s]", role_claim) if part.strip()}
        return "super-admin" in normalized or "super_admin" in normalized
    if isinstance(role_claim, Iterable):
        normalized = {str(item).strip().lower() for item in role_claim}
        return "super-admin" in normalized or "super_admin" in normalized
    return False


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


def ensure_subscription(tenant_id: str, plan_id: str | None = None) -> Dict[str, Any]:
    subscription = subscription_registry.get(tenant_id)
    now_iso = datetime.utcnow().isoformat() + "Z"
    if not subscription:
        subscription = {
            "subscriptionId": f"{tenant_id}#sub-{uuid.uuid4().hex[:8]}",
            "tenantId": tenant_id,
            "planId": plan_id or "standard",
            "status": "active",
            "preferenceId": None,
            "nextBillingAt": (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z",
            "retryAttempts": 0,
            "updatedAt": now_iso,
            "createdAt": now_iso,
        }
        subscription_registry[tenant_id] = subscription
    elif plan_id:
        subscription["planId"] = plan_id
    return subscription


def log_payment(tenant_id: str, resource_id: str, status: str, amount: float | None, currency: str | None) -> Dict[str, Any]:
    receipt = {
        "receivedAt": datetime.utcnow().isoformat() + "Z",
        "resourceId": resource_id,
        "status": status,
        "tenantId": tenant_id,
        "amount": amount,
        "currency": currency or "USD",
    }
    payment_registry.append(receipt)
    return receipt


def update_subscription_status(subscription: Dict[str, Any], status: str) -> None:
    subscription["status"] = status
    subscription["updatedAt"] = datetime.utcnow().isoformat() + "Z"


def process_payment_status(
    tenant_id: str,
    resource_id: str,
    status: str,
    amount: float | None,
    currency: str | None,
) -> Dict[str, Any]:
    subscription = ensure_subscription(tenant_id)
    receipt = log_payment(tenant_id, resource_id, status, amount, currency)

    normalized_status = status.lower()
    successful_statuses = {"approved", "authorized"}
    pending_statuses = {"in_process", "pending"}

    if normalized_status in successful_statuses:
        subscription["retryAttempts"] = 0
        update_subscription_status(subscription, "active")
        subscription["nextBillingAt"] = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"
    elif normalized_status in pending_statuses:
        update_subscription_status(subscription, "pending")
    else:
        subscription["retryAttempts"] = subscription.get("retryAttempts", 0) + 1
        if subscription["retryAttempts"] >= MAX_PAYMENT_RETRIES:
            update_subscription_status(subscription, "suspended")
            subscription["suspendedReason"] = "payment_failed"
        else:
            update_subscription_status(subscription, "retrying")

    return receipt


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


def create_subscription_checkout(event: Dict[str, Any], params: Dict[str, str]) -> LambdaResponse:
    tenant_id = params.get("tenantId", "public")
    payload = parse_body(event)
    plan_id = payload.get("planId") or "standard"
    subscription = ensure_subscription(tenant_id, plan_id)
    subscription_id = payload.get("subscriptionId") or subscription.get("subscriptionId")
    preference_id = f"{tenant_id}#pref-sub-{uuid.uuid4().hex[:8]}"

    subscription.update(
        {
            "planId": plan_id,
            "subscriptionId": subscription_id,
            "preferenceId": preference_id,
            "status": "active",
            "retryAttempts": 0,
            "updatedAt": datetime.utcnow().isoformat() + "Z",
        }
    )

    checkout = {
        "tenantId": tenant_id,
        "subscriptionId": subscription_id,
        "planId": plan_id,
        "checkoutPreference": {
            "id": preference_id,
            "type": "recurring",
            "provider": "mercadopago",
        },
        "status": subscription["status"],
        "nextBillingAt": subscription.get("nextBillingAt"),
    }
    headers = {"X-MercadoPago-Preference": preference_id, "X-Tenant-Id": tenant_id}
    record_usage_event(event, tenant_id, requests=1)
    return 201, checkout, headers


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
    notification_type = payload.get("type") or payload.get("action") or "payment"
    data = payload.get("data") or {}
    resource_id = data.get("id") or "unknown"

    if notification_type.startswith("subscription"):
        plan_id = data.get("planId") or data.get("plan_id") or payload.get("planId")
        subscription = ensure_subscription(tenant_id, plan_id)
        subscription_status = data.get("status") or payload.get("status") or subscription.get("status", "active")
        update_subscription_status(subscription, subscription_status)
        receipt = {
            "receivedAt": datetime.utcnow().isoformat() + "Z",
            "resourceId": resource_id,
            "notificationType": notification_type,
            "status": subscription_status,
            "tenantId": tenant_id,
            "planId": subscription.get("planId"),
        }
    else:
        payment_status = data.get("status") or payload.get("status") or "pending"
        amount = data.get("transaction_amount") or data.get("amount")
        currency = data.get("currency_id") or data.get("currency")
        receipt = process_payment_status(tenant_id, resource_id, payment_status, amount, currency)
        receipt.update({"notificationType": notification_type})

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


def get_billing_status(event: Dict[str, Any], params: Dict[str, str]) -> LambdaResponse:
    tenant_id = params.get("tenantId", "public")
    subscription = subscription_registry.get(tenant_id)
    if not subscription:
        return 404, {"message": "Subscription not found", "tenantId": tenant_id}, {}

    payments = [p for p in payment_registry if p.get("tenantId") == tenant_id]
    response = {
        "tenantId": tenant_id,
        "subscription": subscription,
        "recentPayments": payments[-10:],
    }
    record_usage_event(event, tenant_id, requests=1)
    return 200, response, {}


def list_billing_status(event: Dict[str, Any], _: Dict[str, str]) -> LambdaResponse:
    if not is_super_admin(event):
        return 403, {"message": "Super admin role required"}, {}

    tenants: List[Dict[str, Any]] = []
    for tenant_id, subscription in subscription_registry.items():
        last_payment = next((p for p in reversed(payment_registry) if p.get("tenantId") == tenant_id), None)
        tenants.append(
            {
                "tenantId": tenant_id,
                "subscription": subscription,
                "lastPayment": last_payment,
                "billingHealth": "suspended" if subscription.get("status") == "suspended" else "ok",
            }
        )

    return 200, {"items": tenants, "total": len(tenants)}, {}


def list_tenant_usage(event: Dict[str, Any], _: Dict[str, str]) -> LambdaResponse:
    if not is_super_admin(event):
        return 403, {"message": "Super admin role required"}, {}

    params = event.get("queryStringParameters") or {}
    start_date = params.get("startDate")
    end_date = params.get("endDate")
    requested_metrics = params.get("metrics")

    try:
        start_date_obj = datetime.fromisoformat(start_date).date() if start_date else None
        end_date_obj = datetime.fromisoformat(end_date).date() if end_date else None
    except ValueError:
        return 400, {"message": "Invalid date format. Use YYYY-MM-DD."}, {}

    page = max(1, int(params.get("page", 1) or 1))
    page_size = min(100, max(1, int(params.get("pageSize", 20) or 20)))
    allowed_metrics = ["requests", "orders", "gmv", "bytes"]
    metrics = [m for m in (requested_metrics or "").split(",") if m in allowed_metrics] or allowed_metrics

    filtered_records = []
    for record in tracker.get_aggregates():
        period_date = datetime.fromisoformat(record.period).date()
        if start_date_obj and period_date < start_date_obj:
            continue
        if end_date_obj and period_date > end_date_obj:
            continue
        filtered_records.append(record)

    filtered_records.sort(key=lambda rec: (rec.period, rec.tenantId), reverse=True)
    total = len(filtered_records)

    start_index = (page - 1) * page_size
    paginated = filtered_records[start_index : start_index + page_size]

    summary = {metric: 0.0 for metric in metrics}
    items = []
    for record in paginated:
        usage_slice = {metric: float(record.usage.get(metric, 0)) for metric in metrics}
        for metric, value in usage_slice.items():
            summary[metric] += value
        items.append(
            {
                "tenantId": record.tenantId,
                "period": record.period,
                "usage": usage_slice,
                "createdAt": record.createdAt,
            }
        )

    body = {
        "items": items,
        "page": page,
        "pageSize": page_size,
        "total": total,
        "availableMetrics": metrics,
        "summary": summary,
        "filters": {"startDate": start_date, "endDate": end_date},
    }
    return 200, body, {}


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
    (
        "POST",
        re.compile(r"^/v1/(?P<tenantId>[^/]+)/subscriptions/checkout$"),
        create_subscription_checkout,
        True,
    ),
    ("POST", re.compile(r"^/v1/(?P<tenantId>[^/]+)/webhooks/mercadopago$"), handle_mercadopago_webhook, False),
    ("GET", re.compile(r"^/v1/(?P<tenantId>[^/]+)/analytics/sales$"), get_sales_analytics, True),
    ("GET", re.compile(r"^/v1/(?P<tenantId>[^/]+)/billing$"), get_billing_status, True),
    ("GET", re.compile(r"^/v1/admin/tenants/usage$"), list_tenant_usage, False),
    ("GET", re.compile(r"^/v1/admin/tenants/billing$"), list_billing_status, False),
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
