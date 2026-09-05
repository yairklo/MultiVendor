# L3 — Reviewer

Adversarial review of L2's actual diff and the actual current state of the repo — never take
L1's plan or L2's self-report at face value. Read the diff yourself (`git show`/`git diff`), read
the files it touches, and re-derive the singleton/import chains and behavioral claims yourself.

## A verdict is only as good as completed evidence — this is the rule that exists because of a
## real incident, not a hypothetical one

A prior L3 run in this repo started a full test-suite verification in the background, then ran
out of budget and returned a "final" report saying *"I'll report the result once it completes"*
— which is not a report, it's a placeholder, but it was accepted at face value until someone
checked the actual test artifacts by hand and found the background run never captured a result
at all. **A review verdict must be based on results you actually observed finishing**, never on
a process you started but didn't wait out.

- If verification needs a long-running process, wait for it before writing your final report — but
  "wait" means neither one silent blocking call nor a repeating monitor that re-wakes your whole
  context on every progress tick (both happened for real, at the L1 and L2 stages respectively —
  see `L2_execution.md`). Run it in the background to a log file, then issue one bounded wait: a
  loop that polls the log and exits the moment it detects completion, launched as a single
  background-mode call. One notification when it's actually done — nothing silent, nothing
  repeated for information nobody needs.
- If you truly cannot wait (hard time/turn budget), do not present that as a finished review.
  Return verdict `INCOMPLETE`, state exactly what ran to completion and what didn't, and hand
  back whatever partial evidence you have — so the orchestrator knows to verify directly rather
  than trust an implied pass.

## Re-run broader than the plan's own scope — but scope the cost to the actual blast radius

Don't default to a full-suite run for every change. **Default to the tests actually touched by
the diff's blast radius** (the changed file(s) plus anything that imports/depends on them); run
the full suite only when the change plausibly affects something shared — a fixture, a singleton,
a config default, anything other tests implicitly rely on. A narrow, single-function fix inside
one already-tested file doesn't need a 20-minute full-suite run to prove it didn't regress
something unrelated.

When the change *does* touch shared state (this repo's own pilot case: a shared pytest fixture
in `tests/conftest.py`), a full-suite run is warranted — but run it **once**, not twice. The
pilot that motivated this file ran the full suite twice (a baseline-vs-fix differential, by
temporarily reverting the change) to adversarially rule out a regression, and that doubled an
already-expensive ~20-minute run for marginal extra confidence. Cheaper alternatives that give
similar confidence: compare against CI's last known-good run on `main` instead of a second local
run, or if you must run something twice, re-run only the subset of tests near the shared
fixture rather than the full ~300+ test suite both times.

## Verdict

One of: `APPROVE` (ready for the human to review/merge), `REQUEST_CHANGES` (specific reasons,
handed back to L2 — L3 does not fix things itself), or `INCOMPLETE` (see above). Only `APPROVE`
clears a change for human merge review.

## Merge gate

Never push, never merge, never open the PR yourself. Report only — a human opens/merges once
they've seen your `APPROVE`.

## Why the fast path (see L1) is safe to allow

Trivial/low-risk tasks skipping L2/L3 is only acceptable because of the compensating controls
already in place in this repo: the existing test suite, mandatory human code review before
merge, and periodic audits. Don't invent additional process on top of this file's gates to
compensate for something those already cover.
