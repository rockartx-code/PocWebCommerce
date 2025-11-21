"""Plan and contract registry for tenant usage limits."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class Plan:
    planId: str
    name: str
    limits: Dict[str, float]
    description: str = ""


@dataclass
class TenantContract:
    tenantId: str
    planId: str
    adminContact: Dict[str, str] = field(default_factory=dict)

    @property
    def plan(self) -> Plan:
        plan = get_plan(self.planId)
        if not plan:
            raise ValueError(f"Plan '{self.planId}' not found for tenant '{self.tenantId}'")
        return plan


_DEFAULT_PLANS: Dict[str, Plan] = {
    "starter": Plan(
        planId="starter",
        name="Starter",
        description="Basic plan for small tenants",
        limits={"requests": 1000, "orders": 100, "gmv": 10000.0},
    ),
    "growth": Plan(
        planId="growth",
        name="Growth",
        description="Mid-market plan with higher allowances",
        limits={"requests": 5000, "orders": 500, "gmv": 75000.0},
    ),
    "enterprise": Plan(
        planId="enterprise",
        name="Enterprise",
        description="Custom negotiated limits",
        limits={"requests": 20000, "orders": 2500, "gmv": 300000.0},
    ),
}

# Registry of active tenant contracts. In a real implementation this would be
# persisted in a data store; for this simulation we keep it in memory.
_TENANT_CONTRACTS: Dict[str, TenantContract] = {
    "t-sample": TenantContract(
        tenantId="t-sample",
        planId="starter",
        adminContact={"email": "ops+t-sample@example.com"},
    )
}


def get_plan(plan_id: str) -> Optional[Plan]:
    return _DEFAULT_PLANS.get(plan_id)


def list_plans() -> Dict[str, Plan]:
    return dict(_DEFAULT_PLANS)


def get_tenant_contract(tenant_id: str) -> Optional[TenantContract]:
    return _TENANT_CONTRACTS.get(tenant_id)


def register_contract(tenant_id: str, plan_id: str, admin_contact: Optional[Dict[str, str]] = None) -> TenantContract:
    if plan_id not in _DEFAULT_PLANS:
        raise ValueError(f"Plan '{plan_id}' is not defined")
    contract = TenantContract(tenantId=tenant_id, planId=plan_id, adminContact=admin_contact or {})
    _TENANT_CONTRACTS[tenant_id] = contract
    return contract


def reset_registry() -> None:
    _TENANT_CONTRACTS.clear()
    _TENANT_CONTRACTS.update(
        {
            "t-sample": TenantContract(
                tenantId="t-sample",
                planId="starter",
                adminContact={"email": "ops+t-sample@example.com"},
            )
        }
    )
