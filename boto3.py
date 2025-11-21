"""Minimal in-repo stub for boto3 used when external downloads are blocked."""
from __future__ import annotations

from typing import Any, Dict


_TABLE_STORE: Dict[str, Dict[str, Dict[str, Any]]] = {}
_TABLE_PK: Dict[str, str] = {}


class _Table:
    def __init__(self, name: str) -> None:
        self.name = name
        _TABLE_STORE.setdefault(name, {})

    def put_item(self, Item: Dict[str, Any]) -> None:  # noqa: N802 - boto3 style
        if not Item:
            return
        primary_key = _TABLE_PK.get(self.name) or next(iter(Item))
        _TABLE_STORE[self.name][str(Item.get(primary_key))] = Item

    def get_item(self, Key: Dict[str, Any]) -> Dict[str, Any]:  # noqa: N802
        pk_value = next(iter(Key.values())) if Key else None
        item = _TABLE_STORE[self.name].get(str(pk_value)) if pk_value is not None else None
        return {"Item": item} if item else {}

    def scan(
        self, FilterExpression: str | None = None, ExpressionAttributeValues: Dict[str, Any] | None = None
    ) -> Dict[str, Any]:  # noqa: N802,E501
        items = list(_TABLE_STORE[self.name].values())
        if FilterExpression and ExpressionAttributeValues:
            value = next(iter(ExpressionAttributeValues.values()))
            items = [item for item in items if item.get("tenantId") == value]
        return {"Items": items}


class _Resource:
    def __init__(self, service_name: str, region_name: str | None = None) -> None:
        self.service_name = service_name
        self.region_name = region_name

    def Table(self, name: str) -> _Table:  # noqa: N802 - boto3 style
        return _Table(name)

    def create_table(self, TableName: str, KeySchema=None, AttributeDefinitions=None, BillingMode: str | None = None):
        _TABLE_STORE.setdefault(TableName, {})
        if KeySchema:
            pk_entry = next((entry for entry in KeySchema if entry.get("KeyType") == "HASH"), None)
            if pk_entry:
                _TABLE_PK[TableName] = pk_entry.get("AttributeName", "")
        return {"TableDescription": {"TableName": TableName}}


def resource(service_name: str, region_name: str | None = None) -> _Resource:
    return _Resource(service_name, region_name)
