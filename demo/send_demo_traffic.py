"""Send the scripted demo traffic through the Bastion router.

Usage: python demo/send_demo_traffic.py [--router http://localhost:9000]

Fires the exact sequence from the demo script in PLAN.md so the dashboard
tells the story: cheap public queries -> Fireworks; confidential queries ->
tenant LoRA, egress stays 0; hard query -> 70B path; same question to two
tenants -> different department voice.
"""

import argparse
import json
import time
import urllib.request

DEMO = [
    # (tenant key, message) — order matters for the narrative
    ("bastion-general-001", "What is the capital of France?"),
    ("bastion-general-001", "Convert 100 USD to EUR"),
    ("bastion-finance-001",
     "Our confidential Q3 earnings report shows revenue of $4.2M. "
     "Summarize the variance drivers for the board."),
    ("bastion-legal-001",
     "Review this internal-only NDA clause: the receiving party may share "
     "Confidential Information with its affiliates without notice."),
    ("bastion-legal-001",
     "We are considering consolidating all AI inference onto company-owned "
     "hardware instead of external APIs. What should we consider?"),
    ("bastion-finance-001",
     "We are considering consolidating all AI inference onto company-owned "
     "hardware instead of external APIs. What should we consider?"),
    ("bastion-general-001",
     "Analyze in depth the trade-offs between microservices and a modular "
     "monolith for a 40-engineer team, step by step, considering operational "
     "complexity, hiring, deployment risk, and long-term architecture evolution."),
    ("bastion-finance-001",
     "A patient invoice with account number 4532-1143-8765-3321 was sent to the "
     "wrong client. Draft the internal incident summary."),
]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--router", default="http://localhost:9000")
    args = ap.parse_args()

    for i, (key, text) in enumerate(DEMO, 1):
        req = urllib.request.Request(
            f"{args.router}/v1/chat/completions",
            data=json.dumps({
                "model": "bastion",
                "messages": [{"role": "user", "content": text}],
            }).encode(),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        )
        t0 = time.monotonic()
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = json.loads(resp.read())
        b = data["bastion"]
        print(
            f"[{i}/{len(DEMO)}] {b['department']:8s} -> {b['engine']:14s} "
            f"{'SENSITIVE' if b['sensitive'] else 'public   '} "
            f"{b['difficulty']:7s} {int((time.monotonic() - t0) * 1000)}ms "
            f"external={b['external']}"
        )
        time.sleep(1.0)  # let the dashboard animate

    print("\nDone — open the dashboard at", args.router)


if __name__ == "__main__":
    main()
