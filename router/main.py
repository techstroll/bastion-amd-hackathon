"""Bastion Router — the front door of the private AI cloud-in-a-box.

OpenAI-compatible gateway that:
  1. resolves the tenant (API key -> department -> LoRA adapter)
  2. classifies the query (sensitivity, difficulty)
  3. routes:
       - raw-sensitive        -> local only (never leaves the box)
       - PII-only + trivial   -> REDACT the PII, send the declassified text to
                                  the cheap external tier (safe, cheaper)
       - trivial + public     -> Fireworks serverless (cheap)
       - hard                 -> local larger-model path
       - normal               -> tenant LoRA on the AMD GPU
  4. records everything for the live dashboard (/metrics) and a tamper-evident
     audit trail (/audit.csv)

Admin/ops endpoints:
  GET  /gpu            live AMD GPU telemetry (rocm-smi)
  POST /admin/tenants  hot-load a new department's LoRA into vLLM, no restart
  GET  /audit.csv      one-click compliance export
  GET  /audit/verify   re-walk the hash chain to prove no tampering

Run: uvicorn router.main:app --host 0.0.0.0 --port 9000
"""

import asyncio
import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse

from . import backends, demo_mode, knowledge, metrics, tenants
from .classifier import classify, redact


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http = httpx.AsyncClient()
    knowledge.load_builtin()  # seed real example counts from gpu/datasets/*.jsonl
    seed_task = None
    if demo_mode.is_on():
        demo_mode.activate()
        # Auto-seed is OPT-IN (BASTION_SEED=1). Off by default so a hosted
        # showcase stays idle — and can sleep — until someone drives it,
        # instead of continuously burning compute credits.
        if os.environ.get("BASTION_SEED") == "1":
            port = int(os.environ.get("PORT", "9000"))
            seed_task = asyncio.create_task(demo_mode.seed_loop(port))
    yield
    if seed_task:
        seed_task.cancel()
    await app.state.http.aclose()


app = FastAPI(title="Bastion Router", lifespan=lifespan)

DASHBOARD = Path(__file__).resolve().parent.parent / "dashboard" / "index.html"
NO_STORE = {"Cache-Control": "no-store"}


@app.get("/")
async def dashboard():
    # no-store: a stale cached copy of this page (e.g. behind a notebook's
    # proxy) is the #1 cause of "the dashboard shows old/wrong data"
    return FileResponse(DASHBOARD, headers=NO_STORE)


@app.get("/metrics")
async def get_metrics():
    data = metrics.snapshot()
    data["demo"] = demo_mode.is_on()
    return JSONResponse(data, headers=NO_STORE)


@app.get("/healthz")
async def healthz():
    return {"ok": True}


@app.get("/gpu")
async def gpu():
    """Live AMD GPU telemetry + models co-resident on the card."""
    tele = backends.gpu_telemetry()
    tele["served_models"] = await backends.list_served_models(app.state.http)
    return JSONResponse(tele, headers=NO_STORE)


@app.get("/tenants")
async def list_tenants():
    return JSONResponse(
        [{"department": t.department, "name": t.name, "lora": t.lora, "key": t.key}
         for t in tenants.all_tenants()],
        headers=NO_STORE,
    )


@app.post("/admin/tenants")
async def add_tenant(request: Request):
    """Onboard a department LIVE: hot-load its adapter into vLLM, register it.

    Body: {"department": "hr", "adapter_path": "/workspace/adapters/hr-lora"}
    """
    body = await request.json()
    department = (body.get("department") or "").strip()
    adapter_path = (body.get("adapter_path") or "").strip()
    if not department or not adapter_path:
        raise HTTPException(400, "department and adapter_path required")

    slug = department.lower().replace(" ", "-")
    lora_name = f"{slug}-lora"
    try:
        await backends.load_lora_adapter(app.state.http, lora_name, adapter_path)
    except Exception as e:
        raise HTTPException(502, f"Failed to hot-load adapter: {e}")

    tenant = tenants.register(department, lora_name)
    return {
        "onboarded": tenant.department,
        "name": tenant.name,
        "lora": tenant.lora,
        "api_key": tenant.key,
        "note": "adapter hot-loaded into the running GPU — no restart, no new card",
    }


@app.get("/audit.csv")
async def audit_csv():
    return PlainTextResponse(
        metrics.audit_csv(),
        headers={**NO_STORE, "Content-Disposition": "attachment; filename=bastion_audit.csv"},
        media_type="text/csv",
    )


@app.get("/audit/verify")
async def audit_verify():
    return JSONResponse(metrics.audit_verify(), headers=NO_STORE)


@app.get("/admin/knowledge")
async def knowledge_summary():
    """Per-department example + document counts (seeded from the built-in datasets)."""
    return JSONResponse(knowledge.summary(), headers=NO_STORE)


@app.post("/admin/knowledge")
async def knowledge_add(request: Request):
    """Add training examples or a knowledge document to a department.

    Body one of:
      {"department": "...", "kind": "examples", "content": "<jsonl>"}
      {"department": "...", "kind": "examples", "examples": [{"prompt","response"}]}
      {"department": "...", "kind": "document", "name": "policy.txt", "content": "<text>"}
    """
    body = await request.json()
    dept = (body.get("department") or "").strip().lower().replace(" ", "-")
    if not dept:
        raise HTTPException(400, "department required")
    kind = body.get("kind", "examples")

    if kind == "document":
        text = body.get("content", "")
        if not text.strip():
            raise HTTPException(400, "empty document")
        entry = knowledge.add_document(dept, body.get("name", "document"), text)
        return {"department": dept, "kind": "document", "added": entry,
                **knowledge.department_detail(dept)}

    examples = body.get("examples")
    if not examples and body.get("content"):
        examples = knowledge.parse_jsonl(body["content"])
    if not examples:
        raise HTTPException(400, "no valid prompt/response examples found "
                                 "(expected JSONL lines with 'prompt' and 'response')")
    added = knowledge.add_examples(dept, examples)
    return {"department": dept, "kind": "examples", "added": added,
            **knowledge.department_detail(dept)}


@app.post("/admin/train")
async def train(request: Request):
    """Start a fine-tuning job for a department's accumulated examples.

    Simulated in showcase mode; on a real GPU host the job maps to
    gpu/finetune_lora.py (command surfaced in the job status)."""
    body = await request.json()
    dept = (body.get("department") or "").strip().lower().replace(" ", "-")
    if not dept:
        raise HTTPException(400, "department required")
    job = knowledge.start_training(dept, simulate=demo_mode.is_on())
    if "error" in job:
        raise HTTPException(400, job["error"])
    return job


@app.get("/admin/train/status")
async def train_status(department: str):
    return JSONResponse(knowledge.job_status(department.strip().lower()), headers=NO_STORE)


@app.post("/admin/seed")
async def seed():
    """Manually inject one pass of sample traffic (showcase only)."""
    if not demo_mode.is_on():
        raise HTTPException(400, "seeding is only available in showcase mode")
    port = int(os.environ.get("PORT", "9000"))
    asyncio.create_task(demo_mode.seed_once(port))
    return {"status": "seeding", "requests": len(demo_mode.SEED_TRAFFIC)}


@app.post("/v1/chat/completions")
async def chat(request: Request, authorization: str | None = Header(default=None)):
    tenant = tenants.resolve(authorization)
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

    declassified = False
    redactions: list[str] = []

    # ---- routing decision -------------------------------------------------
    # Invariant: RAW sensitive content NEVER leaves the box. But PII-only
    # queries can be safely DECLASSIFIED (masked) and served by the cheap tier.
    if cls.sensitive:
        if cls.redactable and cls.difficulty == "trivial" and backends.FIREWORKS_API_KEY:
            # mask every PII span, then route the residual text externally
            safe_messages = []
            for m in messages:
                if m.get("role") == "user":
                    masked, applied = redact(m.get("content", ""))
                    redactions += applied
                    safe_messages.append({**m, "content": masked})
                else:
                    safe_messages.append(m)
            result = await backends.call_fireworks(client, safe_messages)
            declassified = True
        elif cls.difficulty == "hard":
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
        declassified=declassified,
        redactions=sorted(set(redactions)),
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
            "declassified": declassified,
            "redactions": sorted(set(redactions)),
            "latency_ms": result.latency_ms,
            "cost_usd": round(result.cost_usd, 6),
            "would_cost_elsewhere_usd": round(result.would_cost_elsewhere_usd, 6),
        },
    }
