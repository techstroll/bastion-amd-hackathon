# Bank Client Scenario — "Northwind Bank" runs Bastion

A worked example of Bastion in a regulated bank: departments, real queries,
how each routes, and the compliance framing that makes a bank say yes.

Run it: `python demo/bank_scenario.py` (or use the **Playground** page).

---

## Why a bank is the ideal Bastion customer

Banks want AI in every department but are boxed in by regulation:

- **GLBA** (Gramm-Leach-Bliley) — safeguard customer financial data.
- **PCI-DSS** — cardholder data must not sprawl to third parties.
- **BSA / AML** — SAR content is legally confidential; tipping-off is unlawful.
- **SOX** — auditable controls over financial reporting.
- **SR 11-7 / model risk** — models must be governed and documented.

A per-token public API fails all of these the moment a customer's SSN, card
number, or a SAR narrative is in the prompt. Bastion's answer: **it never
leaves the bank's own GPU**, and every decision is on a tamper-evident ledger.

## Northwind Bank's departments (each = one LoRA on one GPU)

| Department | Adapter | Handles |
|---|---|---|
| Retail Banking / Customer Service | base / general | everyday customer questions |
| Treasury & Markets | finance-lora | NIM, funding, board reporting |
| Legal & Regulatory Compliance | legal-lora | contracts, GLBA, regulatory |
| Financial Crime / AML | **aml-lora** | SAR/CTR, KYC, sanctions |
| Wealth Management | **wealth-lora** | client advisory (suitability-aware) |

*AML and Wealth are onboarded **live** in the demo — the mic-drop: a new
regulated department stood up on the same card, zero restart.*

## The routing, query by query (verified)

| # | Department | Query | Routes to | Why |
|---|---|---|---|---|
| 1 | Retail | "What are your branch opening hours?" | ☁ Fireworks | public, trivial — cheap tier is fine |
| 2 | Retail | "Translate to Spanish: welcome email for jane.smith@gmail.com" | 🛡 declassified | email **masked**, safe residual goes external; egress still 0 |
| 3 | Treasury | "Summarize our **confidential** Q3 net interest margin for the board" | 🔒 local | confidential financials never leave |
| 4 | Legal | "Review this **internal-only** vendor clause, flag GLBA risks" | 🔒 local | regulated contract stays on-box |
| 5 | AML | "Three $9,500 cash deposits this week — reportable **SAR**?" | 🔒 local | SAR content is legally confidential |
| 6 | AML | "**Wire** from a **sanctioned** jurisdiction for account 4021-…-0098" | 🔒 local | sanctions + card number — must stay local |
| 7 | Wealth | "Client nearing retirement wants to reduce **portfolio** risk" | 🔒 local | client financial profile stays on-box |
| 8 | Retail | "Analyze in depth, step by step, a high-yield savings product" | 🔒 local (large model) | hard reasoning → local larger model |

**Result:** raw sensitive egress = **0**, one declassified call, everything
regulated stayed on the bank's AMD GPU — and every line is in the exportable,
hash-chained audit trail.

## The two moments that close a bank

1. **The sanctioned-wire test (#6).** A query that contains a card number *and*
   a sanctions reference is the exact thing a public API must never see.
   Bastion pins it local, automatically. Show the CISO the egress counter: 0.
2. **Live-onboard "Financial Crime / AML."** Stand up a new regulated
   department on the same card during the demo, then ask it a SAR question and
   watch it answer in-house. "This is how fast you add a compliance-grade
   assistant — no new hardware, no data leaving the building."

## Deploying the bank departments (on the GPU)

```bash
python gpu/finetune_lora.py --tenant aml
python gpu/finetune_lora.py --tenant wealth
# then onboard them live from the Departments page, or:
curl -X POST $ROUTER/admin/tenants -H "Content-Type: application/json" \
  -d '{"department":"aml","adapter_path":"/workspace/adapters/aml-lora"}'
curl -X POST $ROUTER/admin/tenants -H "Content-Type: application/json" \
  -d '{"department":"wealth","adapter_path":"/workspace/adapters/wealth-lora"}'
```

On the Render showcase, the adapters hot-load in the simulated engine, so the
whole bank story is demoable at the public URL too.

## The economics a bank CFO cares about

- One AMD GPU serves every department vs. a fleet of dedicated model endpoints.
- ~90% below per-token API pricing at steady state; breakeven under a month at
  typical mid-size-bank AI spend.
- Scales unchanged to AMD Instinct MI300X (192 GB) — a whole bank's departments,
  plus a co-resident large model, on one card.

*Educational/demo content. Regulatory summaries are illustrative, not legal or
compliance advice.*
