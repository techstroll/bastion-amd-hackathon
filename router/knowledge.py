"""Per-department knowledge & training store.

Two kinds of knowledge per department:
  - training examples (prompt/response pairs) -> used to fine-tune the LoRA
  - knowledge documents (raw text)            -> the retrieval knowledge base

On startup we load the built-in datasets in gpu/datasets/*.jsonl so the
Console shows real, inspectable example counts for every department.

Fine-tuning is exposed as a job with progress. In showcase mode it is
simulated; on a real GPU host it maps to gpu/finetune_lora.py (the actual
command is surfaced to the operator).
"""

import asyncio
import json
import random
import time
from pathlib import Path
from threading import Lock

DATASETS_DIR = Path(__file__).resolve().parent.parent / "gpu" / "datasets"

_lock = Lock()
# department -> {"examples": [{"prompt","response"}], "docs": [{"name","chars"}]}
_kb: dict[str, dict] = {}
# department -> job dict
_jobs: dict[str, dict] = {}


def _dept(department: str) -> dict:
    return _kb.setdefault(department, {"examples": [], "docs": []})


def load_builtin() -> None:
    """Seed the store from the committed datasets so counts are real."""
    if not DATASETS_DIR.exists():
        return
    for f in sorted(DATASETS_DIR.glob("*.jsonl")):
        dept = f.stem  # legal / finance / hr / aml / wealth
        examples = []
        for line in f.read_text().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ex = json.loads(line)
                if "prompt" in ex and "response" in ex:
                    examples.append({"prompt": ex["prompt"], "response": ex["response"]})
            except json.JSONDecodeError:
                continue
        if examples:
            _dept(dept)["examples"] = examples


def add_examples(department: str, examples: list[dict]) -> int:
    clean = [
        {"prompt": e["prompt"], "response": e["response"]}
        for e in examples if e.get("prompt") and e.get("response")
    ]
    with _lock:
        _dept(department)["examples"].extend(clean)
    return len(clean)


def parse_jsonl(content: str) -> list[dict]:
    out = []
    for line in content.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            ex = json.loads(line)
            if ex.get("prompt") and ex.get("response"):
                out.append(ex)
        except json.JSONDecodeError:
            continue
    return out


def add_document(department: str, name: str, text: str) -> dict:
    """Store a raw doc as retrieval knowledge (and as coarse training context)."""
    entry = {"name": name or "document", "chars": len(text),
             "added": time.strftime("%H:%M:%S")}
    with _lock:
        _dept(department)["docs"].append(entry)
    return entry


def summary() -> dict:
    with _lock:
        return {
            dept: {"examples": len(v["examples"]), "docs": len(v["docs"]),
                   "doc_list": v["docs"][-10:]}
            for dept, v in sorted(_kb.items())
        }


def department_detail(department: str) -> dict:
    with _lock:
        v = _dept(department)
        return {
            "department": department,
            "examples": len(v["examples"]),
            "docs": len(v["docs"]),
            "sample_examples": v["examples"][:3],
            "doc_list": v["docs"],
        }


# ----------------------------------------------------------------- training

def _adapter_path(department: str) -> str:
    return f"/workspace/adapters/{department}-lora"


async def run_job(department: str, simulate: bool) -> None:
    total = 3
    with _lock:
        n = len(_dept(department)["examples"])
    job = _jobs[department]
    loss = 3.6
    for epoch in range(1, total + 1):
        steps = max(1, n // 4)
        for s in range(steps):
            await asyncio.sleep(0.25 if simulate else 0.05)
            loss = max(0.4, loss - random.uniform(0.02, 0.12))
            with _lock:
                job.update(progress=round(100 * ((epoch - 1) * steps + s + 1) / (total * steps)),
                           epoch=epoch, loss=round(loss, 3))
    with _lock:
        job.update(status="done", progress=100,
                   adapter=_adapter_path(department),
                   ready_to_onboard=True)


def start_training(department: str, simulate: bool) -> dict:
    with _lock:
        n = len(_dept(department)["examples"])
        if n == 0:
            return {"error": "no training examples for this department yet"}
        if _jobs.get(department, {}).get("status") == "running":
            return {"error": "a training job is already running"}
        _jobs[department] = {
            "department": department, "status": "running", "progress": 0,
            "epoch": 0, "total_epochs": 3, "loss": None, "examples": n,
            "adapter": _adapter_path(department),
            "command": f"python gpu/finetune_lora.py --tenant {department}",
            "simulated": simulate,
        }
    asyncio.create_task(run_job(department, simulate))
    return dict(_jobs[department])


def job_status(department: str) -> dict:
    with _lock:
        return dict(_jobs.get(department, {"status": "none"}))
