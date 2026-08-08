# Benchmark Methodology

Use this reference when designing a performance experiment or interpreting ambiguous results.

## Tool selection

- Use a profiler to locate expensive code, not to produce benchmark timings. Python documents that
  profiling adds execution overhead and can distort comparisons, especially between Python and C:
  <https://docs.python.org/3/library/profile.html>.
- Use `timeit` for narrow snippets. It repeats measurements, excludes setup, and disables garbage
  collection by default; re-enable GC when collection belongs to the workload:
  <https://docs.python.org/3/library/timeit.html>.
- Default to this repository's `pytest-benchmark` workflow for decision-grade Python work. Run it
  through `uv run pytest`, record warmups and repeated rounds, and pass a unique
  `--benchmark-json` path for every run so the raw result and environment metadata remain
  reproducible: <https://pytest-benchmark.readthedocs.io/en/latest/usage.html>.
- Prefer representative application workloads over synthetic kernels for end-to-end claims. The
  Python `pyperformance` suite follows this principle and uses pinned environments:
  <https://pyperformance.readthedocs.io/usage.html>.

## Control and inspect noise

- Keep the system idle and record CPU topology, frequency behavior, power mode, temperature,
  competing work, and runtime/dependency versions. Use CPU affinity or isolation where practical.
- Do not run official timings while CPU-heavy subagents or unrelated checks are active. Keep
  baseline and candidate checkout paths and environments equivalent; the DIWire campaign found
  both scheduler stalls and unequal path lengths capable of contaminating short measurements.
- Inspect the retained `pytest-benchmark` JSON artifacts for stability, raw values, distributions,
  warmups, outliers, and environment metadata before summarizing.
- Repeat and alternate or randomize baseline/candidate order to reduce system-drift bias. Google
  Benchmark supports repetitions, warmups, aggregates, and randomized interleaving:
  <https://google.github.io/benchmark/user_guide.html>.
- Do not assume warmup reaches a steady state, especially for JIT runtimes; inspect time-series
  behavior: <https://eprints.lancs.ac.uk/id/eprint/85932/>.

## Make decisions

- Use both uncertainty evidence and a predeclared practical effect size. Compare saved
  `pytest-benchmark` runs, but do not confuse statistical significance with a useful effect:
  <https://pytest-benchmark.readthedocs.io/en/latest/comparing.html>.
- Treat a suite geometric mean as a summary, not a substitute for inspecting individual protected
  workloads.
- Observe the system while a steady benchmark runs and verify the test measures the intended
  limiter. Brendan Gregg's active-benchmarking checklist emphasizes reproducibility, errors,
  physical plausibility, and explaining the actual bottleneck:
  <https://www.brendangregg.com/activebenchmarking.html>.
- Keep each accepted optimization as one small, independently tested commit so regressions remain
  reviewable and bisectable: <https://git-scm.com/docs/gitworkflows#_separate_changes>.

## DIWire precedent

Read [diwire-campaign-evidence.md](diwire-campaign-evidence.md) for the committed canonical report,
including protocol, paired results, accepted commits, rejected hypotheses, and quality gates.

The performance campaign merged in commit `5339011` first corrected benchmark semantics and then
retained each accepted hypothesis as a separate commit. The accepted commit bodies recorded the
environment, exact commands, raw artifacts, focused paired results, broader-suite results, and
independent semantic/measurement reviews. Apparent regressions were confirmed with focused paired
runs instead of trusting one noisy full-suite result.

The campaign retained 12 accepted performance commits plus a measurement-only baseline commit.
Across 22 preregistered hypotheses, nine candidates were explicitly rejected and never committed.
Some large local wins were rejected because the global score or a protected workload regressed,
showing that the focused result was necessary but not sufficient.

The final accepted series improved the 17-scenario geometric mean from 2,526,993 to 2,799,947 ops/s
(+10.80%) and eliminated the only miss against its competitor-margin goal. Failed candidates were
discarded as uncommitted changes in isolated candidate worktrees while their raw benchmark evidence
and rejection records were retained; the accepted branch contains no revert commits.

That campaign used project-specific five-pair confirmations, at least four paired wins, a 3%
focused-effect floor, a 2% protected-regression confirmation boundary, and a saturation stop after
three well-founded sub-threshold attempts. Treat these as DIWire precedent, not universal constants:
measure current noise and declare all thresholds before each new campaign.
