# Bastion Console — Client Walkthrough, Features & Verification

How a customer actually uses Bastion, screen by screen, plus the exact tests
that prove routing is correct.

---

## The cast (who's using it)

| Persona | Cares about | Lives on which screen |
|---|---|---|
| **IT / Platform admin** | onboarding departments, GPU capacity | Departments, GPU |
| **Department end-user** (legal/finance/HR analyst) | getting a good answer, fast | *their app* → Playground proves it |
| **CISO / Compliance officer** | "does sensitive data ever leave?" | Compliance, Overview |
| **CFO / FinOps** | cost vs. cloud APIs | Overview |

---

## Screen 1 — Overview (the control room)

**What the client sees:** live tiles (total requests, sensitive requests, **raw
sensitive egress = 0**, declassified count, cost saved), an engine-distribution
bar, a live GPU mini-panel, and a streaming log of every routing decision.

**What it proves:** the system is alive, sensitive data is sealed, and money is
being saved — the 10-second executive read.

## Screen 2 — Playground (⭐ this is your verification tool)

**What the client does:**
1. Pick **"Acting as"** → a department (e.g. *Finance Dept*).
2. Type a message, or hit a **Quick test** chip.
3. Click **Send request →**.

**What comes back, side by side:**
- **How Bastion routed it** — verdict badge (🔒 stayed local / ☁ external /
  🛡 declassified), engine used, model/adapter, sensitive? + why, declassified?
  + what was masked, difficulty, left-the-box?, latency, cost.
- **Answer returned to the user** — the actual model output, in that
  department's voice.

**This is how you verify a real case end-to-end** — you see the input, the
routing logic, *and* the result in one screen.

## Screen 3 — Departments (self-service onboarding)

**What the admin sees:** every department, its adapter, a **masked API key**
(with copy button), and where it runs. A form to **onboard a new department
live** — type a name, the adapter path auto-fills, one click hot-loads it into
the running GPU. New department appears instantly; no restart, no new hardware.

## Screen 4 — Compliance (the auditor's screen)

**What the officer sees:** egress = 0 tile, audit-entry count, declassified
count, and two buttons: **Export audit trail (CSV)** and **Verify chain
integrity**. Every decision is hash-chained — verification re-walks the chain
and proves nothing was altered.

## Screen 5 — GPU (the AMD hardware story)

**What the client sees:** live VRAM usage bar and the list of every model +
adapter resident **on the one card** — the "one GPU, many departments" proof,
with the "scales to MI300X 192 GB" note.

---

## ✅ Verification test matrix (do these in the Playground)

Run each row; confirm the "How Bastion routed it" panel matches **Expected**.

| # | Act as | Message | Expected engine | Expected verdict |
|---|---|---|---|---|
| 1 | General | `What is the capital of France?` | Fireworks (external) | ☁ external, not sensitive |
| 2 | Finance | `Summarize this confidential merger agreement and its key risks.` | AMD GPU · finance-lora | 🔒 stayed local (sensitive-keyword) |
| 3 | Legal | `Review the indemnification clause in our vendor contract.` | AMD GPU · legal-lora | 🔒 stayed local |
| 4 | General | `Translate to French: reach me at john.doe@acme.com` | Fireworks (external) | 🛡 declassified (email masked), egress still 0 |
| 5 | Finance | `A patient invoice with account 4532-1143-8765-3321 went to the wrong client.` | AMD GPU · finance-lora | 🔒 stayed local (card+keyword, NOT redactable) |
| 6 | General | `Analyze in depth, step by step, the trade-offs between leasing and buying hardware.` | AMD GPU · large model | 🔒 stayed local (hard) |
| 7 | Finance | (same as #2) then **switch to Legal**, ask #2 | finance-lora vs legal-lora | different voices, same card |

**The two money-shot rows for the demo:** #4 (declassification — we don't just
block, we minimize) and #7 (multi-LoRA — two departments, two voices, one GPU).

**After running the matrix**, open **Compliance → Verify chain integrity** →
should report the chain intact with N entries, and **Raw sensitive egress**
on Overview should still read **0**.

---

## Real vs. showcase — what's live where

| | Render showcase (BASTION_DEMO=1) | AMD Developer Cloud (GPU) |
|---|---|---|
| Routing / classify / audit | **real code** | **real code** |
| Answers | simulated (canned per adapter) | **real fine-tuned model output** |
| GPU telemetry | simulated (labeled) | **real rocm-smi** |
| Purpose | always-on URL for judges | the truth, shown in the video |

Routing verification (which engine, sensitive?, declassified?, egress) is
**identical** in both — only the answer text differs. So the Playground proves
correctness even on the showcase URL.
