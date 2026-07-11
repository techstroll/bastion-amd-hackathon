# 🏰 Bastion — Private AI Cloud-in-a-Box

**AMD Developer Hackathon: ACT II — Track 3 (Unicorn)**

> Every department gets its own fine-tuned model, sensitive data never leaves
> the GPU, and a router keeps cost minimal per query — all on a **single AMD
> Instinct MI300X**.

## Why one GPU can be a whole AI cloud

The MI300X has **192 GB of HBM3 on one card**. That single fact enables three
things at once that normally require a GPU fleet:

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
the MI300X, hard queries go to the 70B path — and anything classified
sensitive is **pinned to the box, no exceptions**.

```
client (per-department API key)
   │
   ▼
┌────────────── Bastion Router ───────────────────────────────────┐
│ tenant lookup → sensitivity check → difficulty check            │
│                                                                  │
│ trivial + public ──► Fireworks serverless 8B      (external, $) │
│ normal ────────────► MI300X: base 8B + tenant LoRA (local)      │
│ hard ──────────────► MI300X: 70B path              (local)      │
│ sensitive ─────────► NEVER leaves the box                       │
└──────────────────────────────────────────────────────────────────┘
```

## Repo layout

| Path | What |
|---|---|
| `router/` | FastAPI gateway: OpenAI-compatible `/v1/chat/completions`, classifiers, backends, metrics |
| `gpu/` | Runs on the MI300X (AMD Developer Cloud notebook): LoRA fine-tune + vLLM multi-LoRA launch |
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

## Full deployment (AMD Developer Cloud MI300X)

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
| `bastion-legal-001` | Legal | `legal-lora` on MI300X |
| `bastion-finance-001` | Finance | `finance-lora` on MI300X |
| `bastion-general-001` | General | base 8B on MI300X |

```bash
curl localhost:9000/v1/chat/completions \
  -H "Authorization: Bearer bastion-legal-001" -H "Content-Type: application/json" \
  -d '{"messages":[{"role":"user","content":"Review this confidential NDA clause..."}]}'
```

The response includes a `bastion` block showing the routing decision:
tenant, engine, sensitivity + reasons, difficulty + reasons, latency, cost.

## Stack

AMD Instinct MI300X (192 GB) · ROCm 7.2 · vLLM 0.16.0 multi-LoRA · PyTorch 2.9
+ PEFT · Fireworks AI serverless (Llama-3.1-8B) · FastAPI · Docker

## The pitch

See [pitch/PITCH.md](pitch/PITCH.md).
