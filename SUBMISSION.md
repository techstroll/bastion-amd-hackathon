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
2. `rocm-smi`: base + 2 LoRAs (+ 70B) on ONE 192 GB MI300X (20 s)
3. Live: trivial query → Fireworks, cost ticker (20 s)
4. Live: confidential clause → legal-lora, 🔒 stayed local, egress = 0 (30 s)
5. Same question, legal vs finance tenant → two voices, one GPU (30 s)
6. Hard query → 70B path (15 s)
7. Dashboard wide shot + unit economics slide (30 s)

## lablab.ai submission form

- [ ] Public repo URL
- [ ] Demo video link
- [ ] Cover image (dashboard screenshot)
- [ ] Team + track (Track 3 — Unicorn)
- [ ] Blurb: "Every department gets its own fine-tuned model, sensitive data
      never leaves the GPU, and a router keeps cost minimal per query — all on
      a single AMD Instinct MI300X."
