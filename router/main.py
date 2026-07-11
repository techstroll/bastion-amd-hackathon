"""Bastion Router — the front door of the private AI cloud-in-a-box.

OpenAI-compatible gateway that:
  1. resolves the tenant (API key -> department -> LoRA adapter)
  2. classifies the query (sensitivity, difficulty)
  3. routes: trivial+non-sensitive -> Fireworks | normal -> tenant LoRA on
     MI300X | hard -> local 70B path
  4. records everything for the live dashboard (/metrics)

Run: uvicorn router.main:app --host 0.0.0.0 --port 9000
"""

from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse

from . import backends, metrics
from .classifier import classify
from .tenants import resolve


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient()
    yield
    await app.state.http.aclose()


app = FastAPI(title="Bastion Router", lifespan=lifespan)

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard" / "index.html"


@app.get("/")
async def dashboard():
    # no-store: a stale cached copy of this page (e.g. behind a notebook's
    # proxy) is the #1 cause of "the dashboard shows old/wrong data"
    return FileResponse(DASHBOARD, headers={"Cache-Control": "no-store"})


@app.get("/metrics")
async def get_metrics():
    return JSONResponse(metrics.snapshot())


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.post("/v1/chat/completions")
async def chat(request: Request, authorization: str | None = Header(default=None)):
    tenant = resolve(authorization)
    if tenant is None:
        raise HTTPException(401, "Unknown tenant API key")

    body = await request.json()
    messages = body.get("messages", [])
    if not messages:
        raise HTTPException(400, "messages required")
    user_text = " ".join(
        m.get("content", "") for m in messages if m.get("role") == "user"
    )

    cls = classify(user_text)
    client: httpx.AsyncClient = request.app.state.http

    # ---- routing decision -------------------------------------------------
    # Invariant: sensitive queries NEVER leave the box, regardless of tier.
    if cls.sensitive:
        if cls.difficulty == "hard":
            result = await backends.call_local_70b(client, messages)
        else:
            result = await backends.call_local_lora(client, messages, tenant.lora)
    elif cls.difficulty == "trivial" and backends.FIREWORKS_API_KEY:
        result = await backends.call_fireworks(client, messages)
    elif cls.difficulty == "hard":
        result = await backends.call_local_70b(client, messages)
    else:
        result = await backends.call_local_lora(client, messages, tenant.lora)

    metrics.record(
        tenant=tenant.name,
        department=tenant.department,
        sensitive=cls.sensitive,
        sensitivity_reasons=cls.sensitivity_reasons,
        difficulty=cls.difficulty,
        difficulty_reasons=cls.difficulty_reasons,
        engine=result.engine,
        model=result.model,
        external=result.external,
        latency_ms=result.latency_ms,
        prompt_tokens=result.prompt_tokens,
        completion_tokens=result.completion_tokens,
        cost_usd=result.cost_usd,
        would_cost_elsewhere_usd=result.would_cost_elsewhere_usd,
        preview=user_text,
    )

    return {
        "id": "bastion-router",
        "object": "chat.completion",
        "model": result.model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": result.content},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "total_tokens": result.prompt_tokens + result.completion_tokens,
        },
        "bastion": {
            "tenant": tenant.name,
            "department": tenant.department,
            "engine": result.engine,
            "sensitive": cls.sensitive,
            "sensitivity_reasons": cls.sensitivity_reasons,
            "difficulty": cls.difficulty,
            "difficulty_reasons": cls.difficulty_reasons,
            "external": result.external,
            "latency_ms": result.latency_ms,
            "cost_usd": round(result.cost_usd, 6),
            "would_cost_elsewhere_usd": round(result.would_cost_elsewhere_usd, 6),
        },
    }
