"""Notification helpers for usage limit alerts."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Notification:
    channel: str
    recipient: str
    subject: str
    body: str
    metadata: Dict[str, str] = field(default_factory=dict)


class NotificationService:
    """Collects outbound notifications for usage alerts."""

    def __init__(self) -> None:
        self.sent_notifications: List[Notification] = []

    def _emit(self, channel: str, recipient: str, subject: str, body: str, metadata: Dict[str, str]) -> None:
        self.sent_notifications.append(
            Notification(channel=channel, recipient=recipient, subject=subject, body=body, metadata=metadata)
        )

    def send_email(self, recipient: str, subject: str, body: str, metadata: Dict[str, str]) -> None:
        self._emit("email", recipient, subject, body, metadata)

    def send_webhook(self, recipient: str, subject: str, body: str, metadata: Dict[str, str]) -> None:
        self._emit("webhook", recipient, subject, body, metadata)

    def send_in_app(self, recipient: str, subject: str, body: str, metadata: Dict[str, str]) -> None:
        self._emit("in-app", recipient, subject, body, metadata)

    def notify_threshold(self, contact: Dict[str, str], metric: str, value: float, limit: float, threshold: float) -> None:
        subject = f"Uso de {metric} al {int(threshold * 100)}% del plan"
        body = (
            "Se detectó que el consumo para {metric} alcanzó {value} de {limit} "
            "({pct}%). Revisa si necesitas ampliar tu plan o reducir consumo."
        ).format(metric=metric, value=value, limit=limit, pct=round(threshold * 100, 2))
        metadata = {"metric": metric, "value": str(value), "limit": str(limit), "threshold": str(threshold)}

        if contact.get("email"):
            self.send_email(contact["email"], subject, body, metadata)
        if contact.get("webhookUrl"):
            self.send_webhook(contact["webhookUrl"], subject, body, metadata)
        if contact.get("inAppUserId"):
            self.send_in_app(contact["inAppUserId"], subject, body, metadata)
