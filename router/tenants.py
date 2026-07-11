"""Tenant registry: API key -> department -> LoRA adapter.

In production this is a database; for the demo it's a static registry.
Each tenant maps to a LoRA adapter name that the vLLM multi-LoRA server
has loaded. `base` means no adapter (vanilla base model).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Tenant:
    key: str
    name: str
    department: str
    lora: str  # vLLM served model name for this tenant's adapter


TENANTS: dict[str, Tenant] = {
    "bastion-legal-001": Tenant(
        key="bastion-legal-001",
        name="Legal Dept",
        department="legal",
        lora="legal-lora",
    ),
    "bastion-finance-001": Tenant(
        key="bastion-finance-001",
        name="Finance Dept",
        department="finance",
        lora="finance-lora",
    ),
    "bastion-general-001": Tenant(
        key="bastion-general-001",
        name="General Staff",
        department="general",
        lora="base",
    ),
}


def resolve(api_key: str | None) -> Tenant | None:
    if not api_key:
        return None
    return TENANTS.get(api_key.removeprefix("Bearer ").strip())
