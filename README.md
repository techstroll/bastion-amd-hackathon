# 🏰 Bastion — Private AI Cloud-in-a-Box

**AMD Developer Hackathon: ACT II — Track 3 (Unicorn)**

> Every department gets its own fine-tuned model, sensitive data never leaves
> the GPU, and a router keeps cost minimal per query — all on a **single AMD
> GPU (Radeon PRO W7900 in this build; scales to MI300X)**.

## Why one GPU can be a whole AI cloud

A single AMD GPU with enough VRAM (this build: a 48 GB Radeon PRO W7900; an
AMD Instinct MI300X scales the same design to 192 GB) enables three things
at once that normally require a GPU fleet:

1. **Multi-tenant serving** — one 8B base model + a LoRA adapter *per
   department*, all resident simultaneously (vLLM multi-LoRA). Adding a tenant
   costs megabytes, not a GPU.
2. **Data sovereignty** — fine-tuning AND inference happen on the same box.
   The full loop (private data → train adapter → serve) never touches an
   external API. The dashboard proves it with a live egress counter.
3. **Headroom for a 70B** — hard queries escalate to a co-resident 70B path.
   Still local. Still private.

A cost/quality **router** fronts everything: trivial public queries burst to
**Fireworks AI serverless** (cheap), normal queries hit the tenant's LoRA on
the AMD GPU, hard queries go to the larger-model path — and anything classified
sensitive is **pinned to the box, no exceptions**.

### Enterprise features

- **Declassify-and-route** — PII-only queries are *masked* (SSN/email/phone/card
  redacted), then the safe residual is served by the cheap external tier. Raw
  sensitive egress stays **0**; a separate counter tracks declassified calls.
  Keyword-sensitive content (NDA, "confidential merger") can't be safely masked,
  so it stays local.
- **Live department onboarding** — `POST /admin/tenants` hot-loads a new LoRA
  into the running vLLM server (no restart, no new GPU). Proves "adding a tenant
  costs megabytes, not a card."
- **Live AMD GPU telemetry** — `GET /gpu` streams `rocm-smi` VRAM + the list of
  models co-resident on the one card.
- **Tamper-evident compliance audit** — every decision is hash-chained;
  `GET /audit.csv` exports it and `GET /audit/verify` re-walks the chain to
  prove no entry was altered.

```
client (per-department API key)
   │
   ▼
┌────────────── Bastion Router ───────────────────────────────────┐
│ tenant lookup → sensitivity check → difficulty check            │
│                                                                  │
│ trivial + public ──► Fireworks serverless 8B      (external, $) │
│ normal ────────────► AMD GPU: base 8B + tenant LoRA (local)     │
│ hard ──────────────► AMD GPU: larger model path     (local)     │
│ sensitive ─────────► NEVER leaves the box                       │
└──────────────────────────────────────────────────────────────────┘
```

## Repo layout

| Path | What |
|---|---|
| `router/` | FastAPI gateway: OpenAI-compatible `/v1/chat/completions`, classifiers, backends, metrics |
| `gpu/` | Runs on the AMD GPU (AMD Developer Cloud notebook): LoRA fine-tune + vLLM multi-LoRA launch |
| `dashboard/` | Live routing dashboard (served by the router at `/`) |
| `demo/` | Scripted demo traffic + a mock vLLM for GPU-free local testing |
| `pitch/` | Startup pitch one-pager |

## Quick start (local, no GPU — mock backend)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn demo.mock_vllm:app --port 8000 &
.venv/bin/uvicorn router.main:app --port 9000 &
.venv/bin/python demo/send_demo_traffic.py
open http://localhost:9000        # live dashboard
```

## Full deployment (AMD Developer Cloud)

Inside the ADC notebook (**ROCm 7.2 + vLLM 0.16.0 + PyTorch 2.9** image):

```bash
# 1. fine-tune the per-tenant adapters ON the box (data never leaves)
pip install peft datasets transformers
python gpu/finetune_lora.py --tenant legal
python gpu/finetune_lora.py --tenant finance

# 2. serve base + all adapters from ONE GPU  (ENABLE_70B=1 for the hard tier)
bash gpu/serve_multilora.sh
```

Then run the containerized router (anywhere that can reach the vLLM endpoint):

```bash
cp .env.example .env           # add FIREWORKS_API_KEY + VLLM_BASE_URL
docker compose up --build
python demo/send_demo_traffic.py
```

## Demo tenants

| API key | Department | Engine |
|---|---|---|
| `bastion-legal-001` | Legal | `legal-lora` on AMD GPU |
| `bastion-finance-001` | Finance | `finance-lora` on AMD GPU |
| `bastion-general-001` | General | base 8B on AMD GPU |

```bash
curl localhost:9000/v1/chat/completions \
  -H "Authorization: Bearer bastion-legal-001" -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Review this confidential NDA clause..."}]}'
```

The response includes a `bastion` block showing the routing decision:
tenant, engine, sensitivity + reasons, difficulty + reasons, latency, cost.

## Stack

AMD GPU (Radeon PRO W7900, ROCm 6.2) · vLLM 0.16.0 multi-LoRA · PyTorch 2.5
+ PEFT · Qwen2.5-7B-Instruct base · Fireworks AI serverless · FastAPI · Docker

## The pitch

See [pitch/PITCH.md](pitch/PITCH.md).
