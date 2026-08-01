---
name: optimize-performance
description: Improve software performance through falsifiable, one-change-at-a-time experiments with reproducible benchmarks, frequent green commits, independent review, and safe rollback of rejected uncommitted changes. Use when Codex must profile a hot path, design or repair a benchmark, optimize latency/throughput/memory, compare a candidate against a baseline, investigate a performance regression, or run an iterative performance campaign without compromising correctness or unrelated work.
---

# Optimize Performance

Run performance work as a sequence of controlled experiments. Retain only reproducible,
practically useful wins that preserve correctness; leave the branch green after every decision.

Read [references/benchmark-methodology.md](references/benchmark-methodology.md) when choosing a
benchmark harness, setting thresholds, diagnosing noise, or planning a decision-grade campaign.

## Establish the contract

1. Read repository instructions and inspect the worktree, benchmark suite, profiler tooling, and
   recent performance history.
2. State the user-visible goal and protected constraints: correctness, public API, concurrency,
   memory, startup, cleanup, fairness, and quality gates.
3. Define representative target workloads and broader regression workloads. Verify that each
   benchmark exercises equivalent lifecycle and setup boundaries across candidates.
4. Predeclare decision rules. Derive the minimum useful effect and regression tolerance from
   observed noise and project requirements; do not invent a universal percentage.
5. Record the exact baseline commit, executable/runtime, dependency lock fingerprint, machine,
   power/CPU state, command, dataset, benchmark parameters, and raw artifact location.
6. Declare a saturation rule, such as stopping after a fixed number of well-founded hypotheses
   fail to clear the useful-effect threshold.

If the existing benchmark is unfair or incomplete, fix and rebaseline it in a measurement-only
commit before claiming runtime improvement.

## Protect the worktree

- Start each experiment from a committed, tested checkpoint.
- Run `git status --short` and record which paths are already dirty. Treat those changes as user
  work unless proven otherwise.
- Prefer an isolated worktree when existing changes overlap the hot path or when baseline and
  candidate must be measured side by side.
- Assign one writer. Use subagents for read-only profiling, hypothesis generation, semantic
  review, and benchmark-methodology review so concurrent edits cannot contaminate an experiment.
- Finish or pause CPU-heavy subagents and unrelated processes before official timing runs.
- Never use `git reset --hard`, `git clean`, broad `git restore`, or a checkout that could erase
  unrelated changes.

## Build the baseline

1. Run focused correctness tests and the benchmark under stable conditions.
2. Save raw results with unique names; never overwrite a prior run.
3. Repeat across fresh processes when supported. Inspect warmup, distributions, outliers, and
   environment metadata before summarizing.
4. Profile a representative workload to locate the limiter. Do not use profiled timings as the
   benchmark result.
5. Confirm the suspected cost is material enough to optimize.

## Write one hypothesis

Write this card before changing code:

```text
Hypothesis: <specific mechanism causing cost>
Change: <one bounded implementation change>
Target: <benchmark and expected direction/practical magnitude>
Risks: <semantics and protected workloads that might regress>
Accept: <correctness, stability, effect, and regression conditions>
Reject: <rollback conditions>
```

Keep speculative refactors, benchmark changes, and runtime changes in separate experiments.

## Run the experiment

1. Make only the hypothesized change and add tests for any newly specialized path or invariant.
2. Run focused correctness tests first. Reject immediately on unexplained semantic or API change.
3. Run the identical focused benchmark for baseline and candidate. Alternate or randomize order
   when drift is plausible, and use sibling worktrees with equivalent path lengths, dependencies,
   and environment configuration.
4. Compare raw distributions and paired results. Require a practical effect larger than the
   predeclared threshold and observed noise; statistical significance alone is insufficient.
5. If the result is noisy or the environment changed, classify it as inconclusive, normalize the
   conditions, and rerun. Do not discard inconvenient samples selectively.
6. Run broader benchmarks. Confirm any apparent protected-workload regression with focused paired
   runs before deciding.
7. Ask independent subagents to review semantics/concurrency and benchmark fairness. Give them the
   diff and raw artifacts, not the intended verdict.

## Decide immediately

Accept only when the target win is reproducible and practically useful, protected workloads remain
within their declared tolerance, reviews find no benchmark gaming, and required tests pass.

When accepting:

1. Run formatting, linting, typing, tests, coverage, API-signature checks, and platform/runtime
   variants required by the repository.
2. Commit immediately as one logical Conventional Commit. Include the hypothesis, environment,
   exact commands, focused and broad results, regressions checked, and verification in the body.
3. Start the next hypothesis from that green checkpoint.

When rejecting:

1. Record the hypothesis, raw evidence, and rejection reason in the project experiment ledger or
   task report.
2. Identify the exact tracked files changed by this experiment and verify they were clean at its
   start.
3. Restore only those owned tracked paths from the current checkpoint. Remove only exact untracked
   artifacts created by the experiment and known to be disposable; otherwise preserve them.
4. Re-run `git status --short` and the focused correctness test to prove the checkpoint is restored.

Reject or redesign when correctness fails, the target is reproducibly slower, the win does not
clear the practical/noise threshold but adds complexity, a protected workload exceeds tolerance,
or the optimization depends on benchmark-specific behavior.

## Commit evidence template

```text
perf(<area>): <bounded improvement>

Hypothesis:
<mechanism and change>

Benchmark environment:
<runtime, machine, power state, dependencies, lock fingerprint>

Benchmark command:
<exact reproducible command and artifact paths>

Focused result:
<baseline -> candidate, effect, paired wins/stability>

Full-suite result:
<aggregate plus worst protected scenarios and confirmations>

Verification:
<tests, lint/types, coverage/API, platform variants, independent reviews>
```

## Finish the campaign

Re-run the canonical baseline and candidate suite from clean states, inspect every protected
workload rather than only an aggregate, and document retained and rejected hypotheses. Ensure the
final branch contains small independently testable commits and no transient experiment changes.
Stop when the goal is met or the predeclared saturation rule fires; do not keep adding complexity
for sub-threshold gains.
