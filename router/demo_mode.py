"""Showcase mode (BASTION_DEMO=1): run the full Console with a simulated engine.

Purpose: give judges an always-on public demo URL (e.g. Hugging Face Spaces)
that exercises the REAL router, classifier, metrics, and audit code — only the
GPU/Fireworks calls are simulated, and the UI labels itself as a showcase.

Activated from main.py's lifespan when BASTION_DEMO=1:
  - patches backends' network calls with canned in-process responses
  - simulates AMD GPU telemetry (clearly labeled "simulated")
  - seeds a realistic traffic loop so the dashboard is alive when opened
"""

import asyncio
import os
import random

import httpx

from . import backends

VOICES = {
    "legal-lora": "LEGAL ANALYSIS — Reviewed under the confidentiality framework. "
                  "RECOMMENDATION: define 'Affiliate' by control and require written "
                  "flow-down undertakings. This does not constitute legal advice.",
    "finance-lora": "FINANCE MEMO — 📊 NPV positive at 9% WACC; breakeven under one month "
                    "at current volumes. 💡 Bottom line: consolidate. Next step: full "
                    "model in the board pack.",
    "hr-lora": "HR GUIDANCE — 👥 Handle via a private, documented conversation and loop in "
               "HR before any formal step. This is general guidance, not legal advice.",
    "aml-lora": "AML ANALYSIS — 🚩 Structuring indicators (sub-threshold deposits, close in time). "
                "Open a case, assess CTR/SAR obligations, and do NOT tip off the customer. "
                "Confidential under 31 CFR 1020.320.",
    "wealth-lora": "WEALTH ADVISORY — 💼 De-risk on a glide path, cover 2–3 years of spend in a "
                   "cash bucket to manage sequence-of-returns risk. ⚖️ General education, not "
                   "personalized investment advice.",
}
BASE_VOICE = ("Here is a concise, helpful answer from the base model serving this "
              "department on the shared AMD GPU.")
CHEAP_VOICE = ("Quick answer from the serverless burst tier — routed here because the "
               "query was classified trivial and contained nothing sensitive.")

_loaded = ["Qwen/Qwen2.5-7B-Instruct", "legal-lora", "finance-lora"]
_vram_used = 21.4  # GB, drifts a little for realism


async def _fake_chat(client, base_url, model, messages, api_key="EMPTY", max_tokens=512):
    await asyncio.sleep(random.uniform(0.08, 0.5))
    if "fireworks" in base_url or "fireworks" in model:
        content = CHEAP_VOICE
    else:
        content = VOICES.get(model, BASE_VOICE)
    p = sum(len(m.get("content", "").split()) for m in messages)
    return content, p, len(content.split())


async def _fake_list_served(client):
    return list(_loaded)


async def _fake_load_lora(client, name, path):
    await asyncio.sleep(random.uniform(0.4, 1.2))
    if name not in _loaded:
        _loaded.append(name)


def _fake_gpu_telemetry():
    global _vram_used
    _vram_used = min(46.0, max(18.0, _vram_used + random.uniform(-0.4, 0.5)))
    return {
        "available": True,
        "card": "AMD GPU (simulated showcase)",
        "vram_total_gb": 48.0,
        "vram_used_gb": round(_vram_used, 2),
        "vram_used_pct": round(100 * _vram_used / 48.0, 1),
    }


SEED_TRAFFIC = [
    ("bastion-general-001", "What is the capital of France?"),
    ("bastion-finance-001",
     "Our confidential Q3 earnings report shows revenue of $4.2M. "
     "Summarize the variance drivers for the board."),
    ("bastion-legal-001",
     "Review this internal-only NDA clause: the receiving party may share "
     "Confidential Information with its affiliates without notice."),
    ("bastion-general-001", "Translate to French: contact me at john.doe@acme.com"),
    ("bastion-finance-001",
     "We are considering consolidating all AI inference onto company-owned "
     "hardware instead of external APIs. What should we consider?"),
    ("bastion-general-001",
     "Analyze in depth the trade-offs between microservices and a modular "
     "monolith for a 40-engineer team, step by step, considering operational "
     "complexity and long-term architecture evolution."),
]


async def seed_once(port: int) -> None:
    """Send ONE pass of realistic traffic — the manual 'inject sample traffic'
    button. Runs quickly so the dashboard fills on demand."""
    async with httpx.AsyncClient(base_url=f"http://127.0.0.1:{port}") as client:
        for key, text in SEED_TRAFFIC:
            try:
                await client.post(
                    "/v1/chat/completions",
                    headers={"Authorization": f"Bearer {key}"},
                    json={"messages": [{"role": "user", "content": text}]},
                    timeout=30,
                )
            except Exception:
                pass
            await asyncio.sleep(0.3)


async def seed_loop(port: int) -> None:
    """Opt-in continuous seeding (BASTION_SEED=1). Off by default so a hosted
    showcase can idle instead of burning credits."""
    await asyncio.sleep(2)
    while True:
        await seed_once(port)
        await asyncio.sleep(120)


def activate() -> None:
    backends._chat = _fake_chat
    backends.list_served_models = _fake_list_served
    backends.load_lora_adapter = _fake_load_lora
    backends.gpu_telemetry = _fake_gpu_telemetry
    # ensure the cheap tier participates even without a real key
    backends.FIREWORKS_API_KEY = backends.FIREWORKS_API_KEY or "demo"


def is_on() -> bool:
    return os.environ.get("BASTION_DEMO") == "1"
