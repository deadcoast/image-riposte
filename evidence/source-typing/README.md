# PAC-033 / bounded raw-source typing reduction

2026-09-18. User-authorized development: "CONTINUE   Next: PAC-033 — raw-source typing debt."
The complete PACER task calls for a declared module/error-class reduction, starting
with shared request/result records and mutation boundaries. It does not require
or establish a clean source-wide audit. The working checkpoint is
[todo-audit.PACER.md](../../todo-audit.PACER.md); all four registers remain frozen.

## Implemented scope

`src/riposte/records.py` defines source-derived request options, progress events,
PNG/image results, catalog rows, media inspection records and selection/sort
options. The service, worker and controller expose their concrete input/return
contracts. Catalog producers and sorting, undo and publication consumers retain
the existing record values and validation. External declarations re-export the
shared records instead of keeping duplicate definitions. Fourteen application
files changed relative to PAC-032; public parameter names/defaults are retained.

An operation result remains an opaque `object` at the worker boundary; legacy
service aggregation still has its pre-existing dynamic result annotation. Request
options form a broad per-command record, not a discriminated union proving every
command/option combination. Callback consumers accept read-only mappings while
the external producer contracts retain their stricter progress-event record.
This work does not claim that every dynamic producer has been schema-validated.

Typed dictionaries remain ordinary dictionaries at runtime, and casts add no
validation. Producer checks and caller-established page/workspace/editor
invariants support the localized casts. See the
[Python typing reference](https://docs.python.org/3/library/typing.html#typing.TypedDict)
and [mypy TypedDict documentation](https://mypy.readthedocs.io/en/stable/typed_dict.html).
The installed/source package probe checks independent request default dictionaries
and the real required/optional image-record keys.

## Reproduced reduction

All audits use the existing strict `typing/mypy-source.ini`, Python 3.13 checker
target and installed Windows Python 3.14.3 environment; no dependency, lockfile or
checker-setting changes. `baseline-command.json` binds the fresh failing baseline
to the exact application bytes preserved in `source-before.zip`.

| Scope | Before | After | Reduction |
| --- | ---: | ---: | ---: |
| All diagnostics | 1,100 | 876 | 224 |
| Files with diagnostics | 37 | 36 | 1 |
| Python files checked | 52 | 53 | New records module |
| Controller | 197 | 25 | 172 |
| Service | 39 | 9 | 30 |
| Worker jobs | 7 | 0 | 7 |
| Organizer | 17 | 13 | 4 |
| Terminal app, through typed callees | 19 | 15 | 4 |
| Store | 6 | 3 | 3 |
| Publication | 96 | 94 | 2 |
| Sanitize | 5 | 4 | 1 |
| Terminal output, through typed callees | 26 | 25 | 1 |

| Error class | Before | After |
| --- | ---: | ---: |
| `no-untyped-call` | 605 | 467 |
| `no-untyped-def` | 317 | 272 |
| `type-arg` | 66 | 55 |
| `union-attr` | 27 | 2 |
| `assignment` | 7 | 4 |
| `arg-type` | 11 | 10 |
| `no-any-return` | 9 | 7 |

Every other class count is unchanged; no module/error-class pair increases.
`analyze.py` verifies this comparison and records it in `analysis.json`.
The 876 remaining diagnostics include reports (155), CLI (123), publication (94),
rendering (91), server (67) and controller (25). Counts describe checker findings,
not demonstrated runtime bugs.

## Behavior review and runtime evidence

`reviewed-source.diff` preserves the normalized diff of the thirteen existing
files; `records.py` is the one new application file. `analyze.py` rejects new
application `Any` references, ignores or deleted definitions. Removing annotations,
imports and casts for review identifies four function-body differences:

- `sort_history._check`: compare the same row through a read-only mapping alias.
- `Controller._key`: use a distinct local name for report choices; call then
  return `None` in two branches whose existing callees return `None`.
- `service.execute`: spell out preview/apply branches with the same policy and
  options; explicitly test a missing destination before the existing hash check.
- `service.image_selection`: spell out the same year/month/size filter fields.

The request default factory becomes the all-optional record constructor, still
producing independent empty dictionaries. AST comparison is a review aid, not
semantic proof. Runtime checks cover real behavior:

- `full-native.txt/xml`: **1,180 passed, 9 skipped**, final application source,
  outside the sandbox. Five Windows symlink-privilege and four POSIX terminal
  skips; two dependency warnings and a pytest cache warning remain. Native browser
  regressions, application-root/lease safeguards, preview consent, videos,
  catalog row budgets, collision/recovery and exact undo are included.
- `focused-first.txt/xml`: 254 passed/1 skip on the initial record changes. This
  predates final controller/consumer annotations and is superseded by the full run.
- `contracts-final.txt` and `typing/evidence/verification.json`: all seven external
  stages pass, **402 signatures / 50 leaf modules / 60 application files**, with
  all thirteen existing invalid-consumer checks retained. Source identity was
  reviewed before updating the snapshot. External success is not source cleanliness.
- `consumers.py.txt`, `rejected.py.txt`, `check_consumers.py`: real-source positive
  consumers produce zero errors; nine invalid keys/values/callback/results fail
  at exact lines and codes. Source files are explicit inputs with normal import
  following: the full output has **885 errors = 876 source + 9 intentional fixture
  errors**, across 55 checked files. The harness passes while mypy exits 1.
- `package.json`: all 60 application files match source, fresh sdist, wheel and
  isolated target. Real record defaults/keys, catalog lookup/revision guards/audit,
  CLI/API/service preview/apply/exact undo and combined receipt/model gates pass
  from both source and installed imports.
- `entries.json` and `start-transcript.txt`: actual Windows wrapper version and
  PowerShell linear menu with explicit q-exit pass using the existing installation.

## Preserved failures and limits

`baseline.txt` retains 1,100 errors. `source-first.txt` retains 1,095 after initial
record propagation; `source-second.txt` retains 890, including newly exposed
record-inference/controller edges subsequently repaired. `source-third.txt` and
its source-bound command record are the final **876-error failure**, also retained
as `typing/evidence/source-current.txt`. `contracts-before-review.txt` retains
the expected rejection of changed source and the initially missing records stub.
`contracts-first.txt` preserves the earlier passing contract run.
The captured uv command adds its environment-selection warning before the raw
checker output; the verifier compares every remaining output line exactly.

`consumers-imports-only.txt/json` preserves the first probe, which checked fixture
compatibility but did not report imported bodies. It is superseded by the explicit
whole-source consumer run, without changing mypy settings or suppressing errors.
`before-typing/` retains the preceding PAC-032 evidence; its source identity is
historical. Prior task verifiers intentionally reject later source drift.

This is existing-dependency Windows regression and packaging evidence, not clean
bootstrap, Python-minimum/native Linux/macOS qualification, real-model efficacy,
or release completion. PAC-034 is next. Raw-source debt remains open.
Read-only PACER validation is structurally valid and retains eleven stale evidence
records. `deferred-inventory.json` intentionally reports missing/stale registrations
under the freeze, with unchanged application source and recorded passing contracts.
`deferred-operations.json` is a plan only; no guarded mutation has been submitted.

## Reproduction

```powershell
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py --source
uv run --no-sync --locked --cache-dir .tmp/uv-cache python evidence/source-typing/check_consumers.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv run --no-sync --locked --cache-dir .tmp/uv-cache python evidence/source-typing/analyze.py
uv run --no-sync --locked --cache-dir .tmp/uv-cache python evidence/source-typing/verify_package.py
uv run --no-sync --locked --cache-dir .tmp/uv-cache python evidence/source-typing/check_entries.py
uv run --no-sync --locked --cache-dir .tmp/uv-cache python evidence/source-typing/verify.py
```

The source audit intentionally exits 1. Package verification requires the fresh
artifacts/isolated target under `.tmp/source-typing`; use the existing environment
and the build workflow in [REBUILD](../../docs/REBUILD.md). Native full pytest needs
an existing writable temporary parent outside application roots and native browser
permissions. `verify.py` checks retained evidence identities and scope; it does not
rerun tests or turn any unavailable qualification into a pass.
