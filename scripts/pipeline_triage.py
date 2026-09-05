#!/usr/bin/env python3
"""Deterministic complexity/risk gate for the L1/L2/L3 pipeline (see
.claude/rules/L1_architecture.md). Run this before deciding whether a task
can take the fast path (L1 implements directly) or needs the full pipeline
(L1 plans, L2 executes, L3 reviews).

This is intentionally NOT an LLM judgment call for the parts that don't need
one: file-path sensitivity and file count are checked with plain pattern
matching, the same way .cursor/rules/*.mdc glob matching avoids relying on
an LLM to decide which rules are relevant. L1 still applies judgment on top
of this for anything the patterns don't cover -- this script can only ever
escalate a "low"/"medium" risk tag to full_pipeline, never downgrade a
human-set "high" tag, and never turn a full_pipeline result back into
fast_path.

Usage:
    python scripts/pipeline_triage.py --risk low --files tests/conftest.py
    python scripts/pipeline_triage.py --risk medium --files a.py,b.py,c.py,d.py
    python scripts/pipeline_triage.py --risk high --files anything.py

Exit code: 0 = fast_path allowed, 1 = full_pipeline required.
Prints a JSON decision object to stdout either way.
"""
import argparse
import json
import re
import sys

# Path patterns that always force full_pipeline, regardless of the stated
# risk tag or file count -- these are the areas this repo's own CI/tests
# have already shown to be load-bearing (auth, payments, shipping crypto,
# schema, tenant isolation).
SENSITIVE_PATH_PATTERNS = [
    r"app/core/security",
    r"auth_router",
    r"payment",
    r"stripe",
    r"pay_order",
    r"checkout",
    r"cart_router",
    r"crypto\.py",
    r"shipping",
    r"ENCRYPTION",
    r"\.env",
    r"alembic/versions",
    r"models\.py",
    r"db/seed\.sql",
    r"schema",
    r"tenant_isolation",
    r"rls",
]

# A "trivial" task is single-file by definition (see L1_architecture.md).
# More than this many files means it isn't trivial even if no sensitive
# path matched.
MAX_FAST_PATH_FILES = 1

RISK_ORDER = {"low": 0, "medium": 1, "high": 2}


def classify(risk: str, files: list[str]) -> dict:
    reasons = []

    if risk not in RISK_ORDER:
        raise ValueError(f"--risk must be one of {list(RISK_ORDER)}, got {risk!r}")

    if not files:
        return {"decision": "full_pipeline", "reasons": ["no files given -- cannot be trivial"]}

    if risk == "high":
        reasons.append("risk tag is 'high' (set by the human at task definition -- never downgraded)")
        return {"decision": "full_pipeline", "reasons": reasons}

    if risk == "medium":
        reasons.append("risk tag is 'medium' -- only 'low' is eligible for the fast path")
        return {"decision": "full_pipeline", "reasons": reasons}

    if len(files) > MAX_FAST_PATH_FILES:
        reasons.append(
            f"{len(files)} files touched, fast path is limited to "
            f"{MAX_FAST_PATH_FILES} (multi-file changes get the full pipeline)"
        )
        return {"decision": "full_pipeline", "reasons": reasons}

    hits = []
    for f in files:
        for pattern in SENSITIVE_PATH_PATTERNS:
            if re.search(pattern, f, re.IGNORECASE):
                hits.append((f, pattern))

    if hits:
        for f, pattern in hits:
            reasons.append(f"'{f}' matches sensitive-path pattern '{pattern}'")
        return {"decision": "full_pipeline", "reasons": reasons}

    reasons.append("risk=low, single file, no sensitive-path match")
    return {"decision": "fast_path", "reasons": reasons}


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--risk", required=True, choices=list(RISK_ORDER), help="risk tag set by the human at task-definition time")
    parser.add_argument("--files", required=True, help="comma-separated list of files the plan intends to touch")
    args = parser.parse_args()

    files = [f.strip() for f in args.files.split(",") if f.strip()]
    result = classify(args.risk, files)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["decision"] == "fast_path" else 1)


if __name__ == "__main__":
    main()
