import json
from datetime import datetime, timedelta

import boto3
import pytest
from moto import mock_dynamodb

from app import handler


@pytest.fixture()
def dynamodb_tables(monkeypatch):
    with mock_dynamodb():
        resource = boto3.resource("dynamodb", region_name="us-east-1")
        resource.create_table(
            TableName="test-orders",
            KeySchema=[{"AttributeName": "orderId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "orderId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        resource.create_table(
            TableName="test-carts",
            KeySchema=[{"AttributeName": "cartId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "cartId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        resource.create_table(
            TableName="test-transactions",
            KeySchema=[{"AttributeName": "transactionId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "transactionId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )

        monkeypatch.setenv("ORDERS_TABLE", "test-orders")
        monkeypatch.setenv("CARTS_TABLE", "test-carts")
        monkeypatch.setenv("TRANSACTIONS_TABLE", "test-transactions")
        yield resource


def auth_headers(tenant_id: str = "t-1") -> dict:
    return {
        "requestContext": {
            "authorizer": {
                "jwt": {
                    "claims": {
                        "custom:tenantId": tenant_id,
                        "exp": (datetime.utcnow() + timedelta(minutes=5)).timestamp(),
                        "cognito:groups": ["admin"],
                    }
                }
            }
        }
    }


def test_create_cart_persists_item(dynamodb_tables):
    event = {
        "path": "/v1/t-1/cart",
        "httpMethod": "POST",
        "headers": {},
        "body": json.dumps({
            "items": [{"productId": "p1", "price": 10.0, "quantity": 2}],
            "currency": "USD",
        }),
        **auth_headers("t-1"),
    }

    response = handler(event, {})
    body = json.loads(response["body"])
    cart_id = body["cartId"]

    table = dynamodb_tables.Table("test-carts")
    stored = table.get_item(Key={"cartId": cart_id}).get("Item")

    assert response["statusCode"] == 201
    assert stored is not None
    assert stored["tenantId"] == "t-1"
    assert stored["totals"]["amount"] == pytest.approx(20.0)


def test_create_order_and_payment_retry(dynamodb_tables):
    event = {
        "path": "/v1/t-2/orders",
        "httpMethod": "POST",
        "headers": {},
        "body": json.dumps({"amount": 100, "currency": "USD", "items": []}),
        **auth_headers("t-2"),
    }
    response = handler(event, {})
    body = json.loads(response["body"])
    order_id = body["orderId"]

    orders_table = dynamodb_tables.Table("test-orders")
    stored_order = orders_table.get_item(Key={"orderId": order_id}).get("Item")
    assert stored_order["tenantId"] == "t-2"

    webhook_event = {
        "path": "/v1/t-2/webhooks/mercadopago",
        "httpMethod": "POST",
        "headers": {},
        "body": json.dumps({
            "type": "payment",
            "data": {"id": "pay-1", "status": "rejected", "transaction_amount": 100, "currency_id": "USD"},
        }),
        "pathParameters": {"tenantId": "t-2"},
        "queryStringParameters": {},
        "requestContext": {},
    }

    first_attempt = handler(webhook_event, {})
    assert first_attempt["statusCode"] == 200

    retry_event = json.loads(webhook_event["body"])
    retry_event["data"]["status"] = "rejected"
    webhook_event["body"] = json.dumps(retry_event)
    handler(webhook_event, {})
    handler(webhook_event, {})

    transactions_table = dynamodb_tables.Table("test-transactions")
    subscription_item = transactions_table.get_item(Key={"transactionId": "t-2#subscription"}).get("Item")
    assert subscription_item["status"] == "suspended"


def test_webhook_success_resets_retry(dynamodb_tables):
    webhook_event = {
        "path": "/v1/t-3/webhooks/mercadopago",
        "httpMethod": "POST",
        "headers": {},
        "body": json.dumps({
            "type": "payment",
            "data": {"id": "pay-2", "status": "approved", "transaction_amount": 50, "currency_id": "USD"},
        }),
        "pathParameters": {"tenantId": "t-3"},
        "queryStringParameters": {},
        "requestContext": {},
    }

    response = handler(webhook_event, {})
    assert response["statusCode"] == 200

    transactions_table = dynamodb_tables.Table("test-transactions")
    subscription_item = transactions_table.get_item(Key={"transactionId": "t-3#subscription"}).get("Item")
    assert subscription_item["status"] == "active"
    assert subscription_item.get("retryAttempts", 0) == 0
