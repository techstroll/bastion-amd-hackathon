# Bastion — the private AI cloud-in-a-box

## The problem

Enterprises want department-grade AI (legal answers like a lawyer, finance
like a CFO) but face a three-way bind:

1. **Per-token APIs leak data** — legal, health, and finance teams can't send
   contracts, patient records, or unreleased earnings to external endpoints.
   Compliance says no; when it says yes, it costs months of review per vendor.
2. **Fine-tuned models don't scale on serving** — a dedicated GPU per
   fine-tuned model means N departments × N GPUs. Even Fireworks — best-in-class
   serverless — doesn't serve LoRAs serverless; every adapter needs a dedicated
   deployment.
3. **One-size models waste money** — routing "what's the capital of France"
   to a 70B (or a premium API) burns budget on queries an 8B answers.

## The insight

**AMD Instinct MI300X changes the serving math.** 192 GB of HBM3 on a single
card holds: an 8B base + *dozens* of per-department LoRA adapters + a 70B for
hard queries — simultaneously. Train the adapters on the same card. Nothing
ever leaves the box.

What used to be a GPU fleet + an MLOps team + a compliance program is now
**one card and a router**.

## The product

An appliance (or dedicated-cloud instance) + a gateway:

- **Per-department models**: each department's private data fine-tunes its own
  LoRA, on-box. Adding a department costs megabytes of VRAM, not a GPU.
- **Sovereignty by construction**: the router pins anything sensitive
  (PII/confidential, classified in <1 ms) to local engines. A live egress
  meter reads **0** — auditable, demoable, sellable to compliance.
- **Cost routing**: trivial public queries burst to Fireworks serverless;
  everything else is served at owned-hardware unit economics.

## Why now, why AMD

- MI300X dedicated-cloud pricing ($1.99/hr on AMD Developer Cloud) makes
  owned-inference economics available to mid-market, not just hyperscalers.
- vLLM multi-LoRA on ROCm is production-grade **today** — this demo runs on
  the stock ROCm 7.2 + vLLM 0.16 image, zero custom kernels.
- The 192 GB single-card capacity is an AMD-specific moat: the same build on
  80 GB cards needs 2–3× the hardware and cross-GPU orchestration.

## Unit economics (demo-scale illustration)

| | Per-token API (70B-class) | Bastion on 1× MI300X |
|---|---|---|
| 10 departments, fine-tuned | 10 dedicated deployments | 1 GPU, 10 adapters |
| $/1M tokens (blended) | ~$0.90 | ~$0.06–0.15 |
| Sensitive-data egress | vendor DPA + review | **zero by construction** |
| Add a department | new deployment | `finetune_lora.py --tenant X` (minutes) |

At ~$38K/mo of API spend, breakeven on a dedicated MI300X is under a month.

## Go-to-market

1. **Design partners**: legal-tech and healthcare mid-market (100–2,000 seats)
   already blocked from external AI by compliance.
2. **Land**: one appliance/instance, 2–3 departments, 30-day pilot measuring
   $/1K tokens vs. API baseline + egress audit report.
3. **Expand**: per-department adapter subscriptions; the marginal cost of a
   new tenant is near zero — software margins on hardware economics.

## The ask (hackathon framing)

Working vertical slice, built this weekend on AMD Developer Cloud:
multi-LoRA serving + on-box fine-tuning + sensitivity/cost router + live
egress-and-cost dashboard, containerized. Everything in the demo is real
infrastructure — no slides-ware.

**One MI300X. Every department. Zero egress.**
