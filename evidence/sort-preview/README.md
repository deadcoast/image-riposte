# PAC-031 — ordinary and combined preview binding

The Markdown audit accepts this bounded repair. Version remains 0.5.0; the
overall audit and release milestone remain open. All four PACER CSVs are frozen.

Ordinary previews include per-file source identity/hash, intended output hash
and exact destination. Apply requires the same receipt, rechecks before creating
state and after obtaining the workspace lease, and executes only that file list.
Combined receipts bind the nested sorting plan, selection, filters, protection
recipe, device and configured model paths. The top-level ID is required;
model preflight still precedes sorting, followed by another sort-plan check.
This does not hash model weights at preview or certify protection efficacy.

Known stale or missing consent creates no initial state. Changes during execution
can leave incomplete, journal-backed work; existing recovery checks remain active.
Later additions are never sorted automatically. A collision keeps the planned
destination and source intact rather than selecting an unreviewed name.
Ordinary valid files may still be applied from an unchanged preview with blockers;
category and combined sorting require a ready plan. Original bytes/names/mtime
remain private recovery data. Videos remain byte-preserved and sort-only.

## Executed evidence

| Evidence | Result and scope |
| --- | --- |
| `before.xml` / `before.txt` | 20 pre-fix regression failures retained |
| `first.xml` | First implementation: 20 passed |
| `compatibility-first.xml` | 18 failures, 1,124 passed, 9 skips; old consent expectations, two sandbox Chromium timeouts |
| `compatibility-second.xml` | 178 passed, 1 skip; one new fixture call error, then corrected |
| `full-native.xml` | 1,155 passed, 9 skips on Windows before final planner import/annotation correction |
| `final-sort.xml` | After that correction: 168 passed, 1 skip; receipt/API/CLI/controller, combined synthetic protection, real video fixtures, partial failure/collision/undo paths |
| `contracts-before-review.txt` | Correctly rejected seven changed/new application files against PAC-030 |
| `contracts-final.txt` | Seven external stages pass: 398 signatures, 48 leaf modules, 58 application hashes |
| `raw-source-first.txt` | 1,105 diagnostics, including five new planner typing errors, retained |
| `raw-source.txt` | 1,100 diagnostics in 37 files, 51 checked; remains failing; planner has no diagnostics |
| `browser.txt`, `browser/` | Real Chromium UI, controlled network responses, 1100x900 and 390x844 captures inspected |
| `ui-audit.json`, `ui-review.json` | Same 66 static findings as earlier audit; no blanket static-clean claim |
| `build-final.txt`, `install-final.txt`, `package.json` | Fresh source/sdist/wheel/isolated installation equality across 58 application files; real CLI/API/service consent, apply, exact undo and combined model gates |
| `entries.json`, `start-transcript.txt` | Actual Windows wrapper/version and START linear menu/q-exit |
| `pacer-validation.json` | Structurally valid; stale evidence and new registrations deferred |

The native suite has five Windows symlink-privilege and four POSIX terminal skips;
junctions are tested. Dependency/cache warnings did not affect assertions.
The full suite predates only the final new-planner codec-import and callback-type
correction. Its source basis is retained in `raw-source-first-command.json`;
the final affected suite, contracts, raw audit and packages use the final source.
The prior external/source records are retained under `typing-before/`.

The UI probe covers ordinary/category receipt transport, duplicate prevention,
late previews, missing receipts, stale server errors, retry, rule drafts and undo.
Reduced-motion emulation, narrow geometry, Escape and focus restoration passed.
Real API tests independently cover filesystem effects. This is not mobile
hardware, screen-reader, Safari, translated UI or live-model acceptance. The
static scanner's 64 externally bound handler findings, moved DESIGN document
heuristic and unrelated publication textarea finding remain documented separately.

Run `uv run --no-sync --locked --cache-dir .tmp/uv-cache python
evidence/sort-preview/verify.py` to check retained evidence/source identity.
`--inventory` only produces deferred register/symbol operations, and intentionally
reports missing/stale registrations under the freeze. It never edits CSVs.
The verifier does not rerun tests or establish clean bootstrap/native platform
qualification. Existing environments/dependencies were used; no model weights,
new dependencies or release version were added. Next: PAC-032 catalog scaling.
