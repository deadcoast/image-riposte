# PCUC-004: committed reviewer panels and exact agreement diagnostics

Status: bounded implementation verified, 2026-09-19. PAC-034 remains shelved; all four PACER CSVs
remain frozen. This is the INFERRED implementation scope of the user's continuing
PCUC development authorization, not a new claim of model or rubric qualification.

Research -> theory -> formulation -> critique -> implementation:

- OBSERVED: experiment reviews have no reviewer assignment or cross-reviewer
  agreement analysis. A first complete review can score a cohort without any
  measurement of whether the task rubric produces consistent decisions.
- [Artstein and Poesio (2008), sections 2-3 and 5](https://aclanthology.org/J08-4004.pdf)
  distinguish observed agreement from chance-corrected coefficients and explain
  their dependence on coder marginals and category prevalence. Agreement does not
  establish validity. We retain raw contingency tables and individual pairwise
  Cohen coefficients as diagnostics, without averaging coefficients or imposing
  a universal acceptance threshold.
- [GRRAS (2011) checklist](https://www.equator-network.org/wp-content/uploads/2012/12/GRRAS-checklist-for-reporting-of-studies-of-reliability-and-agreement.pdf)
  motivates explicit subjects, raters, measurement procedures and analysis. This
  software does not establish GRRAS compliance or independently recruit raters.
- INFERRED design: freeze an explicit set of completed experiments, one task,
  task-specific candidate rubric, 2-8 reviewer slots and per-reviewer opaque
  assignments before exporting packets. Each slot submits once, including any
  uncertainty; corrections require a new panel. Preserve every selected item and
  every absent response. Calibration never replaces an experiment/cohort score.

For N items and R reviewers, retain denominator D=N*R*(R-1)/2. On item i, y yes,
n no and u missing decisions satisfy y+n+u=R. Completing k missing decisions as
yes gives f(k)=C(y+k,2)+C(R-y-k,2), 0<=k<=u. This convex integer quadratic reaches
its maximum at an endpoint and minimum at the feasible integer nearest R/2-y.
Thus [sum min f / D, sum max f / D] are attainable, exact finite-panel completion
bounds. With three unobserved binary reviewers, the lower bound is 1/3, not zero:
at least two must agree. This is a deterministic combinatorial result, not a
confidence interval. Independent completion per item makes the summed bounds tight.

For a fully observed reviewer pair, with 2x2 counts a,b,c,d and total N,
Po=(a+d)/N, Pe=((a+b)(a+c)+(c+d)(b+d))/N^2 and kappa=(Po-Pe)/(1-Pe).
If Pe=1, kappa is undefined, even with perfect raw agreement. With any missing
pair decision, kappa is withheld instead of deleting that item from the panel.

Critical limits: agreement can be high when everyone is wrong. Correlated outputs
from the same artwork are not independent observations; no confidence intervals,
p-values, population reliability or efficacy verdict follows. Opaque slots and
randomized presentation do not authenticate people, establish actual viewing or
prevent operator unblinding/history rewriting. Built-in anchors are unvalidated
candidates; custom rubric wording has the same unvalidated status. Calibration
selection may be outcome-informed and never becomes independent preregistration.

Phases: exact arithmetic and exhaustive counterexamples; immutable artifact-bound
panel/packet/response workflow; shared service and CLI; affected-path/native and
distribution verification; source-derived contracts and preserved evidence.

Executed evidence:

- `source-before.zip` and `source-before.json` preserve all 63 preceding application
  files. Three feature-availability checks failed before implementation; their
  exact command/output are retained. These establish missing entry points, not
  an earlier mathematical malfunction. The first integrated focused run passed
  75 tests. Further packet interruption/orphan, multiple-run and shared-root checks
  are included in the final full suite.
- `prove.py` passed 9,837 single-item patterns and all 87,376 binary completions
  for 2-8 raters; 729 two-item patterns and 4,096 completions; and 1,024 complete
  Cohen cases with an independent cross-item enumeration of expected agreement.
- Final `run_full.py`: **1,286 passed, 9 skipped, 2 dependency warnings**. The same
  count passed before two local variable-name typing corrections; both source-bound
  runs remain. `full-command.json` binds the final suite to unchanged final source.
- All seven external-contract stages pass: **464 signatures, 55 leaf modules,
  65 application files**, preserving all 13 negative-consumer checks. Initial
  missing-stub/source-drift rejection is retained. The separate raw audit first
  reported 779 errors, including seven caused by reused local variable names;
  after correction it reports **772 errors in 36 files, 58 checked**, still FAIL.
  The new modules have no source-body diagnostics. No strict setting, allowlist,
  dependency, lockfile, Any or ignore was added to hide debt.
- Fresh offline build and no-dependency installation into an isolated local target
  pass. `verify_package.py` proves equality of all 65 source/sdist/wheel/installed
  application files and selected shipped docs/launchers. Both actual imports execute
  panel creation, packets, final responses and agreement through CLI/shared service,
  plus prior cohort/experiment/solver/sort/recovery operations, with synthetic models
  and synthetic ratings. Its first elevated-context wheel read failed with
  PermissionError; the same verification passed under the builder's sandbox identity.
  No permission changes or test reductions were used. See `package-first-failure.txt`.
- PACER structural validation remains valid. The four CSVs match their frozen
  hashes; deferred inventory/guarded-operation proposals remain unapplied.

Production integration is in `agreement.py`, `review_panel.py`, shared request
records, service dispatch and four CLI commands. Each validation pass loads each
selected generation report once; item-to-run joins are indexed. Export rechecks
frame/reference bytes while streaming them into the packet. Statistics
cost O(N*R^2), with N<=320 and 2<=R<=8; completion bounds themselves cost O(N*R).
Packet creation streams one PNG at a time and preserves all sequence frames,
date-only PNGs and fixed ZIP dates. Failure before final export cleans temporary
bytes; an orphan final ZIP without its receipt fails closed and remains recoverable
as retained evidence. Already committed reviewer responses cannot be overwritten.

Reproduce with the existing environments (temporary test artwork must stay outside
application roots):

```powershell
.venv/Scripts/python.exe evidence/pcuc-review-panels/prove.py
.venv/Scripts/python.exe evidence/pcuc-review-panels/run_full.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py --source
.venv/Scripts/python.exe evidence/pcuc-review-panels/verify_package.py
.venv/Scripts/python.exe evidence/pcuc-review-panels/verify.py
```

The last command checks retained identity; it does not rerun tests. Rerunning proof,
tests or builds can change evidence identity and requires reviewing fresh results
before recording a new acceptance. Prior study verifiers continue to reject later
source drift; their historical acceptance files were not rewritten.

No real people rated a panel, no task rubric was empirically validated, and no
pretrained generator was evaluated. Current Torch is CPU-only; CUDA is unavailable.
Next research/qualification requires independently selected modern generator
families/artworks and separate reviewers on an available CUDA environment. Keep
these unavailable gates separate from the completed local tool implementation.
