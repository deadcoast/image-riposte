# Development claims audit

**Disposition: product completion is not established.** This audit found multiple
independent implementation defects and gaps between claims and verification. It
does not establish that previous authors deliberately fabricated their results.
Application source, runtime tests, launchers and packaging configuration were not
edited. Historical evidence was retained.

Reviewed checkout: `126bd6c52af945a56e119d7387298ca36da51427`. Execution used Windows
11, Python 3.14.3 and the existing `.venv`, whose default text encoding is cp1252.
Machine-readable details and file identities are in [report.json](report.json).

## Findings requiring action

| ID | Priority / evidence | Finding and consequence | Source / repair record |
|---|---|---|---|
| D01 | High; real filesystem reproduction | A dated PNG has different `st_ctime_ns` through `fstat` and `Path.stat`. Organization reports `SOURCE_CHANGED_OUTPUT_RETAINED`; three retries leave the source and create three catalog entries. A newly saved, unmodified control completes. This is conditional, not a claim that every import fails. | `policy.py:91`, `organizer.py:139`; PAC-002 |
| D02 | High; real ASGI request and existing failing test | Browser `/` returns HTTP 500 on this Windows environment. UTF-8 HTML is read using cp1252; byte 0x81 raises `UnicodeDecodeError`. | `server.py:214`; PAC-008 |
| D03 | Medium; real ASGI job | An organization job with an unsupported text file returns `checkpoint: INCOMPLETE`, but the enclosing job says `state: done`, `phase: Complete`. Terminal workers correctly classify incomplete results as needing attention. | `server.py:135`; PAC-009 |
| D04 | High; exact JS function executed with substituted DOM collaborators | Publishing completion unconditionally replaces the workspace audit with `checkpoint: COMPLETE`. A preexisting incomplete audit becomes complete even for a blocked batch, without another audit call. This is an isolated function reproduction, not a live browser session. | `static/publish.js:73`; PAC-009 |
| D05 | Medium; real review/status/export functions, synthetic committed records | After approving a valid candidate and changing its bytes, status still reports `READY_FOR_REVIEW / ACCEPTED`. Rejecting it fails with `PUBLICATION_ARTIFACT_CHANGED`, leaving the acceptance receipt. Serving and ZIP export correctly reject the changed artifact; this is stale status and blocked revocation, not an export bypass. | `publication.py:268`, `publication.py:311`; PAC-010 |
| D06 | Medium; real authenticated ASGI requests | The same 40,015-byte JSON request is rejected with 413 when Content-Length is present but accepted with 200 when sent chunked. The advertised 32 KiB check only inspects the header. Authentication remains enforced; this is not an unauthenticated remote exploit demonstration. | `server.py:192`; PAC-011 |
| D07 | Medium; real controller/parser | `focus 3` in a six-field doctor form leaves cursor at field 1. `focus` counts page rows, while forms use a separate field list. The `down` control reaches field 2. | `terminal/app.py:31`; PAC-012 |
| D08 | Medium; source plus controlled call-order instrumentation | The publishing contract says models pass a numerical input-gradient probe before request commit. Only encoders are probed. Optional inpainting and temporal adapters are instantiated but not executed before `request.json` is written. Instrumented deliberately non-executable optional adapters reach that commit boundary. This does not test real model numerics. | `publication.py:131`, `docs/PUBLISHING.md:15`; PAC-013 |
| D09 | Low; live API read plus source | The installed package is 0.5.0, while `/api/state` reports 0.3.0. Generation reports also hardcode `application_version: 0.2.0` (source inspection only). Version evidence can therefore identify the wrong application release. | `server.py:219`, `generation.py:201`; PAC-009 |
| D10 | Medium; current suite failures/skips | Three independent test assumptions fail on Windows: a fake stat object lacks `st_ctime`; migration snapshots use backslashes while the assertion replaces slashes; a symlink test assumes creation privileges. Eight entire modules skip at collection without Torch, including publication/API tests. Passing the remaining suite cannot certify those paths. | `test_policy.py:21`, `test_v02_migration.py:31`, `test_v02_models.py:34`; PAC-014 |
| D11 | Investigate; source only | Legacy `optimizer.protect`, reachable through the encoder engine, starts with random noise, accepts finite zero gradients and returns without a positive-objective check. A differentiable constant encoder appears able to return random-start pixels. The production release guard has stronger checks. Torch is unavailable here, so this hypothesis requires a real-autograd reproduction before being called runtime-confirmed. | `optimizer.py:137`, `optimizer.py:157`, `optimizer.py:189`; PAC-013 |

The independent findings are not counted as separate defects for every failing
test. Fifteen current test failures/setup errors are consistent with the same
organizer boundary; they are not fifteen demonstrated root causes.

## What the current test result means

Command:

```powershell
.venv/Scripts/python.exe -m pytest -q --basetemp=typing/.cache/development-audit/pytest-corrected --junitxml=evidence/development-audit/full-suite-corrected.xml
```

Result: **457 passed, 10 failed, 9 setup errors, 30 skipped**. The full output and
JUnit XML are retained. Breakdown of the 19 failures/errors: six organizer-related
test failures plus nine setup failures at the organization checkpoint, one
homepage decoding failure, and three test portability/environment failures.
The organizer's observed stat mismatch explains the demonstrated reproduction;
we did not instrument every failing test to prove its precise internal cause.

The 30 skips include eight module-level Torch skips, seventeen further Torch
cases, four POSIX terminal cases and one symlink-privilege skip. Module-level
skips conceal the number of parametrized cases that would otherwise collect;
30 is not the number of untested behaviors. All 49 v0.5 revision cases passed in
this run, yet the wider suite and new probes still fail.

The first attempt used a missing parent directory for pytest's temporary path.
Its 276 setup errors were an **audit harness error**, not 276 application defects.
That output is preserved as `full-suite.txt`; use `full-suite-corrected.txt` for
the current application result.

Replay the bounded probes with:

```powershell
.venv/Scripts/python.exe scripts/audit_development.py
```

The script's zero exit code means the probes executed without a harness exception.
It does **not** mean the application passed. Read the actual observed values in
[probes.json](probes.json). Fixtures use temporary directories under
`typing/.cache/development-audit`; no user artwork or models are used.

## Claims checked across the admitted scope

| Domain | Evidence examined or executed | Supported boundary / unresolved work |
|---|---|---|
| Sanitation and storage | `sanitize`, `policy`, `store`, `organizer`; full suite; repeated dated-file imports | 26 sanitation cases pass; real PNG audit and date-only ZIP controls pass. Organizer retry/idempotence is defective. No hostile filesystem-race or forensic-erasure claim is established. |
| Publishing lifecycle | Plan, model setup, task commit, status, review, resume checks, serving and pack source; synthetic exact-byte review/ZIP probe | Candidate corruption is blocked at serving/packing. Status and rejection have the separate defect above. No real-model publishing run occurred. |
| Models and optimization | `models`, `runtime_probe`, `optimizer`, `coupled`, `release_guard`, `temporal`, `qualification`, `generation`, `benchmark`; optional-loader instrumentation | Source distinguishes proxy metrics from effectiveness. Optional pre-commit probing is incomplete; old optimizer zero-gradient behavior remains a runtime hypothesis. No pretrained/CUDA/MPS/full-video result was produced. |
| API and browser | Server and JS flows; existing server tests; authenticated ASGI requests; isolated JS callback | Homepage, body bound, job state and audit badge defects reproduced. Full DOM/browser, real TCP listener and external origin environments were not rerun. |
| CLI and terminal | CLI/service/controller, operation lifecycle, keyboard/line input and relevant tests | 120 terminal-core and 49 revision cases pass; line-form focus fails. Native Windows console, desktop viewer and actual POSIX terminal behavior were not tested in this audit. |
| Packaging and launchers | `pyproject.toml`, launchers, offline sdist-to-wheel build, isolated target install, imports and byte comparison | All 47 application files agree in source, sdist, wheel and installed target. Dependencies were reused from `.venv`; clean-machine bootstrap and Python 3.11 compatibility were not established. |
| Tests and historical evidence | Current full suite, test substitutions, old test logs, package equality manifest, browser QA scripts | Historical logs contain 667-pass source/wheel results, with synthetic/native limitations documented. Ten historical package hashes differ from current files; those old results do not validate this checkout. Test counts are not feature coverage. |
| Roadmap and PACER completion | `DEVELOPMENT-SPEC`, `WAVE-03-HANDOFF`, `WAVE-04`, `VALIDATION`, current PACER registers and prior completion audit | Native/pretrained qualification, artist judgments, actual platform derivatives and modern text-conditioned/video efficacy remain pending or partial in the documents themselves. Narrow completed tasks cannot establish the whole roadmap is complete. PAC-015 retains the missing qualification scope. |

Packaging commands, hashes and import locations are in
[packaging.json](packaging.json). The target install used `uv pip install` on the
local wheel with `--no-deps`; it did not invoke pip or alter project dependencies.

The browser QA script uses Chromium with an in-process FastAPI transport and a
synthetic model oracle. Historical reports label those substitutions. They can
support the paths they exercise, but cannot establish native HTTP/browser
integration or pretrained-model quality. Likewise, mocked Windows keys do not
prove native Windows console operation.

The prior [completion audit](../completion-audit.json) retains separate raw-source
mypy and external-contract results. Its 962 source diagnostics and 232 missing
symbol records were not re-counted here; source identity was checked instead.
Contract/signature success must not be read as proof that source bodies, numerical
models or every returned record are correct.

## Remaining work

PAC-007 is a review task for this bounded audit, not a completed product milestone.
The source repair proposals PAC-008 through PAC-014 remain open; PAC-002 already
tracks the organizer defect. PAC-015 tracks missing model/native qualification.
Existing PAC-005/PAC-006 inventory and patch-governance closure work remains open.
No repair, qualification, roadmap item or organism requirement was marked complete
by this audit. The source owner's restriction is why runtime fixes are recorded
rather than silently applied.

Unverified boundaries include full dependency/platform matrices, pretrained model
loading and gradients, GPU memory/performance, artist-approved visual quality,
adaptive attacks, real platform transforms, actual native terminal lifecycle and
exhaustive malformed-state/crash recovery. This report is a broader reproducible
audit, not a claim to have found every defect.
