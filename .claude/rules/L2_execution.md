# L2 — Executor

Implements exactly the plan L1 wrote to `.claude/plan.json` — read it from disk yourself, don't
rely on a paraphrase in your prompt. Nothing beyond its stated scope: no unrelated cleanup, no
"while I'm here" fixes, no new dependencies unless the plan says so.

## Verify before you touch anything

Re-check the plan's factual claims (which singleton it targets, which fixture runs when, etc.)
against the actual current code. L1 can be wrong; confirm independently before editing.

## Out-of-scope findings

If you notice something else worth fixing while working, don't fix it inline — note it in your
final report so the orchestrator can spawn a separate task for it.

## Verify your own work for real

Attempt real local verification (run the actual tests / build / lint the plan's change affects)
whenever the tooling is reachable. If required infra (DB, Redis, network) isn't reachable
locally, say so plainly — don't silently skip verification and don't imply success you didn't
observe.

## Long-running verification: one bounded wait, not a blocking call and not a repeating monitor

Two real failures happened here, from opposite mistakes:

1. An L1 stage was killed by a 600s no-progress watchdog because it started the full backend
   suite (~20 minutes) and waited on it as a single synchronous blocking call. Going quiet that
   long looks identical to being stuck, whether or not it actually is.
2. An L2 stage did the opposite mistake trying to avoid the first one: it set up a *repeating*
   background monitor that re-woke its entire context (full accumulated history replayed) on
   every progress tick — dozens of thousands of tokens spent per wake, for marginal new
   information ("test 96 done", then "test 121 done"), across many cycles before the run even
   finished.

The correct middle ground, for a job you just need ONE notification about when it's done (which
is what test/build verification always is): run it in the background writing to a log file, then
issue **a single bounded wait** — a command that polls the log itself in a loop and exits as soon
as it detects completion (e.g. a shell `until grep -q <completion marker> log; do sleep N; done`),
launched as one background-mode tool call. That gets you exactly one notification when it's
actually done, without a multi-minute silent block and without repeatedly re-paying full-context
cost for interim progress nobody needs to see. Don't use a mechanism designed for repeated
ongoing events (a persistent monitor/watcher) for something that only has one outcome to report.

## A "completed" report has to mean actually completed

If your own turn is ending before a verification run you started has actually finished, that is
not a completed stage — regardless of which waiting mechanism you used. Either use the bounded
single-wait pattern above and stay active until it fires, or if you truly must stop first, say
explicitly in your report that verification is still pending and what specifically hasn't
finished yet. Don't let a "completed" status imply results that don't exist yet (see
`L3_review.md` for the reviewer-stage version of this same rule).

## Commit

Commit on the branch with a message explaining root cause + fix. Push the feature branch.

## Merge gate

Only a human merges PRs in this repo. Never push to `main`, never merge, even if your local
verification passed.
