import json
import os
import re
import time
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, List, Tuple

import boto3
from botocore.exceptions import ClientError

from usage_tracker import tracker


Headers = Dict[str, str]
LambdaResponse = Tuple[int, Dict[str, Any], Headers]
Route = Tuple[
    str,
    re.Pattern[str],
    Callable[[Dict[str, Any], Dict[str, str]], LambdaResponse],
    bool,
    bool,
]


MAX_PAYMENT_RETRIES = 3


def _dynamodb_resource():
    return boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-1"))


class DynamoRepository:
    def __init__(self, table_env: str) -> None:
        self.table_name = os.environ.get(table_env)
        if not self.table_name:
            raise RuntimeError(f"Missing DynamoDB table env var: {table_env}")
        self.table = _dynamodb_resource().Table(self.table_name)

    def put_item(self, item: Dict[str, Any]) -> None:
        for attempt in range(3):
            try:
                self.table.put_item(Item=item)
                return
            except ClientError as exc:  # pragma: no cover - retried
                if attempt >= 2:
                    raise
                time.sleep(0.1 * (2**attempt))

    def get_item(self, key: Dict[str, Any]) -> Dict[str, Any] | None:
        try:
            response = self.table.get_item(Key=key)
        except ClientError:
            return None
        return response.get("Item")

    def query_by_tenant(self, tenant_id: str) -> List[Dict[str, Any]]:
        try:
            if tenant_id == "*":
                response = self.table.scan()
            else:
                response = self.table.scan(
                    FilterExpression="tenantId = :tenantId",
                    ExpressionAttributeValues={":tenantId": tenant_id},
                )
        except ClientError:
            return []
        return response.get("Items", [])


class TenantRepository(DynamoRepository):
    def save(self, tenant: Dict[str, Any]) -> None:
        onboarding_record = {"transactionId": f"{tenant['tenantId']}#onboarding", **tenant}
        self.put_item(onboarding_record)


class CartRepository(DynamoRepository):
    def save(self, cart: Dict[str, Any]) -> None:
        self.put_item(cart)

    def get(self, cart_id: str) -> Dict[str, Any] | None:
        return self.get_item({"cartId": cart_id})


class OrderRepository(DynamoRepository):
    def save(self, order: Dict[str, Any]) -> None:
        self.put_item(order)

    def get(self, order_id: str) -> Dict[str, Any] | None:
        return self.get_item({"orderId": order_id})


class SubscriptionRepository(DynamoRepository):
    def __init__(self, table_env: str) -> None:
        super().__init__(table_env)

    def _subscription_key(self, tenant_id: str) -> Dict[str, Any]:
        return {"transactionId": f"{tenant_id}#subscription"}

    def get_subscription(self, tenant_id: str) -> Dict[str, Any]:
        existing = self.get_item(self._subscription_key(tenant_id)) or {}
        if existing:
            return existing
        now_iso = datetime.utcnow().isoformat() + "Z"
        return {
            "transactionId": f"{tenant_id}#subscription",
            "tenantId": tenant_id,
            "status": "active",
            "retryAttempts": 0,
            "createdAt": now_iso,
            "updatedAt": now_iso,
        }

    def update_subscription(self, subscription: Dict[str, Any]) -> Dict[str, Any]:
        subscription["updatedAt"] = datetime.utcnow().isoformat() + "Z"
        self.put_item(subscription)
        return subscription

    def log_payment(self, receipt: Dict[str, Any]) -> None:
        self.put_item(receipt)

    def list_payments(self, tenant_id: str) -> List[Dict[str, Any]]:
        return sorted(self.query_by_tenant(tenant_id), key=lambda item: item.get("receivedAt", ""))


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


def get_claims(event: Dict[str, Any]) -> Dict[str, Any]:
    request_context = event.get("requestContext") or {}
    authorizer = request_context.get("authorizer") or {}
    jwt_context = authorizer.get("jwt") or {}
    return jwt_context.get("claims") or authorizer.get("claims") or {}


class AuthError(Exception):
    def __init__(self, status_code: int, message: str, *, details: Dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.details = details or {}


def validate_token(event: Dict[str, Any]) -> Dict[str, Any]:
    claims = get_claims(event)
    if not claims:
        raise AuthError(401, "Missing authorization context")

    exp = claims.get("exp")
    now = datetime.utcnow().timestamp()
    if exp and float(exp) <= now:
        refresh_token = (event.get("headers") or {}).get("X-Refresh-Token")
        message = "Token expired. Refresh required."
        details = {"refreshTokenProvided": bool(refresh_token)}
        raise AuthError(401, message, details=details)

    return claims


def require_admin(claims: Dict[str, Any]) -> None:
    roles = claims.get("cognito:groups") or claims.get("roles") or []
    if isinstance(roles, str):
        roles = [role.strip() for role in roles.split(",") if role.strip()]
    normalized = {str(role).lower() for role in roles}
    if "admin" not in normalized and "super_admin" not in normalized:
        raise AuthError(403, "Admin permissions required")


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


tenant_repository: TenantRepository | None = None
cart_repository: CartRepository | None = None
order_repository: OrderRepository | None = None
subscription_repository: SubscriptionRepository | None = None


def _get_repositories() -> Tuple[TenantRepository, CartRepository, OrderRepository, SubscriptionRepository]:
    global tenant_repository, cart_repository, order_repository, subscription_repository
    if tenant_repository is None:
        tenant_repository = TenantRepository("TRANSACTIONS_TABLE")
    if cart_repository is None:
        cart_repository = CartRepository("CARTS_TABLE")
    if order_repository is None:
        order_repository = OrderRepository("ORDERS_TABLE")
    if subscription_repository is None:
        subscription_repository = SubscriptionRepository("TRANSACTIONS_TABLE")
    return tenant_repository, cart_repository, order_repository, subscription_repository


def process_payment_status(
    tenant_id: str,
    resource_id: str,
    status: str,
    amount: float | None,
    currency: str | None,
) -> Dict[str, Any]:
    _, _, _, subscriptions = _get_repositories()
    subscription = subscriptions.get_subscription(tenant_id)
    normalized_status = status.lower()
    successful_statuses = {"approved", "authorized"}
    pending_statuses = {"in_process", "pending"}

    if normalized_status in successful_statuses:
        subscription["retryAttempts"] = 0
        subscription["status"] = "active"
        subscription["nextBillingAt"] = (datetime.utcnow() + timedelta(days=30)).isoformat() + "Z"
    elif normalized_status in pending_statuses:
        subscription["status"] = "pending"
    else:
        subscription["retryAttempts"] = subscription.get("retryAttempts", 0) + 1
        subscription["status"] = "retrying"
        if subscription["retryAttempts"] >= MAX_PAYMENT_RETRIES:
            subscription["status"] = "suspended"
            subscription["suspendedReason"] = "payment_failed"

    subscriptions.update_subscription(subscription)

    transaction_id = resource_id if resource_id.startswith(tenant_id) else f"{tenant_id}#{resource_id}"
    receipt = {
        "transactionId": transaction_id,
        "receivedAt": datetime.utcnow().isoformat() + "Z",
        "resourceId": resource_id,
        "status": status,
        "tenantId": tenant_id,
        "amount": amount,
        "currency": currency or "USD",
    }
    subscriptions.log_payment(receipt)
    return receipt


def create_tenant(event: Dict[str, Any], _: Dict[str, str]) -> LambdaResponse:
    tenants, _, _, _ = _get_repositories()
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
    tenants.save({"tenantId": tenant_id, **tenant, "onboardingToken": onboarding_token})
    headers = {"X-Tenant-Id": tenant_id}
    record_usage_event(event, tenant_id, requests=1)
    return 201, body, headers


def create_subscription_checkout(event: Dict[str, Any], params: Dict[str, str]) -> LambdaResponse:
    tenant_id = params.get("tenantId", "public")
    payload = parse_body(event)
    plan_id = payload.get("planId") or "standard"
    _, _, _, subscriptions = _get_repositories()
    subscription = subscriptions.get_subscription(tenant_id)
    subscription_id = payload.get("subscriptionId") or subscription.get("subscriptionId") or f"{tenant_id}#sub-{uuid.uuid4().hex[:8]}"
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
    subscriptions.update_subscription(subscription)

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
    _, carts, _, _ = _get_repositories()
    payload = parse_body(event)
    tenant_id = params.get("tenantId", "public")
    items = payload.get("items", [])
    cart_id = payload.get("cartId") or f"{tenant_id}#cart-{uuid.uuid4().hex[:8]}"
    totals = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
    expires_at = datetime.utcnow() + timedelta(hours=2)
    cart = {
        "tenantId": tenant_id,
        "cartId": cart_id,
        "items": items,
        "totals": {"amount": round(totals, 2), "currency": payload.get("currency", "USD")},
        "expiresAt": expires_at.isoformat() + "Z",
        "ttl": int(expires_at.timestamp()),
    }
    carts.save(cart)
    record_usage_event(event, tenant_id, requests=1, gmv=totals)
    return 201, cart, {}


def get_cart(event: Dict[str, Any], params: Dict[str, str]) -> LambdaResponse:
    _, carts, _, _ = _get_repositories()
    user_id = (event.get("queryStringParameters") or {}).get("userId", "guest")
    tenant_id = params.get("tenantId", "public")
    cart_id = f"{tenant_id}#cart-{user_id}"
    cart = carts.get(cart_id)
    if not cart:
        cart = {
            "tenantId": tenant_id,
            "cartId": cart_id,
            "items": [],
            "totals": {"amount": 0.0, "currency": "USD"},
            "userId": user_id,
        }
    record_usage_event(event, tenant_id, requests=1)
    return 200, cart, {}


def create_order(event: Dict[str, Any], params: Dict[str, str]) -> LambdaResponse:
    _, _, orders, _ = _get_repositories()
    payload = parse_body(event)
    tenant_id = params.get("tenantId", "public")
    order_id = f"{tenant_id}#ord-{uuid.uuid4().hex[:10]}"
    preference_id = f"{tenant_id}#pref-{uuid.uuid4().hex[:6]}"
    now_iso = datetime.utcnow().isoformat() + "Z"
    order = {
        "tenantId": tenant_id,
        "orderId": order_id,
        "amount": payload.get("amount", 0),
        "currency": payload.get("currency", "USD"),
        "items": payload.get("items", []),
        "paymentPreferenceId": preference_id,
        "paymentStatus": "pending",
        "status": "created",
        "createdAt": now_iso,
        "updatedAt": now_iso,
    }
    orders.save(order)
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
        receipt = process_payment_status(
            tenant_id,
            resource_id,
            data.get("status") or payload.get("status") or "pending",
            data.get("amount"),
            data.get("currency"),
        )
        receipt.update({"notificationType": notification_type, "planId": plan_id})
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
    _, _, _, subscriptions = _get_repositories()
    tenant_id = params.get("tenantId", "public")
    subscription = subscriptions.get_subscription(tenant_id)
    payments = subscriptions.list_payments(tenant_id)[-10:]
    response = {
        "tenantId": tenant_id,
        "subscription": subscription,
        "recentPayments": payments,
    }
    record_usage_event(event, tenant_id, requests=1)
    return 200, response, {}


def list_billing_status(event: Dict[str, Any], _: Dict[str, str]) -> LambdaResponse:
    _, _, _, subscriptions = _get_repositories()
    claims = validate_token(event)
    require_admin(claims)

    tenants: List[Dict[str, Any]] = []
    all_records = subscriptions.query_by_tenant(tenant_id="*")  # type: ignore[arg-type]
    tenant_ids = {rec.get("tenantId") for rec in all_records if rec.get("tenantId")}
    for tenant_id in tenant_ids:
        subscription = subscriptions.get_subscription(str(tenant_id))
        last_payment = next((p for p in reversed(subscriptions.list_payments(str(tenant_id))) if p.get("tenantId") == tenant_id), None)
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
    claims = validate_token(event)
    require_admin(claims)

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


def extract_tenant_id_from_claims(claims: Dict[str, Any]) -> str | None:
    tenant_id = (
        claims.get("custom:tenantId")
        or claims.get("tenantId")
        or claims.get("tenant_id")
        or claims.get("tenant")
    )
    if not tenant_id:
        return None
    return str(tenant_id)


def inject_tenant(
    event: Dict[str, Any], params: Dict[str, str], *, claims: Dict[str, Any]
) -> Tuple[str | None, Dict[str, Any], Dict[str, str], str | None]:
    tenant_claim = extract_tenant_id_from_claims(claims)
    path_tenant = (
        params.get("tenantId")
        or (event.get("pathParameters") or {}).get("tenantId")
        or (event.get("queryStringParameters") or {}).get("tenantId")
        or (event.get("headers") or {}).get("x-tenant-id")
    )

    allowed = claims.get("allowedTenants") or []
    if isinstance(allowed, str):
        allowed = [tenant.strip() for tenant in allowed.split(",") if tenant.strip()]

    resolved_tenant = path_tenant or tenant_claim
    if not resolved_tenant:
        raise AuthError(401, "Missing tenantId claim")
    if path_tenant and allowed and path_tenant not in allowed and path_tenant != tenant_claim:
        raise AuthError(403, "Tenant not allowed by policy")

    event_with_tenant = {**event, "tenantId": resolved_tenant}
    params_with_tenant = {**params}
    if resolved_tenant:
        params_with_tenant["tenantId"] = resolved_tenant
    return resolved_tenant, event_with_tenant, params_with_tenant, path_tenant


ROUTES: Iterable[Route] = (
    ("POST", re.compile(r"^/v1/tenants$"), create_tenant, False, False),
    ("POST", re.compile(r"^/v1/tenants/(?P<tenantId>[^/]+)/users$"), create_tenant_user, True, True),
    ("GET", re.compile(r"^/v1/(?P<tenantId>[^/]+)/products$"), get_products, True, True),
    (
        "GET",
        re.compile(r"^/v1/(?P<tenantId>[^/]+)/products/(?P<productId>[^/]+)$"),
        get_product_by_id,
        True,
        True,
    ),
    ("POST", re.compile(r"^/v1/(?P<tenantId>[^/]+)/cart$"), create_cart, True, True),
    ("GET", re.compile(r"^/v1/(?P<tenantId>[^/]+)/cart$"), get_cart, True, True),
    ("POST", re.compile(r"^/v1/(?P<tenantId>[^/]+)/orders$"), create_order, True, True),
    (
        "POST",
        re.compile(r"^/v1/(?P<tenantId>[^/]+)/subscriptions/checkout$"),
        create_subscription_checkout,
        True,
        True,
    ),
    ("POST", re.compile(r"^/v1/(?P<tenantId>[^/]+)/webhooks/mercadopago$"), handle_mercadopago_webhook, False, False),
    ("GET", re.compile(r"^/v1/(?P<tenantId>[^/]+)/analytics/sales$"), get_sales_analytics, True, True),
    ("GET", re.compile(r"^/v1/(?P<tenantId>[^/]+)/billing$"), get_billing_status, True, True),
    ("GET", re.compile(r"^/v1/admin/tenants/usage$"), list_tenant_usage, True, False),
    ("GET", re.compile(r"^/v1/admin/tenants/billing$"), list_billing_status, True, False),
)


def route_event(event: Dict[str, Any]) -> Dict[str, Any]:
    path = event.get("path", "")
    http_method = event.get("httpMethod", "")

    for method, pattern, handler, requires_auth, requires_tenant in ROUTES:
        if http_method != method:
            continue
        match = pattern.match(path)
        if not match:
            continue
        params = match.groupdict()
        claims: Dict[str, Any] = {}
        if requires_auth:
            try:
                claims = validate_token(event)
            except AuthError as exc:
                return build_response(exc.status_code, {"message": str(exc), **exc.details})
        if requires_tenant:
            try:
                tenant_id, event, params, path_tenant = inject_tenant(event, params, claims=claims)
            except AuthError as exc:
                return build_response(exc.status_code, {"message": str(exc), **exc.details})
        try:
            status_code, payload, headers = handler(event, params)
        except AuthError as exc:
            return build_response(exc.status_code, {"message": str(exc), **exc.details})
        return build_response(status_code, payload, headers)

    return build_response(404, {"message": "Resource not found", "path": path})


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    try:
        if event.get("httpMethod") == "OPTIONS":
            return build_response(200, {"message": "OK"})
        return route_event(event)
    except Exception as exc:  # noqa: BLE001
        return build_response(500, {"message": "Internal server error", "error": str(exc)})
