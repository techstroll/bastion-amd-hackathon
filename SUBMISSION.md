# Submission checklist — deadline Jul 11, 11:00 PM IT

## ✂️ Copy-paste content for the lablab.ai form

**Submission Title** (max 50 chars):

```
Bastion — Private AI Cloud-in-a-Box on AMD
```

**Short Description** (max 255 chars):

```
Every department gets its own fine-tuned model on ONE AMD GPU. Sensitive data never leaves the box, PII is auto-redacted before any external call, and a cost router + tamper-evident audit make it enterprise-ready. Scales straight to MI300X.
```

**Long Description** (min 100 words):

```
Enterprises want department-grade AI — legal that answers like counsel, finance
like a CFO — but hit a three-way bind: per-token APIs leak sensitive data, a
dedicated GPU per fine-tuned model destroys the economics, and one-size models
waste budget on trivial queries.

Bastion solves all three on a single AMD GPU. A base model plus one LoRA
adapter per department are served simultaneously from one card via vLLM
multi-LoRA on ROCm; adapters are fine-tuned on the same box, so private data
never leaves it. In front sits a policy router that classifies every query in
under a millisecond: raw-sensitive content is pinned to local engines
(live egress counter reads zero), PII-only queries are automatically redacted
and the declassified residual is served by the cheap Fireworks AI serverless
tier, hard questions escalate to a larger local model, and everything else
hits the department's own adapter.

The Bastion Console — a branded, mobile-responsive admin platform — lets teams
onboard a new department live: one form hot-loads its adapter into the running
GPU with zero restart and zero new hardware. Every routing decision lands in a
hash-chained, tamper-evident audit trail with one-click CSV export and chain
verification — the compliance artifact regulated buyers actually ask for.

Everything shown is real infrastructure built this weekend on AMD Developer
Cloud (ROCm 7.2 + vLLM + PyTorch, Radeon PRO W7900). The same code scales
unchanged to AMD Instinct MI300X, where 192 GB HBM3 hosts dozens of
departments — plus a co-resident 70B hard-tier — on one card. One AMD GPU.
Every department. Zero egress.
```

**Main Track:** Unicorn Track (Track 3)

**Technologies:** AMD Developer Cloud · AMD ROCm · vLLM · PyTorch · PEFT/LoRA ·
Qwen 2.5 · Fireworks AI · FastAPI · Docker

**GitHub Repository:** `https://github.com/techstroll/bastion-amd-hackathon`

**Demo Application Platform:** Hugging Face Spaces (always-on showcase) +
AMD Developer Cloud (GPU deployment shown in video)

**Demo Application URL:** `https://huggingface.co/spaces/<your-hf-username>/bastion-console`
(fill in after deploying — see deploy/hf-space/README.md)

**Additional Information:**

```
Scaling beyond the hackathon: the demo runs on a 48 GB Radeon PRO W7900; the
identical codebase on an AMD Instinct MI300X (192 GB HBM3) serves dozens of
department adapters plus a co-resident 70B hard tier on ONE card — multi-tenant
AI at appliance economics (~90% below per-token API pricing at steady state,
breakeven < 1 month at ~$38K/mo API spend). Multi-LoRA serving economics are
market-validated (Predibase/LoRAX); Bastion differentiates on what enterprises
actually buy: data sovereignty by construction, PII declassification, policy
routing, and a tamper-evident audit trail. Roadmap: RBAC/SSO, per-department
budgets, policy-as-code, guard-model classification, PWA mobile alerts, and
multi-site fleet management. The public demo URL is an honestly-labeled
showcase instance (simulated engine, real router/audit code); the video shows
the full GPU deployment on AMD Developer Cloud.
```

---

## Must-do on the GPU (in order, ~2–3 hrs GPU time)

- [ ] Open ADC notebook (ROCm 7.2 + vLLM 0.16.0 + PyTorch 2.9)
- [ ] Clone this repo into the notebook
- [ ] `pip install peft datasets transformers`
- [ ] `python gpu/finetune_lora.py --tenant legal` (few minutes)
- [ ] `python gpu/finetune_lora.py --tenant finance`
- [ ] `bash gpu/serve_multilora.sh` → wait for "Application startup complete"
- [ ] `curl localhost:8000/v1/models` shows base + legal-lora + finance-lora
- [ ] (stretch) `ENABLE_70B=1 bash gpu/serve_multilora.sh` for the real 70B tier
- [ ] Screenshot `rocm-smi` showing everything resident on ONE GPU ← pitch slide

## Router + demo

- [ ] Set FIREWORKS_API_KEY in .env (so trivial queries visibly burst external)
- [ ] `docker compose up --build` (containerization requirement ✓)
- [ ] `python demo/send_demo_traffic.py`
- [ ] Record demo video off the dashboard (see demo script in PLAN.md)

## Demo video beats (2–3 min)

1. The problem: fleet-per-department + data egress (10 s)
2. **GPU telemetry panel** (right card): base + legal + finance LoRAs all
   resident on ONE Radeon W7900 — "one card, many models" (20 s)
3. Run `demo/send_demo_traffic.py`, narrate the live table:
   - trivial public → Fireworks, cost ticker moves (15 s)
   - confidential NDA → legal-lora, 🔒 **stayed local**, raw egress = 0 (20 s)
   - **declassified**: email/phone query → 🛡 PII masked, safely external,
     egress STILL 0 — "we don't just block, we minimize" (25 s)
   - same question legal vs finance → two voices, one GPU (20 s)
   - hard query → larger-model path (10 s)
4. **Departments page** → type "hr" in the onboarding form (adapter path
   auto-fills) → click "＋ Hot-load & onboard" → HR appears in the tenant
   table AND as a new pill in GPU telemetry, then send an HR query.
   The mic-drop: "new department, zero restart, zero new hardware." (30 s)
5. **Compliance page** → "Export audit trail (CSV)" + "Verify chain
   integrity" → tamper-evident CSV, chain verified (15 s)
6. Dashboard wide shot: egress 0, declassified N, cost saved, unit economics (20 s)

## lablab.ai submission form

- [ ] Public repo URL
- [ ] Demo video link
- [ ] Cover image (dashboard screenshot)
- [ ] Team + track (Track 3 — Unicorn)
- [ ] Blurb: "Every department gets its own fine-tuned model, sensitive data
      never leaves the GPU, and a router keeps cost minimal per query — all on
      a single AMD GPU. Live department onboarding, PII declassification, and
      a tamper-evident compliance audit — scales straight to MI300X."
