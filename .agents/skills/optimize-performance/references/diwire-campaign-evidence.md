# DIWire performance-goal final evidence

This committed copy preserves the canonical campaign report that was originally generated under
the ignored `benchmark-results/` tree. The artifact map records that original layout; the paired
results and decision evidence needed to evaluate the precedent are preserved below.

## Contents

- [Outcome](#outcome)
- [Canonical protocol](#canonical-protocol)
- [Competitive score](#competitive-score)
- [Original full comparison table](#original-full-comparison-table)
- [Final full comparison table](#final-full-comparison-table)
- [Final versus original paired evidence](#final-versus-original-paired-evidence)
- [Accepted performance commits](#accepted-performance-commits)
- [Rejected experiments](#rejected-experiments)
- [Remaining measured bottlenecks](#remaining-measured-bottlenecks)
- [Verification](#verification)
- [Artifact map](#artifact-map)

## Outcome

- Repository starting commit: `c33a8956c341913755e25a0beacd73babcc2ef35`.
- Fair canonical runtime baseline: `a19e95d77a1c73dfbae3fee63ebaaf3990e6c8af`.
  This commit only aligned benchmark semantics and added measurement tooling; it made no
  runtime performance claim.
- Final commit: `ab4fc5cce71ee9ac3ec764acc2768437ef25a8c1`.
- Final score clears all canonical gates: zero misses, minimum competitive ratio
  `1.211866126x`, worst original ratio `0.993554384x`, and a higher full-suite geometric
  mean.
- Geometric mean: `2,526,993.427` to `2,799,946.759` ops/s (`+10.801505%`).
- The formerly losing warmed open-generic scoped lifecycle improved from `628,733.861`
  to `913,403.443` ops/s (`+45.276642%`) and now leads Dishka by `1.211866126x`.

## Canonical protocol

- CPython `3.14.6`, GIL enabled.
- Executable:
  `/Users/maksimzayats/.local/share/uv/python/cpython-3.14.6-macos-aarch64-none/bin/python3.14`.
- Darwin `25.5.0`, arm64, Apple M3 Pro.
- AC Power; low power mode off.
- `uv.lock` SHA-256:
  `afe3a74dcf4f7882678465d881ba15d5e0b00df9ba59053eaccdcaaca396b6a2`.
- Suite SHA-256:
  `3b4dca8d0e66998e421a175dfc5cedf8b4b3d8b12dd18146333f2edb57c09f24`.
- Dishka `1.10.1`, Rodi `2.1.0`, Wireup `2.12.0`, pytest-benchmark `5.2.3`.
- Equal-length detached worktrees and separate frozen environments.
- Ten independent full-suite pairs per role, alternating original/final order.
- Headline throughput is the median of ten independent-run mean ops/s.
- All 20 unique raw JSON files and all detected outliers were retained; no selective
  reruns or exclusions were used.
- Every raw file contains all 57 expected benchmark cells and correct commit/environment
  metadata.

The generated records set `review_required` because their conservative quality policy
flags retained modified-z outliers and series with CV above 5%. Fixed medians and ten
paired observations were therefore reviewed explicitly. No final headline regression
against the original exceeds 2%; the worst is only `-0.644562%`.

## Competitive score

| Metric | Original | Final |
| --- | ---: | ---: |
| Scenarios below 1.10x | 1 | 0 |
| Minimum competitive ratio | 0.846671371x | 1.211866126x |
| Worst ratio to original | 1.000000000x | 0.993554384x |
| DIWire geometric mean | 2,526,993.427 | 2,799,946.759 |

## Original full comparison table

Values are median independent-run mean ops/s. A dash means the competitor cannot express
the scenario fairly.

| Scenario | DIWire | Dishka | Rodi | Wireup | Fastest | Ratio |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| enter_close_scope_no_resolve | 7,783,231 | 2,924,869 | 5,231,379 | 1,410,487 | Rodi | 1.488x |
| enter_close_scope_resolve_100_instance | 353,441 | 47,470 | 71,438 | 138,777 | Wireup | 2.547x |
| enter_close_scope_resolve_generator_request_try_finally | 1,838,284 | 1,266,850 | - | 699,955 | Dishka | 1.451x |
| enter_close_scope_resolve_once | 6,020,041 | 1,752,641 | 2,913,615 | 1,255,036 | Rodi | 2.066x |
| enter_close_scope_resolve_open_generic_scoped | 628,734 | 742,595 | - | - | Dishka | 0.847x |
| enter_close_scope_resolve_scoped_100 | 192,644 | 72,061 | 88,156 | 96,682 | Wireup | 1.993x |
| resolve_deep_transient_chain | 2,481,711 | 1,808,460 | 1,012,071 | 1,212,428 | Dishka | 1.372x |
| resolve_generated_scoped_grid | 124,373 | 61,101 | 45,285 | 37,103 | Dishka | 2.036x |
| resolve_mixed_lifetimes | 2,890,473 | 1,291,050 | 1,375,830 | 752,185 | Rodi | 2.101x |
| resolve_open_generic_transient | 2,088,769 | 1,371,074 | - | - | Dishka | 1.523x |
| resolve_scoped | 3,863,959 | 1,821,610 | 2,119,446 | 1,018,393 | Rodi | 1.823x |
| resolve_scoped_with_registered_open_closed_generics | 12,066,458 | 2,872,810 | - | - | Dishka | 4.200x |
| resolve_scoped_with_registered_open_closed_generics_pair_alternating | 6,726,418 | 1,493,837 | - | - | Dishka | 4.503x |
| resolve_scoped_with_registered_open_closed_generics_pair_same | 7,556,980 | 1,526,742 | - | - | Dishka | 4.950x |
| resolve_singleton | 14,400,980 | 5,742,084 | 4,119,259 | 9,773,381 | Wireup | 1.473x |
| resolve_transient | 8,960,712 | 5,054,096 | 3,831,262 | 7,048,560 | Wireup | 1.271x |
| resolve_wide_transient_graph | 3,324,624 | 2,034,766 | 1,056,577 | 1,603,947 | Dishka | 1.634x |

## Final full comparison table

| Scenario | DIWire | Dishka | Rodi | Wireup | Fastest | Ratio |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| enter_close_scope_no_resolve | 7,733,063 | 2,943,632 | 5,157,390 | 1,424,784 | Rodi | 1.499x |
| enter_close_scope_resolve_100_instance | 424,326 | 47,572 | 70,440 | 140,533 | Wireup | 3.019x |
| enter_close_scope_resolve_generator_request_try_finally | 1,947,318 | 1,265,486 | - | 702,569 | Dishka | 1.539x |
| enter_close_scope_resolve_once | 6,282,670 | 1,746,221 | 2,876,690 | 1,247,462 | Rodi | 2.184x |
| enter_close_scope_resolve_open_generic_scoped | 913,403 | 753,716 | - | - | Dishka | 1.212x |
| enter_close_scope_resolve_scoped_100 | 301,019 | 73,094 | 88,420 | 96,794 | Wireup | 3.110x |
| resolve_deep_transient_chain | 3,201,232 | 1,838,324 | 1,016,850 | 1,214,820 | Dishka | 1.741x |
| resolve_generated_scoped_grid | 149,668 | 60,742 | 44,955 | 36,364 | Dishka | 2.464x |
| resolve_mixed_lifetimes | 2,895,344 | 1,285,019 | 1,361,324 | 751,354 | Rodi | 2.127x |
| resolve_open_generic_transient | 2,191,522 | 1,376,590 | - | - | Dishka | 1.592x |
| resolve_scoped | 4,253,993 | 1,810,664 | 2,108,508 | 1,021,199 | Rodi | 2.018x |
| resolve_scoped_with_registered_open_closed_generics | 12,199,176 | 2,896,016 | - | - | Dishka | 4.212x |
| resolve_scoped_with_registered_open_closed_generics_pair_alternating | 6,741,966 | 1,489,736 | - | - | Dishka | 4.526x |
| resolve_scoped_with_registered_open_closed_generics_pair_same | 7,598,431 | 1,535,278 | - | - | Dishka | 4.949x |
| resolve_singleton | 14,552,676 | 5,756,140 | 4,113,471 | 9,906,584 | Wireup | 1.469x |
| resolve_transient | 9,023,460 | 5,162,529 | 3,862,306 | 6,972,784 | Wireup | 1.294x |
| resolve_wide_transient_graph | 3,410,447 | 2,005,772 | 1,086,539 | 1,599,375 | Dishka | 1.700x |

## Final versus original paired evidence

| Scenario | Headline change | Paired median | Wins |
| --- | ---: | ---: | ---: |
| enter_close_scope_no_resolve | -0.644562% | -0.824226% | 4/10 |
| enter_close_scope_resolve_100_instance | +20.055913% | +19.707195% | 9/10 |
| enter_close_scope_resolve_generator_request_try_finally | +5.931338% | +6.856024% | 10/10 |
| enter_close_scope_resolve_once | +4.362571% | +5.131063% | 8/10 |
| enter_close_scope_resolve_open_generic_scoped | +45.276642% | +45.711020% | 10/10 |
| enter_close_scope_resolve_scoped_100 | +56.256621% | +54.957496% | 10/10 |
| resolve_deep_transient_chain | +28.992901% | +26.716554% | 10/10 |
| resolve_generated_scoped_grid | +20.337679% | +20.349527% | 10/10 |
| resolve_mixed_lifetimes | +0.168513% | +0.517113% | 6/10 |
| resolve_open_generic_transient | +4.919334% | +5.064307% | 9/10 |
| resolve_scoped | +10.094161% | +9.836571% | 10/10 |
| resolve_scoped_with_registered_open_closed_generics | +1.099887% | +1.682915% | 7/10 |
| resolve_scoped_with_registered_open_closed_generics_pair_alternating | +0.231155% | -0.309834% | 4/10 |
| resolve_scoped_with_registered_open_closed_generics_pair_same | +0.548502% | -0.076494% | 5/10 |
| resolve_singleton | +1.053368% | +1.099168% | 6/10 |
| resolve_transient | +0.700262% | +0.987625% | 6/10 |
| resolve_wide_transient_graph | +2.581419% | +4.765203% | 9/10 |

## Accepted performance commits

| Commit | Focus | Focused before to after | Change / wins | Full-suite geometric mean change |
| --- | --- | ---: | ---: | ---: |
| `734ad2e` | Reduce child scope initialization | 658,528.643 to 716,063.726 | +8.736914%; 5/5 | +0.980389% |
| `50a3c31` | Specialize child wrapper creation | 723,725.900 to 864,698.530 | +19.478732%; 5/5 | +1.389606% |
| `6b320ac` | Inline current-scope cache hits | 121,617.022 to 135,985.974 | +11.814918%; 5/5 | +0.525923% |
| `d3334ec` | Inline bounded transient subgraphs | 2,529,144.188 to 3,083,846.758 | +21.932422%; 5/5 | +0.308153% |
| `a00e459` | Fuse bounded sync dispatch graphs | 3,198,171.606 to 3,501,919.570 | +9.497551%; 5/5 | +0.873198% |
| `b155dec` | Omit dead cache for all-cached dispatch | 347,044.483 to 426,024.398 | +22.757865%; 5/5 | +3.992309% |
| `12f5827` | Fuse bounded cached miss path | 144,249.155 to 153,796.078 | +6.618356%; 5/5 | +0.470021% |
| `108a2ff` | Fuse shallow cached misses | 4,008,053.572 to 4,349,333.491 | +8.514854%; 10/10 | +5.168696% |
| `f510725` | Inline prebound provider calls | 2,126,983.393 to 2,245,654.378 | +5.579309%; 5/5 | +0.318487% |
| `7d1bffa` | Fuse cached generator dispatch | 1,881,964.398 to 1,947,286.973 | +3.470978%; 5/5 | +0.227577% |
| `647bfa7` | Fuse warmed one-hop scope entry | 864,649.871 to 895,590.094 | +3.578353%; 5/5 | +0.090569% |
| `ab4fc5c` | Inline warmed child construction | 890,545.763 to 931,577.710 | +4.607506%; 5/5 | +0.757871% |

Each optimization is one Conventional Commit with focused repeated A/B evidence, full-suite
non-regression evidence, correctness verification, and semantic review. The separate
`a19e95d` commit is measurement-only.

## Rejected experiments

| Experiment | Hypothesis and measured conclusion |
| --- | --- |
| 006 open-generic partial | Replace one-argument materialization closure with `functools.partial`; `-0.300041%`, paired median `+0.134445%`, 3/5. Rejected as neutral/noisy. |
| 008 hot transition | Consume the warmed transition entry directly; `+1.391573%`, 5/5. Credible but below the 3% commit gate and 2% saturation threshold. |
| 011 nested cached miss | Inline one additional cached-grid layer; `+2.691026%`, 12/15. Statistically credible but below the preregistered 3% acceptance gate. |
| 016 leaf transient fusion | Fuse one-call transient leaves; `+25.843052%`, 5/5, but the lexicographic score worsened and a control regressed `-2.688346%`. Rejected. |
| 018 skip generated no-op enter | Skip marked no-op base entry; `-3.055433%`, paired median `-5.849167%`, 2/5. Rejected; saturation failure 1. |
| 019 stateless default entry | Root-only stateless entry specialization; `+14.821148%` at ten runs, but minimum competitive ratio worsened and wide transient retained `-2.901859%`. Rejected. |
| 020 direct generated base exit | Direct inactive publication for safe marked exits; `+1.935373%`, paired median `+2.477815%`, 3/5. Below fixed gates; saturation failure 2. |
| 021 generated no-owned-scope | Compile-time ownership predicate for reduced exit; `+3.674647%` headline but only 3/5 mean-throughput wins. Rejected as insufficiently credible. |
| 022 single-cleanup exit | Remove only a topology-impossible owned-resolver check; `-1.760955%`, paired median `-0.381365%`, 2/5. Rejected; saturation failure 3. |

All rejected working-tree changes were discarded. The final saturation streak reached
three well-founded failures without an acceptable, statistically credible 2% gain.

## Remaining measured bottlenecks

Post-final cProfile artifacts cover seven representative paths, exceeding the required
five-path audit.

| Path | Profile | Remaining dominant cost |
| --- | ---: | --- |
| Warm open-generic scoped lifecycle | 1,815,607 calls / 0.467s | wrapper `enter_scope` 0.123s, resolve 0.081s, generated resolve 0.050s, wrapper exit/enter 0.041s/0.035s, typing normalization 0.026s |
| Scoped cache lifecycle | 4,000,002 / 0.717s | public loop 0.410s; generated resolve/entry/exit/context entry 0.128s/0.086s/0.051s/0.042s |
| Generated scoped grid | 700,008 / 0.372s | nested generated resolver levels dominate the dependency graph |
| Deep transient chain | 1,800,002 / 0.327s | generated resolve 0.282s; five required constructors account for the remainder |
| Generator cleanup | 800,002 / 0.138s | generated exit 0.045s, resolve 0.037s, generator close 0.031s, provider body 0.023s |
| 100 scoped cache hits | 2,060,002 / 0.220s | caller loop 0.143s; two million generated resolves 0.074s |
| Simple transient | 2,000,002 / 0.289s | public generated resolve 0.192s and provider slot 0.086s |

The remaining time is concentrated in necessary generated dispatch, object construction,
typing normalization, and cleanup semantics. Experiments 018-022 tested distinct entry,
exit, ownership, and cleanup reductions; none cleared the fixed acceptance gates without
noise, regression, or semantic risk.

## Verification

- `make lint`: pass. Ruff check, Ruff format check (267 files), strict mypy (171 files).
- `make test`: `1,100 passed, 65 skipped`; 4,100 statements and 1,516 branches,
  `100.00%` coverage.
- Public API signature test on CPython 3.14.6: pass. Golden snapshot is byte-for-byte
  unchanged from `c33a8956`; SHA-256
  `762ff10a55b77ab8f1918f834cc2d34dc5fc1906a091af54cc4d1e15b7cc0416`,
  9,044 bytes.
- `make test-all-pythons`: pass on Python 3.10.19, 3.14.6, and free-threaded 3.14.6t;
  each lane reported `1,100 passed, 65 skipped` and `100.00%` coverage. The Make target
  omits its tests' Sphinx dependency from the default groups, so it was executed under a
  temporary CI-equivalent `dev` + `docs` group overlay; the overlay was removed afterward.
- Additional CI lanes:
  - Python 3.11.13: Ruff/mypy pass; 1,100 passed, 65 skipped, 100% coverage.
  - Python 3.12.12: Ruff/mypy pass; 1,100 passed, 65 skipped, 100% coverage.
  - Python 3.13.12: Ruff/mypy pass; 1,100 passed, 65 skipped, 100% coverage.
  - Python 3.15.0a6: Ruff/mypy pass; 1,036 passed, 97 expected skips.
  - Python 3.15.0a6t: GIL disabled; Ruff pass; 1,022 passed, 97 expected skips under
    CI's prescribed no-mypy/two-test-ignore policy.
  - Python 3.13.14t: the exact full lane is dependency-blocked because locked dev-only
    `msgspec 0.21.1` has no cp313t wheel and its source explicitly refuses free-threaded
    Python below 3.14. With only that package and its two direct unit modules excluded,
    GIL-disabled core verification passed Ruff, mypy on 169 files, and 1,022 tests
    (67 skipped, 5 Litestar cases deselected). Canonical 3.14t passed the complete suite.
- `uv build`: pass in the clean detached final worktree.
  - Wheel: `diwire-1.4.2.post47.dev0+ab4fc5c-py3-none-any.whl`, SHA-256
    `4996866e4a7ea8d90f154156371a4821bdbf09e425d3b5ff3ec67b33ad0fd704`.
  - Sdist: `diwire-1.4.2.post47.dev0+ab4fc5c.tar.gz`, SHA-256
    `db5ae39ef992a01938b5b072c7e57dd4812844a493eb4fe157a5811082a5f7fb`.
  - Wheel metadata: `Root-Is-Purelib: true`, `Tag: py3-none-any`,
    `Requires-Python: >=3.10`, zero `Requires-Dist` fields.
  - Wheel, sdist, and tracked repository contain zero native binaries or native-source
    extensions.
- `pyproject.toml` still declares `dependencies = []`; `pyproject.toml` and `uv.lock`
  are unchanged from the repository starting commit.
- Main worktree tracked files and index are clean at final commit `ab4fc5c` on branch
  `performace-optimizations`. The only untracked non-ignored path is the pre-existing,
  protected `diwire/` nested checkout; it was not modified, moved, staged, committed, or
  included in the sdist.
- No push, PR, branch switch/rename, history rewrite, amendment, or force operation was
  performed by the optimization agent.
- `make test-e2e-fastapi` remains intentionally reserved as the absolute final shell
  verification command for the goal. Preflight found no `docker` executable or active
  daemon: `/Applications/Docker.app` is absent, the installed `~/.docker/cli-plugins/*`
  links point into that missing application, and the remaining Unix socket is stale.
  The command has not been substituted or weakened; it must run after a Docker-compatible
  runtime is installed and started.

## Artifact map

- `protocol.json`: preregistered fixed final protocol.
- `original-record.json`: immutable generated original ledger.
- `final-record.json`: immutable generated final ledger.
- `raw/`: all 20 canonical JSON runs.
- `../profiles/post-ab4fc5c/`: final cProfile data and text reports.
- `../accepted-*.json` and `../experiment-*/acceptance-summary.json`: accepted evidence.
- `../experiment-*/record-rejected.json`: rejected experiment evidence.
