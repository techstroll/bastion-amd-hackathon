# Submission checklist — deadline Jul 11, 11:00 PM IT

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
4. **Click "＋ Onboard HR department (live)"** → HR adapter hot-loads into the
   running GPU, new pill appears in the telemetry panel, then send an HR query.
   The mic-drop: "new department, zero restart, zero new hardware." (30 s)
5. **Click "Export compliance audit"** + "Verify audit chain" → tamper-evident
   CSV, chain verified (15 s)
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
