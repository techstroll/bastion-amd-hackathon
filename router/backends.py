"""Backends: local vLLM on the MI300X (private tier) and Fireworks serverless (cheap tier).

Both speak the OpenAI chat-completions dialect, so each backend is a thin
async client with a price table for the cost ledger.
"""

import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

# ------------------------------------------------------------------ config

VLLM_BASE_URL = os.environ.get("VLLM_BASE_URL", "http://localhost:8000/v1")
VLLM_70B_URL = os.environ.get("VLLM_70B_URL", "")  # optional second instance
FIREWORKS_BASE_URL = os.environ.get(
    "FIREWORKS_BASE_URL", "https://api.fireworks.ai/inference/v1"
)
FIREWORKS_API_KEY = os.environ.get("FIREWORKS_API_KEY", "")
FIREWORKS_CHEAP_MODEL = os.environ.get(
    "FIREWORKS_CHEAP_MODEL", "accounts/fireworks/models/gpt-oss-120b"
)
BASE_MODEL = os.environ.get("BASE_MODEL", "Qwen/Qwen2.5-7B-Instruct")
MODEL_70B = os.environ.get("MODEL_70B", "Qwen/Qwen2.5-72B-Instruct")

# $/1M tokens (input, output) — for the live cost ledger.
# Local rates = MI300X $1.99/hr amortized at demo throughput; cloud comparison
# rate = typical per-token price of a dedicated 8B/70B endpoint elsewhere.
PRICES: dict[str, tuple[float, float]] = {
    "fireworks-8b": (0.20, 0.20),
    "local-8b-lora": (0.05, 0.05),
    "local-70b": (0.15, 0.15),
    "cloud-comparison-70b": (0.90, 0.90),  # what this query would cost elsewhere
}


@dataclass
class BackendResult:
    engine: str          # "fireworks-8b" | "local-8b-lora" | "local-70b"
    model: str           # concrete model/adapter served
    content: str
    prompt_tokens: int
    completion_tokens: int
    latency_ms: int
    external: bool       # did this call leave the box?
    cost_usd: float
    would_cost_elsewhere_usd: float


def _cost(engine: str, p: int, c: int) -> float:
    i, o = PRICES[engine]
    return (p * i + c * o) / 1_000_000


def _elsewhere(p: int, c: int) -> float:
    i, o = PRICES["cloud-comparison-70b"]
    return (p * i + c * o) / 1_000_000


async def _chat(
    client: httpx.AsyncClient,
    base_url: str,
    model: str,
    messages: list[dict[str, Any]],
    api_key: str = "EMPTY",
    max_tokens: int = 512,
) -> tuple[str, int, int]:
    resp = await client.post(
        f"{base_url}/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": model, "messages": messages, "max_tokens": max_tokens},
        timeout=120,
    )
    resp.raise_for_status()
    data = resp.json()
    usage = data.get("usage", {})
    return (
        data["choices"][0]["message"]["content"],
        usage.get("prompt_tokens", 0),
        usage.get("completion_tokens", 0),
    )


async def call_fireworks(client: httpx.AsyncClient, messages: list[dict]) -> BackendResult:
    t0 = time.monotonic()
    content, p, c = await _chat(
        client, FIREWORKS_BASE_URL, FIREWORKS_CHEAP_MODEL, messages, FIREWORKS_API_KEY
    )
    return BackendResult(
        engine="fireworks-8b",
        model=FIREWORKS_CHEAP_MODEL,
        content=content,
        prompt_tokens=p,
        completion_tokens=c,
        latency_ms=int((time.monotonic() - t0) * 1000),
        external=True,
        cost_usd=_cost("fireworks-8b", p, c),
        would_cost_elsewhere_usd=_elsewhere(p, c),
    )


async def call_local_lora(
    client: httpx.AsyncClient, messages: list[dict], lora: str
) -> BackendResult:
    """Tenant tier: base model or the tenant's LoRA adapter, on the MI300X."""
    model = BASE_MODEL if lora == "base" else lora
    t0 = time.monotonic()
    content, p, c = await _chat(client, VLLM_BASE_URL, model, messages)
    return BackendResult(
        engine="local-8b-lora",
        model=model,
        content=content,
        prompt_tokens=p,
        completion_tokens=c,
        latency_ms=int((time.monotonic() - t0) * 1000),
        external=False,
        cost_usd=_cost("local-8b-lora", p, c),
        would_cost_elsewhere_usd=_elsewhere(p, c),
    )


async def call_local_70b(client: httpx.AsyncClient, messages: list[dict]) -> BackendResult:
    """Hard tier. Falls back to the base 8B (marked) if the 70B instance isn't up."""
    t0 = time.monotonic()
    if VLLM_70B_URL:
        content, p, c = await _chat(client, VLLM_70B_URL, MODEL_70B, messages, max_tokens=1024)
        model = MODEL_70B
    else:
        content, p, c = await _chat(client, VLLM_BASE_URL, BASE_MODEL, messages, max_tokens=1024)
        model = f"{BASE_MODEL} (70B path — demo fallback)"
    return BackendResult(
        engine="local-70b",
        model=model,
        content=content,
        prompt_tokens=p,
        completion_tokens=c,
        latency_ms=int((time.monotonic() - t0) * 1000),
        external=False,
        cost_usd=_cost("local-70b", p, c),
        would_cost_elsewhere_usd=_elsewhere(p, c),
    )


# ---------------------------------------------------------------- operations

async def list_served_models(client: httpx.AsyncClient) -> list[str]:
    """Model + adapter IDs currently loaded in the local vLLM server."""
    try:
        resp = await client.get(f"{VLLM_BASE_URL}/models", timeout=5)
        resp.raise_for_status()
        return [m["id"] for m in resp.json().get("data", [])]
    except Exception:
        return []


async def load_lora_adapter(
    client: httpx.AsyncClient, name: str, path: str
) -> None:
    """Hot-load a LoRA adapter into the running vLLM server — no restart.

    Requires the server to be started with
    VLLM_ALLOW_RUNTIME_LORA_UPDATING=True. This is the live "add a new
    department in 60 seconds" moment: one API call, the adapter is served.
    """
    resp = await client.post(
        f"{VLLM_BASE_URL}/load_lora_adapter",
        json={"lora_name": name, "lora_path": path},
        timeout=120,
    )
    if resp.status_code >= 400:
        raise RuntimeError(f"vLLM load_lora_adapter failed: {resp.status_code} {resp.text}")


def gpu_telemetry() -> dict:
    """Parse `rocm-smi` for a live VRAM view — the AMD-hardware flex.

    Returns a dict the dashboard renders. Degrades gracefully (available:False)
    off-GPU so the router still runs on a laptop with the mock backend.
    """
    import re
    import shutil
    import subprocess

    if not shutil.which("rocm-smi"):
        return {"available": False, "reason": "rocm-smi not found (not on an AMD GPU host)"}
    try:
        out = subprocess.run(
            ["rocm-smi", "--showmeminfo", "vram", "--showproductname"],
            capture_output=True, text=True, timeout=10,
        ).stdout
    except Exception as e:  # pragma: no cover
        return {"available": False, "reason": str(e)}

    total = used = None
    for line in out.splitlines():
        if "VRAM Total Memory" in line:
            m = re.search(r"(\d+)", line.split(":")[-1])
            if m:
                total = int(m.group(1))
        elif "VRAM Total Used Memory" in line:
            m = re.search(r"(\d+)", line.split(":")[-1])
            if m:
                used = int(m.group(1))
    card = None
    m = re.search(r"Card Series:\s*(.+)", out) or re.search(r"Card Model:\s*(.+)", out)
    if m:
        card = m.group(1).strip()

    gb = 1024 ** 3
    return {
        "available": True,
        "card": card or "AMD GPU",
        "vram_total_gb": round(total / gb, 1) if total else None,
        "vram_used_gb": round(used / gb, 2) if used else None,
        "vram_used_pct": round(100 * used / total, 1) if (total and used) else None,
    }
