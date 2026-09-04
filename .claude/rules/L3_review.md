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
  "wait" does not mean one silent blocking call. Run it in the background to a log file and check
  the file periodically with short, distinct commands, the same reasoning as `L2_execution.md`'s
  "never block silently" rule: a stage that goes quiet for 10+ minutes gets killed by a
  no-progress watchdog whether or not it's actually stuck, so waiting has to stay visible.
- If you truly cannot wait (hard time/turn budget), do not present that as a finished review.
  Return verdict `INCOMPLETE`, state exactly what ran to completion and what didn't, and hand
  back whatever partial evidence you have — so the orchestrator knows to verify directly rather
  than trust an implied pass.

## Re-run broader than the plan's own scope

Whenever it's feasible, re-run the full relevant test suite yourself — not just the tests L1/L2
focused on. A narrow-scope fix can pass its own targeted tests while still regressing something
else; that's exactly the kind of thing L3 exists to catch, and a plan/execution stage narrowly
focused on one bug has no reason to have checked it.

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
