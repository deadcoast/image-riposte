# PCUC-001 / shared publication views

2026-09-18. User authorization: "SEEK PINNACLE KNOWLEDGE IN RELEVANT METHODS VIA
RESEARCH", "Mathematics should support", "Provable Claims and Use Cases (PCUC)";
"Next: PAC-034 — clean installation qualification. FOR LATER DEVELOPMENT".
PCUC-001 is a Markdown study label, not an allocation in the frozen PACER CSVs.
See [PCUC standard](../../docs/PCUC.md).

## Research supporting the theory

The production source is `release_guard.py`, connected to OVR-026/487, historical
PAC-016 and OGM-005. PACER context confirms the earlier repair already selects
every eligible iterate and reduces steps that fail quality gates. An initial
idea to add best-iterate selection was rejected for this path after source review;
the older Lab engines have different behavior and are outside this study.

[Athalye et al., ICML 2018](https://proceedings.mlr.press/v80/athalye18b.html)
motivates optimizing over specified transformations. It does not prove our finite
views cover arbitrary public transformations or downstream tasks.
[Croce and Hein, ICML 2020](https://proceedings.mlr.press/v119/croce20b.html)
documents unreliable robustness conclusions from inadequate attack optimization
and evaluation. We retain the existing selection/refusal rules rather than infer
effectiveness from optimization success.
[PyTorch autograd.grad](https://docs.pytorch.org/docs/2.14/generated/torch.autograd.grad.html)
provides the vector-Jacobian product used below. Its
[autograd mechanics](https://docs.pytorch.org/docs/2.14/notes/autograd.html)
explain saved tensors and graph lifetime. These support an execution reformulation,
not a new defense-effectiveness claim. Research consulted 2026-09-18.

## Theory and formulation

For a fixed quantized iterate q, context j uses view v(j), feature/loss f_j and
the existing detached soft-min weight w_j. Let V_v be the implementation's view
including its surrogate derivative. The original calculation is:

```
g = sum_j w_j J[V_v(j)](q)^T grad[f_j](V_v(j)(q))
  = sum_v J[V_v](q)^T (sum_{j:v(j)=v} w_j grad[f_j](V_v(q)))
```

This is linearity of a fixed Jacobian's transpose applied to a vector sum. It
requires the same view, quantized iterate, context losses and detached weights.
The temperature is fixed during each gradient evaluation; this is not the total
derivative through the adaptive temperature. Each context is still differentiated
separately. Only its view-space adjoint is accumulated, then one view backward
runs. No dense Jacobian or ensemble of model graphs is constructed.

For B contexts and V unique views: old transform forward/backward work is B/B
per gradient pass; factored work is V/V. Model forward/backward counts stay B/B.
Graph-free scoring and reference preparation also require V view constructions.
This is an operation-count claim, not a B/V whole-engine speedup. With model cost M
and repeated transform cost T, idealized speedup is (M+B*T)/(M+V*T), bounded by
B/V and approaching 1 as model cost dominates. Copies/adjoints and synchronization
are additional costs. Reference storage and model weights remain.

## Critical self-critique and falsifiers

- Mathematical equality does not imply bitwise floating-point equality. Reordered
  sums may change a near-zero gradient's sign and a later discrete search path.
  Compare actual gradients with independent joint and sequential calculations;
  record pixel differences rather than silently claiming trajectory equivalence.
- Quantization/JPEG/resize use explicit surrogate derivatives. Finite-difference
  gradcheck of the discrete codec would test a different derivative. Validate
  the implemented computational graph, exact forward pixels and quality gates.
- Context callbacks must be deterministic for fixed input/context and must not
  mutate shared inputs or depend on global evaluation order. Shipping adapters
  use frozen models and explicit seeds; arbitrary stateful callbacks are not
  covered by equivalence. Reordering does not qualify CUDA determinism.
- A shared view graph survives while one branch graph is evaluated. Saved tensor
  memory must stay independent of branch count; measure it, and preserve prompt
  cancellation, finite-gradient rejection and no random-output fallback.
- No claim of industry leadership, real-model acceleration or stronger image
  protection follows from synthetic CPU algebra/performance experiments.

## Plan and developmental use cases

1. Preserve source and reproduce redundant transforms in the real release engine.
   `source-before.zip/json` and `before.txt/xml`: three integrated count failures;
   nine tests fail because the proposed kernel does not yet exist (not nine bugs).
   One-step runs use 36/72/144 view calls for 1/2/4 encoders; target is 12 each.
2. Implement a typed graph kernel for grouped scoring and streamed adjoints;
   expose existing mask/model feature evaluation after view construction.
3. Integrate reference preparation, scoring and gradients into `protect_release`.
   Keep branch/result ordering, quality backtracking, eligible-iterate selection,
   spatial limits, seeds and review/consent intact. Add no synthetic production model.
4. Verify independent gradient equivalence (including mixed signs and masks),
   transform counts, saved tensor lifetimes, cancellation/failure cases and optional
   branches. Benchmark legacy versus integrated source on identical synthetic inputs.
5. Run current runtime/contract/package verification; retain failures, source
   identities, actual improvement and any performance ceiling in this evidence.

## Executed evidence

The four changed/added application files are `context_graph.py`, `coupled.py`,
`release_guard.py` and the annotation of `optimizer._round_ste`. The original
Lab algorithm remains in place. Result contexts retain original ordering; progress
counts completed branches in execution order. Per-view grouping changes execution
order, subject to the pure-context assumption above. References are indexed to
their original branch positions. The new report identifies `SHARED_VIEW_STREAMED_VJP`.

`proof.json`: eight float32/float64 comparisons against an independent sequential
gradient calculation, with real JPEG/resize and masks. Maximum absolute errors
are 1.87e-9 (float32) and 5.21e-18 (float64); no gradient signs differed in these
samples. Tests separately compare a joint autograd graph. These observations do
not replace the stated tolerance or promise every future trajectory is identical.

For 1, 4 and 16 repeated JPEG contexts, logical autograd saved-tensor peak was
**66,564 bytes** and remaining saved storage after return was zero. This counts
hook-retained tensors (possibly including aliases), not unique allocator memory,
RSS, model weights, clean references or GPU memory. The asymptotic working graph
is one view plus one model; context scalar/index metadata still grows with B.

`measurements.json`: actual pre-change and integrated production engines, one
warmup and three measured runs for each engine/case, CPU single-threaded Torch,
three optimization steps, deterministic synthetic encoders, real codecs/quality.

| Case | Before median | After median | Speedup | View calls before/after |
| --- | ---: | ---: | ---: | ---: |
| 32x24, one encoder | 32.93 ms | 19.97 ms | 1.65x | 72 / 24 |
| 64x48, two encoders | 83.39 ms | 39.81 ms | 2.10x | 144 / 24 |
| 128x96, four encoders | 328.07 ms | 148.78 ms | 2.21x | 288 / 24 |
| 64x48, two encoders + inpaint/temporal | 134.78 ms | 58.89 ms | 2.29x | 192 / 24 |
| 128x96, four convolution-heavy encoders | 1,093.28 ms | 891.58 ms | 1.23x | 288 / 24 |

All five cases retained identical output pixels, selected restart/iteration and
context scores. Model call counts are unchanged. The heavier fixed convolutional
models reduce the benefit as predicted. These instrumented CPU timings are a
small sample, with no confidence interval or universal speed guarantee. CUDA is
unavailable in this environment. No pretrained weights were used.

`full-native.txt/xml` and `full-command.json`: **1,198 passed, 9 skipped**, final
source bound before/after, native Windows including real browser regressions.
Skips: five unavailable Windows symlink privileges and four POSIX terminal cases;
two dependency warnings. `focused-corrected.txt/xml`: earlier 87 passed/1 skip,
superseded by the final suite. `focused.txt` retains the initial nonexistent test
filename error; no tests ran in that attempt. `before.txt/xml` retains three real
redundant-work failures and nine not-yet-implemented kernel failures.

`contracts-final.txt` (and the preceding `contracts-first.txt`): seven external stages passed, **406 signatures / 51 leaf
modules / 61 application files**, all thirteen pre-existing negative checks.
`contracts-before-review.txt` retains missing declarations and changed-source
rejection. `raw-source-first.txt` retains 880 diagnostics including newly exposed
reference-list typing; `raw-source.txt` retains final **871 diagnostics / 36 files
(54 checked)**. Strict settings are unchanged and the new kernel has no diagnostics.
The source tree remains unclean; prior PAC-033 evidence is historical.

`package.json` binds fresh source/sdist/wheel/isolated-target bytes and exercises
the actual installed shared-view solver using an explicit synthetic encoder, plus
existing record/catalog/CLI/API/undo/combined-operation checks. This uses existing
dependencies; it does not resume shelved clean-install qualification. Native entry
checks are included in the full suite. The development manifest, source proofs,
frozen-register hashes and read-only PACER validation are bound by `verify.py`.
`package-first.txt` retains the missing `docs/PCUC.md` sdist failure. Adding that
authority document to `MANIFEST.in` repairs package contents; rebuilding and
reinstalling the isolated target verifies the final distribution.

## Reproduce and continue

```powershell
.venv/Scripts/python.exe evidence/pcuc-shared-views/prove.py
.venv/Scripts/python.exe evidence/pcuc-shared-views/measure.py
.venv/Scripts/python.exe evidence/pcuc-shared-views/verify_package.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py --source
.venv/Scripts/python.exe evidence/pcuc-shared-views/verify.py
```

The raw-source audit intentionally exits 1. Package verification needs the fresh
`.tmp/pcuc-shared-views/dist` and isolated installed target. `run_full.py` uses an
external temporary directory and needs native browser permissions. `verify.py`
checks retained identities; it does not rerun the suite. Its `--inventory` mode
only writes a deferred registration plan and intentionally reports frozen drift.

Next research question: can a preregistered held-out misuse-task evaluation show
that component shifts predict reduced useful unauthorized reuse? Define endpoints,
matched controls, model identities and rejection criteria before any outcome is
seen. No outcome is claimed here. PAC-034 remains shelved; the release milestone
and coordinated register reconciliation remain open.
