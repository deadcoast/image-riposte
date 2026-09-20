# RIPOSTE / current project status

Reviewed 2026-09-19. **Version 0.5.0; development audit open; release milestone pending.**
The working list, correction and resumption checkpoint are in
[todo-audit.PACER.md](../todo-audit.PACER.md). The four PACER CSVs remain frozen
until that work is complete and the specification can be reconciled together.
PAC-029 through PAC-033 have bounded implementation acceptance in the Markdown audit. PAC-028
was the preceding identification audit. Remaining findings and CSV reconciliation
are open.

The user has shelved PAC-034 and directed research-led development under
[Provable Claims and Use Cases](PCUC.md). PCUC-001 now integrates shared-view
gradients into the production publishing engine. Its mathematical/CPU evidence
establishes reduced transform work, not protection efficacy or industry leadership.
PCUC-002 adds local experiment precommitment, concealed-label review packets and
append-only endpoint ratings. Its matched-control contrast is descriptive;
real-model task outcomes and independent preregistration remain unqualified.
PCUC-003 integrates prospective artwork cohorts with a fixed selected-member
denominator, primary-review order and finite-sample missingness bounds. Failed
members cannot disappear into an aggregate of only completed outcomes.
PCUC-004 adds fixed reviewer calibration panels with task-specific candidate
rubrics, separate packet assignments, one final response per slot, exact binary
agreement completion bounds and pairwise Cohen diagnostics. Actual reviewer
independence, rubric validity and modern-family effectiveness remain unqualified.
PCUC-005 integrates a fixed local Kontext editing backend. Model-aware preparation
and conditioning propagate into experiments, cohorts and review packets. The real
library numerical path passes with tiny random CPU models and test-only device
overrides; pretrained CUDA/bfloat16 execution and useful editing remain unqualified.

## Version, configuration and entry points

| Surface | Observed current state |
| --- | --- |
| `pyproject.toml`, `src/riposte/__init__.py`, `uv.lock` | 0.5.0 |
| Existing local installation | Editable 0.5.0 from this checkout; Windows Python 3.14.3 |
| Runtime declaration | Python >=3.11; minimum-version/native platform qualification remains PAC-034 |
| `INSTALL.ps1`, `INSTALL.sh` | Explicit setup; uv frozen/inexact editable install; optional Lab dependencies; no model weights |
| `START.ps1`, `START.cmd`, `START.sh` | Verify local installation, then menu; optional browser; no dependency installation |
| `riposte.cmd` | Direct local Python command forwarding; requires INSTALL first |
| Root/isolated typing configurations | Strict source audit is separate from external contracts; both target Python 3.13 |
| Root release manifest | Current development source/configuration/launcher/document snapshot; not a built-release certificate |
| Archives and old acceptance artifacts | Historical; never substituted for current build/qualification evidence |

An offline `uv sync --locked --offline --inexact --dry-run --cache-dir .tmp/uv-cache`
resolved the lock and proposed refreshing only the editable project. No installation
was performed by that check. Keep the existing uv environments and lockfiles.
Use [REBUILD.md](REBUILD.md) for explicit install, launch, test and build commands.

The previous root manifest described 0.4.0: 98 entries matched, 52 differed,
one path was missing and one historical wheel could not be read in this environment.
Its exact bytes are retained at
[history/v0.4.0/RELEASE-MANIFEST.json](../history/v0.4.0/RELEASE-MANIFEST.json).
The new root manifest covers its declared development inputs only. It does not
certify every historical distribution, test artifact, model or native interface.

## Current operation and privacy contracts

- Sort, RIPOSTE and Sort + RIPOSTE are independent choices. Startup, location
  selection and previews do not grant operation consent. The normal menu has nine
  actions; Workshop is optional. See [README](../README.md) and [CLI](CLI.md).
- Generated images and public publishing packs contain audited date-only PNGs.
  Private recovery history intentionally retains original bytes, metadata, names
  and timestamps. Private category provenance lives in `sort_titles` and recovery
  journals. These are separate from public catalog/export contents.
- Videos are sort-only and byte-preserved, including their metadata; optional
  `ffprobe` is required to inspect them. They do not enter protection processing.
- CLI, terminal and API reject workspaces overlapping the loaded application,
  including previews. Source checkouts protect their RIPOSTE project root; wheels
  protect the loaded package directory. Independent siblings are allowed, and
  links/junctions remain rejected before canonical overlap comparison.
- Ordinary and category sorting require exact preview IDs. Combined sorting
  requires its top-level ID binding sorting and protection choices. Files and
  destinations are frozen; drift requires renewed preview. Current operations use an OS lease on the
  persistent empty root file `.riposte-operation.lease`. A killed current worker's
  matching marker can be recovered only after acquiring that lease. Explicit undo
  retains its preview and integrity checks. Unknown legacy locks remain blocked;
  neither a PID nor age proves ownership. Keep the lease file in place.
- Visual acceptance, synthetic model regression checks and measured protection
  efficacy remain separate. Installed Torch/Diffusers/Transformers do not establish
  qualification of any real model or native platform.
- Image lookup uses the existing primary-key index and validates the selected
  file. Sorting and audits use operation-local title maps and catalog revision
  checks. External database changes invalidate the operation; no consent cache
  persists between operations. Whole-workspace auditing still checks every file.

## Evidence and its limits

| Evidence | Result and boundary |
| --- | --- |
| Windows full suite | 1,311 passed, 9 platform skips outside sandbox; three dependency warnings; source-bound Kontext, panel, cohort, experiment, browser and publication regressions |
| Focused initial typing verification | 254 passed, 1 Windows symlink-privilege skip before final consumer/controller annotations; final source is covered by the full suite |
| Historical PAC-032 scaling measurements | At 16/32/64 cataloged images, returned audit rows are 32/64/128, all-ID lookup rows 16/32/64, and sorting rows 128/256/512; current full suite retains the row-budget regressions |
| Historical PAC-029 POSIX lease probe | Passed on existing Ubuntu WSL Python 3.12.3: live exclusion, process death, persistent identity, adjacent state rename; low-level lease only |
| Fresh external contract suite | All seven stages passed; 473 signatures, 56 importable leaf modules, 66 application files match reviewed identity; all 13 existing negative checks retained |
| Fresh source-body audit | 772 diagnostics in 36 files, 59 Python files checked; still failing with unchanged strict settings; Kontext, agreement, panel, experiment and cohort modules have no diagnostics |
| Historical PAC-033 source-consumer checks | Positive consumers passed and nine invalid uses failed at exact lines/codes against the then-current source |
| PCUC gradient and memory checks | Eight independent sequential-VJP comparisons pass; maximum float32 absolute error 1.87e-9; logical saved-tensor peak 66,564 bytes for 1/4/16 repeated contexts, zero retained after return |
| PCUC paired engine runs | Five synthetic CPU cases retain identical pixels/selection/scores; 1.23x–2.29x median speedup, including the convolution-heavy case; model call counts unchanged, no CUDA available |
| PCUC experiment workflow | Protocol-before-generation, retained failures, blinded-label packets, append-only ratings, exhaustive binary contrast, drift rejection and loader binding exercised using synthetic model outputs; not a real protection experiment |
| PCUC cohort workflow | 216 bounded sample states and 343 extreme completions verify exact bounds; prospective draw, shared loader, missing members, fixed denominators and primary-review ordering tested with synthetic generators |
| PCUC panel mathematics | 9,837 patterns and 87,376 completions plus 729 two-item patterns, 4,096 completions and 1,024 Cohen cases; exact descriptive arithmetic, no real-rater reliability evidence |
| PCUC Kontext path | 4,115 exact aspect selections and 17 lattice/area checks; real tiny random VAE/CLIP/T5/flow-transformer serialization and CPU execution preserve paired repeatability, context-token geometry and input sensitivity; no pretrained/native CUDA/bfloat16 qualification |
| Fresh distributions and isolated target | All 66 application files match source/sdist/wheel/installed target; fixed Kontext loader/conditioning/packet and prior panel/cohort/experiment/solver/workflow guards checked with synthetic models; existing Windows dependencies, not clean bootstrap |
| Real Windows entry points | Existing editable wrapper reports 0.5.0; PowerShell START opens the linear menu and exits on q with no stderr |
| Prior review's entry/probe checks | 29 launcher/menu tests and real Windows entry checks passed; five then-open observations reproduced before PAC-029 implementation |
| PACER structural validation | Valid; stale source/document evidence and missing new source registrations remain deferred under the CSV freeze |

Current development evidence: [PCUC Kontext backend](../evidence/pcuc-kontext/README.md).
Prior reviewer stage: [PCUC reviewer panels](../evidence/pcuc-review-panels/README.md).
Prior cohort stage: [PCUC cohorts](../evidence/pcuc-cohorts/README.md).
Prior experiment stage: [PCUC experiments](../evidence/pcuc-experiments/README.md).
Prior engine study: [PCUC shared views](../evidence/pcuc-shared-views/README.md).
Prior repair evidence: [source typing](../evidence/source-typing/README.md).
Prior repairs: [catalog scaling](../evidence/catalog-scaling/README.md),
[preview binding](../evidence/sort-preview/README.md),
[application roots](../evidence/application-roots/README.md) and
[workspace lease](../evidence/workspace-lease/README.md).
Historical review baseline: [milestone reconciliation evidence](../evidence/milestone-reconciliation-2026-09-18/review.json).
Earlier implementation evidence: [category sorting](../evidence/category-sort/README.md),
[sort recovery](../evidence/sort-recovery/README.md), and
[typing](../typing/README.md). PAC-033 changes fourteen application files, including
the new shared records module. Earlier repairs and their
evidence remain preserved. All four CSV hashes
remain unchanged. Version, dependency lockfiles, installer and launcher code remain
0.5.0-compatible; no dependencies or model weights were added.

The current validation report and deferred source/symbol plan are retained with
the repair evidence. No CSV requirement acceptance was refreshed during the freeze. They
must be evaluated and reconciled with the other open evidence at the milestone;
structural validity does not mean evidence freshness or product completion.

## Documentation authority and milestone

Current source defines implemented behavior. README, CLI, UX-CONTRACT and this
status page describe the current checkout. DEVELOPMENT-SPEC, WAVE-04, VALIDATION
and the older threat-model text retain their historical scopes; their earlier
blanket ban on original retention is superseded by explicit private undo history.
The selective 0.5 merge record is historical evidence for that merge, not a current
whole-product acceptance report. See [CHANGELOG.md](CHANGELOG.md) for later work.

The milestone requires completed Markdown acceptance, coordinated guarded PACER
reconciliation, consistent release identity, fresh distribution equality/install
checks, launcher/configuration verification and explicit qualification limits.
It remains open. PAC-034 (clean installation qualification) is shelved by the user.
The next PCUC research phase is a preregistered, held-out misuse-task evaluation
protocol that can test whether component proxies predict useful protection.
It requires explicit model/task identities and cannot inherit synthetic speed results.
Remaining source typing debt stays visible for further scoped work. No tag, new
release number or product-complete claim is made by this bounded repair.
