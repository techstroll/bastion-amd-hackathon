"""In-memory metrics: routing log, per-tenant egress counters, cost ledger.

The dashboard polls /metrics; everything here is what the judges see live.
"""

import time
from collections import deque
from dataclasses import dataclass, field, asdict
from threading import Lock


@dataclass
class Metrics:
    total_requests: int = 0
    sensitive_requests: int = 0
    sensitive_egress: int = 0        # MUST stay 0 — the money-shot metric
    external_calls: int = 0          # non-sensitive Fireworks calls (allowed)
    by_engine: dict = field(default_factory=lambda: {
        "fireworks-8b": 0, "local-8b-lora": 0, "local-70b": 0,
    })
    cost_usd: float = 0.0
    would_cost_elsewhere_usd: float = 0.0
    log: deque = field(default_factory=lambda: deque(maxlen=100))


_m = Metrics()
_lock = Lock()


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
) -> None:
    with _lock:
        _m.total_requests += 1
        _m.by_engine[engine] = _m.by_engine.get(engine, 0) + 1
        if sensitive:
            _m.sensitive_requests += 1
            if external:
                _m.sensitive_egress += 1  # should never happen
        if external:
            _m.external_calls += 1
        _m.cost_usd += cost_usd
        _m.would_cost_elsewhere_usd += would_cost_elsewhere_usd
        _m.log.appendleft({
            "ts": time.strftime("%H:%M:%S"),
            "tenant": tenant,
            "department": department,
            "sensitive": sensitive,
            "sensitivity_reasons": sensitivity_reasons,
            "difficulty": difficulty,
            "difficulty_reasons": difficulty_reasons,
            "engine": engine,
            "model": model,
            "external": external,
            "latency_ms": latency_ms,
            "tokens": prompt_tokens + completion_tokens,
            "cost_usd": round(cost_usd, 6),
            "preview": preview[:120],
        })


def snapshot() -> dict:
    with _lock:
        d = asdict(_m)
        d["log"] = list(_m.log)
        d["savings_usd"] = round(_m.would_cost_elsewhere_usd - _m.cost_usd, 6)
        d["cost_usd"] = round(_m.cost_usd, 6)
        d["would_cost_elsewhere_usd"] = round(_m.would_cost_elsewhere_usd, 6)
        return d
