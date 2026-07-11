"""In-memory metrics + tamper-evident audit trail.

The dashboard polls /metrics; everything here is what the judges see live.
The audit trail is a separate, uncapped, hash-chained record for the
compliance-export story (/audit.csv).
"""

import csv
import hashlib
import io
import json
import time
from collections import deque
from dataclasses import dataclass, field, asdict
from threading import Lock


@dataclass
class Metrics:
    total_requests: int = 0
    sensitive_requests: int = 0
    sensitive_egress: int = 0        # raw sensitive data leaving — MUST stay 0
    declassified_external: int = 0   # PII-redacted queries safely sent to cheap tier
    external_calls: int = 0          # total calls that left the box (incl. declassified)
    by_engine: dict = field(default_factory=lambda: {
        "fireworks-8b": 0, "local-8b-lora": 0, "local-70b": 0,
    })
    cost_usd: float = 0.0
    would_cost_elsewhere_usd: float = 0.0
    log: deque = field(default_factory=lambda: deque(maxlen=100))


_m = Metrics()
_lock = Lock()

# Uncapped, hash-chained audit trail. Each entry embeds the SHA-256 of the
# previous entry, so any after-the-fact edit breaks the chain — the basis of
# the "tamper-evident compliance log" claim.
_audit: list[dict] = []
_GENESIS = "0" * 64


def _chain_hash(prev: str, entry: dict) -> str:
    payload = prev + json.dumps(entry, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode()).hexdigest()


def record(
    *,
    tenant: str,
    department: str,
    sensitive: bool,
    sensitivity_reasons: list[str],
    difficulty: str,
    difficulty_reasons: list[str],
    engine: str,
    model: str,
    external: bool,
    latency_ms: int,
    prompt_tokens: int,
    completion_tokens: int,
    cost_usd: float,
    would_cost_elsewhere_usd: float,
    preview: str,
    declassified: bool = False,
    redactions: list[str] | None = None,
) -> None:
    redactions = redactions or []
    # A sensitive query only counts as EGRESS if raw sensitive data left the
    # box. A declassified (PII-redacted) query that leaves is NOT egress — the
    # sensitive spans were masked before it ever went external.
    raw_sensitive_egress = sensitive and external and not declassified

    with _lock:
        _m.total_requests += 1
        _m.by_engine[engine] = _m.by_engine.get(engine, 0) + 1
        if sensitive:
            _m.sensitive_requests += 1
        if raw_sensitive_egress:
            _m.sensitive_egress += 1  # invariant violation — must never happen
        if declassified and external:
            _m.declassified_external += 1
        if external:
            _m.external_calls += 1
        _m.cost_usd += cost_usd
        _m.would_cost_elsewhere_usd += would_cost_elsewhere_usd

        entry = {
            "ts": time.strftime("%H:%M:%S"),
            "iso": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "tenant": tenant,
            "department": department,
            "sensitive": sensitive,
            "sensitivity_reasons": sensitivity_reasons,
            "difficulty": difficulty,
            "difficulty_reasons": difficulty_reasons,
            "engine": engine,
            "model": model,
            "external": external,
            "declassified": declassified,
            "redactions": redactions,
            "latency_ms": latency_ms,
            "tokens": prompt_tokens + completion_tokens,
            "cost_usd": round(cost_usd, 6),
            "preview": preview[:120],
        }
        _m.log.appendleft(entry)

        prev = _audit[-1]["hash"] if _audit else _GENESIS
        audit_entry = dict(entry)
        audit_entry["seq"] = len(_audit)
        audit_entry["prev_hash"] = prev
        audit_entry["hash"] = _chain_hash(prev, entry)
        _audit.append(audit_entry)


def snapshot() -> dict:
    with _lock:
        d = asdict(_m)
        d["log"] = list(_m.log)
        d["savings_usd"] = round(_m.would_cost_elsewhere_usd - _m.cost_usd, 6)
        d["cost_usd"] = round(_m.cost_usd, 6)
        d["would_cost_elsewhere_usd"] = round(_m.would_cost_elsewhere_usd, 6)
        d["audit_entries"] = len(_audit)
        return d


def audit_csv() -> str:
    """Full audit trail as CSV — the one-click compliance export."""
    cols = [
        "seq", "iso", "tenant", "department", "sensitive", "sensitivity_reasons",
        "difficulty", "engine", "model", "external", "declassified", "redactions",
        "latency_ms", "tokens", "cost_usd", "prev_hash", "hash",
    ]
    with _lock:
        rows = list(_audit)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=cols, extrasaction="ignore")
    w.writeheader()
    for r in rows:
        row = dict(r)
        row["sensitivity_reasons"] = "|".join(r.get("sensitivity_reasons", []))
        row["redactions"] = "|".join(r.get("redactions", []))
        w.writerow(row)
    return buf.getvalue()


def audit_verify() -> dict:
    """Re-walk the hash chain to prove the log hasn't been tampered with."""
    with _lock:
        rows = list(_audit)
    prev = _GENESIS
    for r in rows:
        entry = {k: r[k] for k in r if k not in ("seq", "prev_hash", "hash")}
        expected = _chain_hash(prev, entry)
        if r["prev_hash"] != prev or r["hash"] != expected:
            return {"ok": False, "broken_at_seq": r["seq"], "entries": len(rows)}
        prev = r["hash"]
    return {"ok": True, "entries": len(rows)}
