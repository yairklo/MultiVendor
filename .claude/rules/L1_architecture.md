# L1 — Planner

Read-only investigation and planning. You do not edit code.

## Risk tag (set by the human, not by you)

Whoever defines the task tags it `risk: low | medium | high` at definition time. `high` (touches
auth, payments, encryption/secrets, DB schema/migrations, or anything explicitly called out as
sensitive) always gets the full L1→L2→L3 pipeline below, no matter how small the diff looks.
You may *upgrade* a `low`/`medium` tag if your investigation shows the blast radius is worse than
stated — say so explicitly in your report — but you never downgrade a human-set tag.

## Step 1 — verify, don't trust

Read the actual current code yourself before accepting any claim in the task description (bug
report, stack trace, prior agent's summary). Confirm or correct it explicitly in your report.

## Step 2 — classify complexity: run the gate, don't eyeball it

Once you know which files the fix needs (from Step 1's investigation), run:

```
python scripts/pipeline_triage.py --risk <the human-set tag> --files <comma-separated files>
```

This is deterministic on purpose — file-path sensitivity and file count are plain pattern
matching, not an LLM judgment call, the same reasoning as why `.cursor/rules/*.mdc` glob
matching beats LLM-mediated relevance judgment. It can only ever escalate toward
`full_pipeline`, never hand you a `fast_path` for something that should obviously be escalated
on judgment alone (e.g. it doesn't know about every possible risk — if you can see the change is
riskier than the gate thinks, escalate anyway and say why).

- **`fast_path`**: implement the fix yourself directly instead of handing off to L2/L3 — commit
  it on a branch, push the branch. Still never merge, never push to `main` (see Merge gate
  below).
- **`full_pipeline`**: stay read-only. Hand off to L2. The script's `reasons` array explains why;
  include it in your plan so L2/L3 know what triggered the full pipeline.

This script exists because of a real cost measurement: a one-file, 9-line, `risk: low` fix
(tests/conftest.py, the rate-limiter test-isolation bug) went through the full pipeline anyway
and cost ~215K tokens and over an hour of wall time, almost entirely in L3 re-running the full
test suite twice adversarially. `pipeline_triage.py --risk low --files tests/conftest.py`
correctly returns `fast_path` for that exact case — run `python -m pytest
scripts/test_pipeline_triage.py -q` if you want to see it (and other cases) verified.

## Investigating? Never block silently on a long run

If confirming a hypothesis needs a real test run and it takes more than ~1-2 minutes, don't
block on it synchronously. This happened for real: an earlier L1 run here started the full
backend suite (~20 minutes) as one blocking call and was killed by a 600s no-progress watchdog
— going quiet that long looks identical to being stuck, whether or not it is. Run it in the
background to a log file, then use a single bounded wait (a loop that polls the log and exits
the moment it detects completion, launched as one background-mode call) instead of one long
silent block. Don't swing the other way either — a repeating monitor that re-wakes your whole
context on every progress tick is its own expensive mistake (seen for real at the L2 stage,
see `L2_execution.md`); you only need ONE notification for a job with one outcome. If you can't
get a cheap enough reproduction within a reasonable budget, that's a legitimate finding — report
confidence as "probable, not confirmed" rather than either faking certainty or stalling trying to
force it.

## Step 3 — plan (standard/high-risk only)

Write a minimal plan to `.claude/plan.json`:

```json
[{"id": 1, "title": "...", "area": "...", "files": ["..."], "description": "...", "status": "planned"}]
```

Keep `description` self-contained (root cause + exact change), since L2 starts with zero memory
of this conversation. Do not plan speculative work, refactors, or anything outside the reported
problem.

## Handoff

Write the plan to disk; don't paste its full content back into whatever prompt reaches L2 — L2
reads the file itself. Keep the handoff to a pointer (file path) plus a one-paragraph summary,
not a re-statement of your full investigation.

## Merge gate

Only a human merges PRs in this repo. You may create branches, commit, and push feature
branches (never `main`) and open PRs. Never merge.
