# PACER resumption and browser scan jobs / 2026-09-20

User: "OK UPDATE WHAT NEEDS TO BE UPDATED AND CONTINUE TO PAC WORKFLOW FROM THE @todo.audit.PACER.md".

NDL-021 admits PAC-044 reconciliation, PAC-036 exact acceptance review and
PAC-035 browser read-only scan jobs, including reconciliation of the previously
implemented PAC-029 through PAC-033. The original checkpoints and failures in
`todo-audit.PACER.md` remain historical evidence. PAC-034 is still shelved.

PAC-035 implements cancellable authenticated jobs for category discovery, rule
review, ordinary/category sort previews and undo inspection. Progress and Cancel
remain inside the native sorting dialog. Changed settings/closed dialogs invalidate
old replies. Cancellation at completion cannot publish a usable preview. Shutdown
rejects new work and signals scans; source replacement, saved rules and undo commits
may finish. Cancellation is cooperative at scan checkpoints, not an interrupt of
arbitrary decoder/hash calls. Saved-rule loading remains a bounded direct request.
The footer reads its version from the running server.

## Executed evidence

| Artifact | Result and boundary |
| --- | --- |
| `scans-before.txt` | Ten reproduced failures before the repair; retained |
| `scans-expanded.txt` | 72 affected tests passed; one native test selected separately |
| `suite.txt`, `suite.xml` | 1,499 passed, nine platform skips, three native browser tests deselected; warnings retained |
| `native-final.txt`, `native.xml` | All three real Chromium regressions passed: sort, publication review and Duplicate Finder |
| `browser-live-final.txt`, `browser-live.json`, `wide.png`, `narrow.png` | Actual authenticated server/scanner/Chromium over 960 synthetic images; cancellation, discovery, rule review, exact destinations, consent, keyboard and narrow layout; input bytes/mtimes unchanged; no fetch mocks |
| `contracts-final.txt`, `contract-review.json` | Seven external stages passed; 531 signatures, 62 leaf modules, 73 source files; 13 expected negative diagnostics retained |
| `raw-source.txt` | FAIL: 823 diagnostics in 36 files, 65 Python files checked; unchanged strict settings and baseline from Duplicate Finder |
| `entries.json`, `start-transcript.txt` | Existing editable Windows riposte.cmd version and real START.ps1 linear menu/q exit |
| `verification.json`, `build.txt` | Declared development manifest/version consistency and fresh wheel/sdist equality; no clean installation |
| `ui-static.json` | Strict generic audit retains 74 findings; reviewed limitations below; not a global clean UI claim |

The full suite covers the final Python behavior and scan UI. The subsequent
version-label-only HTML/JS edit is covered by the final native and real-server
browser checks. Live fixture directories are isolated generated test inputs, not
user artwork. No source media were sorted by the live browser probe.

## PACER reconciliation

`reconcile.py` submits reviewed operations through the installed PACER Service
with fresh onboarding, revision and full context receipts. Assets precede edges,
each transaction is at most 200 operations, and transaction receipts are retained
under `.tmp/pacer-resumption/`. CSVs are never written by these scripts directly.
The initial inventory plan and the interrupted stale-context transaction remain
recorded; a fresh plan resumes from the published graph without replaying additions.

The source index includes PCUC, sorter, float-storage, optional-category and
Duplicate Finder integrations, their declarations, tests and admitted evidence.
`terminal.service.Progress` now re-exports `records.Progress`; its old OVR identity
is preserved with an explicit alias classification and dependency.

`decisions.json` reviews each exact OGM-001 through OGM-023 requirement and names
its regression modules and limits. `acceptance.py` checks the retained executions,
historical archive/decision integrity and the current inventory before preparing
separate source-bound reports. PACER `verify` performs actual acceptance; old
reports and prior bindings are preserved. Historical selective-merge and PAC-028
identification evidence describe those events, not a claim that later source was
never changed. OGM-018 follows the user's optional-category correction; OGM-016
no longer describes already implemented persistent rules as future work.
NDL-022 / PAC-045 supplies four explicit bounded requirements for the implemented
PCUC tools, opinionated sorter, Duplicate Finder and browser inspections. This
reconciliation records their actual qualification limits rather than inferring
whole-product acceptance from the source index.

PCUC remains qualified only at its mathematical/synthetic/tiny-random CPU scope.
Duplicate scores are heuristic evidence, not calibrated probabilities or semantic
understanding. Sorter filename proposal accuracy and human host usability remain
unmeasured. PAC-034 is shelved; no release tag, version bump or clean-install
qualification is created by this work. The next audit development item is PAC-037.

## Static UI review

The generic strict audit reports native-select ownership as unresolved because
it looks for a root design file; this repository's maintained decision is in
`docs/DESIGN.md` and `docs/UX-CONTRACT.md`. Most findings are false actionless-button
reports: handlers are attached by ID in separate JavaScript. The new Cancel
handler and existing sorting controls were traced and exercised in Chromium.
The existing publication download anchor gains its URL at runtime; the existing
large textareas intentionally allow resizing inside the scrolling dialog.
These retained findings do not establish a global UI pass. Native screen-reader,
independent human and other terminal-host acceptance remain outside this evidence.
