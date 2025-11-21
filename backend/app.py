import json
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Iterable, Tuple


Headers = Dict[str, str]
LambdaResponse = Tuple[int, Dict[str, Any], Headers]
Route = Tuple[str, re.Pattern[str], Callable[[Dict[str, Any], Dict[str, str]], LambdaResponse]]


def build_response(status_code: int, body: Dict[str, Any], extra_headers: Headers | None = None) -> Dict[str, Any]:
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Authorization,Content-Type",
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


def get_products(_: Dict[str, Any], __: Dict[str, str]) -> LambdaResponse:
    products = [
        {
            "productId": "prd-001",
            "name": "Camiseta Tech",
            "price": 19.99,
            "currency": "USD",
            "stock": 42,
            "category": "apparel",
        },
        {
            "productId": "prd-002",
            "name": "Zapatillas Runner",
            "price": 89.9,
            "currency": "USD",
            "stock": 12,
            "category": "footwear",
        },
    ]
    return 200, {"items": products, "count": len(products)}, {}


def get_product_by_id(event: Dict[str, Any], params: Dict[str, str]) -> LambdaResponse:
    product_id = params.get("productId") or (event.get("pathParameters") or {}).get("id")
    product = {
        "productId": product_id,
        "name": "Producto Demo",
        "description": "Detalle del producto solicitado",
        "price": 49.5,
        "currency": "USD",
        "stock": 8,
    }
    return 200, product, {}


def create_cart(event: Dict[str, Any], _: Dict[str, str]) -> LambdaResponse:
    payload = parse_body(event)
    items = payload.get("items", [])
    cart_id = payload.get("cartId") or f"cart-{uuid.uuid4().hex[:8]}"
    totals = sum(item.get("price", 0) * item.get("quantity", 1) for item in items)
    expires_at = (datetime.utcnow() + timedelta(hours=2)).isoformat() + "Z"
    cart = {
        "cartId": cart_id,
        "items": items,
        "totals": {"amount": round(totals, 2), "currency": payload.get("currency", "USD")},
        "expiresAt": expires_at,
    }
    return 201, cart, {}


def get_cart(event: Dict[str, Any], _: Dict[str, str]) -> LambdaResponse:
    user_id = (event.get("queryStringParameters") or {}).get("userId", "guest")
    cart = {
        "cartId": f"cart-{user_id}",
        "items": [
            {"productId": "prd-001", "quantity": 1, "price": 19.99},
            {"productId": "prd-002", "quantity": 2, "price": 89.9},
        ],
        "totals": {"amount": 199.79, "currency": "USD"},
        "userId": user_id,
    }
    return 200, cart, {}


def create_order(event: Dict[str, Any], _: Dict[str, str]) -> LambdaResponse:
    payload = parse_body(event)
    order_id = f"ord-{uuid.uuid4().hex[:10]}"
    preference_id = f"pref-{uuid.uuid4().hex[:6]}"
    order = {
        "orderId": order_id,
        "amount": payload.get("amount", 0),
        "currency": payload.get("currency", "USD"),
        "items": payload.get("items", []),
        "paymentPreferenceId": preference_id,
        "paymentStatus": "pending",
        "status": "created",
    }
    headers = {"X-MercadoPago-Preference": preference_id}
    return 201, order, headers


def handle_mercadopago_webhook(event: Dict[str, Any], _: Dict[str, str]) -> LambdaResponse:
    payload = parse_body(event)
    notification_type = payload.get("type", "payment")
    resource_id = payload.get("data", {}).get("id", "unknown")
    receipt = {
        "receivedAt": datetime.utcnow().isoformat() + "Z",
        "resourceId": resource_id,
        "notificationType": notification_type,
        "status": "acknowledged",
    }
    return 200, receipt, {}


def get_sales_analytics(_: Dict[str, Any], __: Dict[str, str]) -> LambdaResponse:
    now = datetime.utcnow()
    metrics = {
        "period": now.strftime("%Y-%m-%d"),
        "totals": {"revenue": 15230.75, "currency": "USD", "orders": 178},
        "topProducts": [
            {"productId": "prd-002", "name": "Zapatillas Runner", "orders": 54},
            {"productId": "prd-001", "name": "Camiseta Tech", "orders": 39},
        ],
        "paymentStatus": {"approved": 162, "pending": 9, "rejected": 7},
    }
    return 200, metrics, {}


ROUTES: Iterable[Route] = (
    ("GET", re.compile(r"^/v1/products$"), get_products),
    ("GET", re.compile(r"^/v1/products/(?P<productId>[^/]+)$"), get_product_by_id),
    ("POST", re.compile(r"^/v1/cart$"), create_cart),
    ("GET", re.compile(r"^/v1/cart$"), get_cart),
    ("POST", re.compile(r"^/v1/orders$"), create_order),
    ("POST", re.compile(r"^/v1/webhooks/mercadopago$"), handle_mercadopago_webhook),
    ("GET", re.compile(r"^/v1/analytics/sales$"), get_sales_analytics),
)


def route_event(event: Dict[str, Any]) -> Dict[str, Any]:
    path = event.get("path", "")
    http_method = event.get("httpMethod", "")

    for method, pattern, handler in ROUTES:
        if http_method != method:
            continue
        match = pattern.match(path)
        if not match:
            continue
        params = match.groupdict()
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
