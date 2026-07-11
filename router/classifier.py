"""Query classification: sensitivity (may it leave the box?) and difficulty (which engine?).

Deterministic and fast (<1 ms) — heuristics chosen so the routing decision is
explainable in the dashboard. A production build would back this with a small
local guard model; the interface stays the same.
"""

import re
from dataclasses import dataclass

# ---------------------------------------------------------------- sensitivity

# PII / secrets patterns — any hit means the query must stay on the box.
_PII_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("credit_card", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    ("iban", re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{10,30}\b")),
    ("email", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.]+\b")),
    ("phone", re.compile(r"\b(?:\+?\d{1,3}[ -]?)?(?:\(\d{2,4}\)[ -]?)?\d{3,4}[ -]?\d{4}\b")),
    ("api_key", re.compile(r"\b(?:sk|pk|key|token)[-_][A-Za-z0-9]{16,}\b", re.I)),
]

_SENSITIVE_KEYWORDS = re.compile(
    r"\b(confidential|proprietary|internal[- ]only|do not (?:share|distribute)|nda|"
    r"attorney[- ]client|privileged|trade secret|salary|salaries|compensation|"
    r"acquisition|merger|m&a|layoff|termination|lawsuit|settlement|patient|diagnosis|"
    r"contract|clause|agreement|invoice|account number|routing number|earnings (?:call|report)|"
    r"unreleased|pre[- ]release|embargo|"
    # banking / financial-crime terms — a bank treats these as must-stay-local
    r"wire(?: transfer)?|swift|kyc|know your customer|aml|anti[- ]money|suspicious activity|"
    r"\bsar\b|beneficial owner|politically exposed|\bpep\b|sanction(?:s|ed)?|ofac|"
    r"loan application|mortgage|underwriting|credit score|credit report|chargeback|"
    r"fraud|customer (?:record|data|pii)|cardholder|portfolio|net worth|balance)\b",
    re.I,
)


@dataclass(frozen=True)
class Classification:
    sensitive: bool
    sensitivity_reasons: list[str]
    difficulty: str  # "trivial" | "normal" | "hard"
    difficulty_reasons: list[str]
    pii_types: list[str]       # which PII patterns matched (redactable)
    keyword_sensitive: bool    # confidential/NDA-type — cannot be safely redacted

    @property
    def redactable(self) -> bool:
        # Sensitivity comes ONLY from PII we can mask (no free-text secrets like
        # "confidential merger terms" that redaction can't neutralize).
        return bool(self.pii_types) and not self.keyword_sensitive


def classify_sensitivity(text: str) -> tuple[bool, list[str], list[str], bool]:
    pii_types = [name for name, pat in _PII_PATTERNS if pat.search(text)]
    keyword = bool(_SENSITIVE_KEYWORDS.search(text))
    reasons = list(pii_types) + (["sensitive-keyword"] if keyword else [])
    return (len(reasons) > 0, reasons, pii_types, keyword)


def redact(text: str) -> tuple[str, list[str]]:
    """Mask every PII span so the residual text is safe to send off-box.

    Returns (redacted_text, list_of_redaction_labels). Keyword-sensitivity is
    NOT handled here — that content can't be neutralized by masking and must
    stay local.
    """
    applied: list[str] = []
    out = text
    for name, pat in _PII_PATTERNS:
        if pat.search(out):
            out = pat.sub(f"[REDACTED_{name.upper()}]", out)
            applied.append(name)
    return out, applied


# ---------------------------------------------------------------- difficulty

_HARD_MARKERS = re.compile(
    r"\b(prove|derive|step[- ]by[- ]step|chain of|multi[- ]step|analy[sz]e in depth|"
    r"compare and contrast|trade[- ]?offs?|architecture|refactor|optimi[sz]e|"
    r"legal implications|risk assessment|comprehensive|walk me through)\b",
    re.I,
)
_CODE_OR_MATH = re.compile(r"(```|\bdef |\bclass |\bSELECT\b|[∑∫√]|\\frac|\d+\s*[*/^]\s*\d+)")
_TRIVIAL_MARKERS = re.compile(
    r"^\s*(what is|what's|who is|when (?:is|was|did)|define|translate|convert|"
    r"how do you spell|capital of)\b",
    re.I,
)


def classify_difficulty(text: str) -> tuple[str, list[str]]:
    words = len(text.split())
    reasons: list[str] = []

    if _HARD_MARKERS.search(text):
        reasons.append("reasoning-marker")
    if _CODE_OR_MATH.search(text):
        reasons.append("code-or-math")
    if words > 150:
        reasons.append(f"long-input({words}w)")
    if reasons:
        return "hard", reasons

    if _TRIVIAL_MARKERS.search(text) and words <= 25:
        return "trivial", ["simple-lookup", f"short({words}w)"]
    if words <= 12:
        return "trivial", [f"short({words}w)"]

    return "normal", [f"medium({words}w)"]


def classify(text: str) -> Classification:
    sensitive, s_reasons, pii_types, keyword = classify_sensitivity(text)
    difficulty, d_reasons = classify_difficulty(text)
    return Classification(
        sensitive, s_reasons, difficulty, d_reasons, pii_types, keyword
    )
