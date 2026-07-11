"""Bank client scenario — 'Northwind Bank' running Bastion.

Sends a realistic sequence of banking queries across departments and prints
how Bastion routed each one. Frames the existing tenants as bank departments:

  bastion-general-001  -> Retail Banking / Customer Service
  bastion-finance-001  -> Treasury & Markets
  bastion-legal-001    -> Legal & Regulatory Compliance
  bastion-hr-001       -> HR   (onboard live first, or omit)
  bastion-aml-001      -> Financial Crime / AML  (onboard live first)
  bastion-wealth-001   -> Wealth Management       (onboard live first)

Usage:
  python demo/bank_scenario.py [--router http://localhost:9000]

To include AML/Wealth, first train + onboard them (or run on the showcase where
the adapters can be hot-loaded):
  curl -X POST $ROUTER/admin/tenants -d '{"department":"aml","adapter_path":"/workspace/adapters/aml-lora"}'
  curl -X POST $ROUTER/admin/tenants -d '{"department":"wealth","adapter_path":"/workspace/adapters/wealth-lora"}'
"""

import argparse
import json
import urllib.request

BANK = "Northwind Bank"

# (api key, banking-department label, message)
SCENARIO = [
    ("bastion-general-001", "Retail Banking",
     "What are your branch opening hours?"),  # public -> external
    ("bastion-general-001", "Retail Banking",
     "Translate to Spanish: welcome email for jane.smith@gmail.com"),  # PII email, trivial -> declassified
    ("bastion-finance-001", "Treasury & Markets",
     "Summarize our confidential Q3 net interest margin and the variance vs. plan for the board."),  # sensitive -> local
    ("bastion-legal-001", "Legal & Compliance",
     "Review this internal-only vendor contract clause on data processing and flag GLBA risks."),  # sensitive -> local
    ("bastion-aml-001", "Financial Crime / AML",
     "A customer made three $9,500 cash deposits this week. Is this a reportable SAR?"),  # sensitive -> local (aml)
    ("bastion-aml-001", "Financial Crime / AML",
     "A wire arrived from a sanctioned jurisdiction for account 4021-8837-2261-0098. Next steps?"),  # card+sanctions -> local
    ("bastion-wealth-001", "Wealth Management",
     "A client nearing retirement wants to reduce portfolio risk. How should I frame it?"),  # advisory -> local (keyword: portfolio)
    ("bastion-general-001", "Retail Banking",
     "Analyze in depth, step by step, the trade-offs of launching a high-yield savings product."),  # hard -> large model
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--router", default="http://localhost:9000")
    args = ap.parse_args()

    print(f"\n=== {BANK} — Bastion routing demo ===\n")
    for i, (key, dept, text) in enumerate(SCENARIO, 1):
        req = urllib.request.Request(
            f"{args.router}/v1/chat/completions",
            data=json.dumps({"messages": [{"role": "user", "content": text}]}).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                b = json.loads(resp.read())["bastion"]
        except Exception as e:
            print(f"[{i}] {dept:22s} -> ERROR: {e} "
                  f"(department not onboarded? see file header)")
            continue

        if b["declassified"]:
            verdict = f"🛡 declassified (masked {', '.join(b['redactions'])})"
        elif b["external"]:
            verdict = "☁ external (non-sensitive)"
        else:
            verdict = "🔒 stayed on the AMD GPU"
        print(f"[{i}] {dept:22s} {b['engine']:14s} {verdict}")

    print(f"\nDone — open the Console; raw sensitive egress should read 0.\n")


if __name__ == "__main__":
    main()
