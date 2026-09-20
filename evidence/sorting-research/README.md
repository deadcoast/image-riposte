# Research-led Riposte Sorter / 2026-09-20

The user requested critical review and integration of both supplied sorting
papers while retaining year and month. Exact wording is in `todo-audit.PACER.md`;
decisions and primary references are in
[`RIPOSTE-REVIEW.md`](../../docs/research/sorting/RIPOSTE-REVIEW.md).
The supplied research files remain unchanged. The user's unrelated research-file
move is preserved. No user artwork was processed.

## Implemented behavior

- Existing Sort / Dry Run / Enter Path flow; no mandatory setup added.
- Unicode normalization, visible CamelCase boundaries, conservative export/noise
  parsing and contiguous phrases. Numeric identifiers such as R5/B52 survive.
  Explicit saved rules retain legacy token matches as well as CamelCase matches.
- Dependency-free local proposals use distinct normalized filename families,
  document frequencies, sparse observed NPMI associations and deterministic
  anchor neighbourhoods. Equivalent word/phrase proposals are suppressed.
  These are lexical heuristics, not a trained semantic classifier or a modularity
  community implementation. Scores are IDF coverage, not probabilities.
- Manual choices and saved rules take precedence; existing category folders
  remain and guide later imports. Tied rules are not rescued with an arbitrary
  automatic choice. Small, ambiguous, unknown or resource-limited inputs take
  the ordinary route. No automatic `uncategorized` folder or rules save.
- Shared engine proposals and their version/settings enter the exact preview
  receipt (version 3). Terminal, CLI, API and combined sorting use that planner.
  Discovery exposes optional reusable-rule groups. Terminal/browser show local
  pattern evidence within the existing review controls.
- Actual four-digit years replace the former 2024–2026 bucket restriction.
  Legacy image/video EVERYTHING_ELSE catalogs remain readable; their relocation
  is previewed, consented and undoable. Browser trees and year selection accept
  the actual years.
- Existing source identity checks, REPLACE/UNDO, private original provenance,
  date-only PNG metadata and byte-preserved videos remain. `_float_` and
  `__float__` are excluded before sorting/analysis; independent image RIPOSTE
  processing remains available inside them.

## Executed evidence

All media are synthetic temporary fixtures outside the application root.

- `first-regressions.txt`: 26 failed / 207 passed / 2 skipped. Failures were old
  assertions for three-year bucketing. Updated expectations admit actual years;
  new legacy image/video tests exercise real catalog relocation and exact undo.
- `new-tests-first.txt`: 1 failed / 18 passed. Repeat sorting unnecessarily made
  another journal because retained categories lost matched-term provenance.
  Retaining those terms fixes that regression.
- `phrase-first.txt`: the observed duplicate phrase/word proposal failure.
  `research-tests.txt`: all 22 adversarial research cases pass after its repair.
  These include Unicode/noise boundaries, variant deduplication, deterministic
  ordering, preserved category anchors, conflicts, all analysis limits,
  cancellation, stale settings, actual years, repeat import and exact undo.
- `integration-first.txt`: 1 failed / 74 passed / 1 deselected. The new API
  fixture omitted its session token; the application correctly refused it.
  `integration-tests.txt`: corrected fixture, 75 passed / 1 deselected. Includes
  real API/CLI apply/undo, FFmpeg video transactions and synthetic CPU combined
  sorting/protection. This intermediate run precedes the phrase fix.
- `full-suite.txt`: final application source, **1,438 passed, 9 skipped,
  2 deselected**, 207.58 seconds. Command: `.venv/Scripts/python.exe -m pytest
  -q -k 'not category_browser_native and not native_browser'`. Skips are platform
  capabilities; dependency warnings remain. `full-suite-before-final.txt` and
  `core-tests.txt` retain earlier passing scopes, not substitutes for this run.
- `native-browser.txt`: **2 passed, 28 deselected** in real Chromium, production
  DOM with fixture transport. New checks select a complete proposed rule group,
  expose heuristic scores and display years outside the former range. Existing
  error/retry, consent and responsive-state checks remain. Separate API tests
  above use the actual engine; fixture transport is not a live server acceptance
  test. The log retains dependency and pytest-cache concurrency warnings.
- `native-powershell.txt`, `native-cmd.txt`: actual Windows ConPTY execution of
  START.ps1 / START.cmd with motion enabled. Enter a generated folder, preview
  without rules or writes, type REPLACE, verify nine categorized and two ordinary
  outputs, repeat with NO CHANGES, type UNDO, verify exact original bytes/names
  and unchanged float storage, exit zero with cursor restored. Raw ANSI and
  decoded output are retained. The user's Windows Terminal/VS Code windows
  were not operated; no human usability acceptance is claimed.
- `capture.py`: production-cell renders at 72x24 and 100x34 for sorter, preview,
  pattern details and confirmation. Images were inspected for readable wrapping
  and reachable controls. These are simulated host renders, not native screenshots.
- `benchmark.py` / `scaling.json`: one in-memory synthetic run per size. 1,000
  titles: .0412 s / 940,406 traced bytes; 10,000: .3649 s / 9,323,402 bytes;
  both produce four groups from four observed pairs. The 50,001-title workload
  stops at the vocabulary limit after 33,330 families, in 1.0605 s /
  32,078,886 bytes, with no partial proposals. Separate limit regressions prove
  ordinary sorting still applies. This is classifier-stage timing/allocation,
  not whole-folder I/O, representative graph density or million-file qualification.
- `contract-review.txt` / `contracts.txt`: fourteen reviewed/new source owners,
  **486 signatures, 57 leaf modules, 67 application files**. External contract
  stages pass; all 13 negative-consumer diagnostics remain. The new corpus stub
  is source-derived. Dynamic report boundaries were not broadened. External
  contracts do not certify source bodies or product acceptance.
- `raw-source.txt`: **797 diagnostics in 36 of 60 files**, still FAIL. The
  normalized difference from 788 is nine calls to existing untyped terminal
  report helpers. No suppressions, Any declarations or relaxed configuration.
  The new corpus module has no raw diagnostics. Earlier raw runs are retained.
- `build.txt` / `packages.json`: fresh wheel and sdist match all **67** reviewed
  application files. Native checks use the existing editable installation;
  PAC-034 clean-install qualification stays shelved.
- `premium-audit.json`: the same 66 finding records as the preceding snapshot,
  including static handler-detection/native-ownership limitations. No clean
  scanner claim. Canonical design documents remain under `docs/`. The external
  design-document linter was unavailable offline in the prior pass and was not
  reinstalled or claimed to have run here.

Frozen-register before/after hashes match. Read-only PACER validation is valid
with no errors/warnings, but now reports twelve stale records, including OGM-008
in addition to the eleven recorded at onboarding. Registration of the new module,
source/evidence reconciliation and the wider release milestone remain deferred.

## Remaining qualification

There is no labeled local artwork corpus in the supplied research. These tests
establish exercised parsing, routing, consent, recovery and interface mechanics;
they do not establish category precision, useful semantic taxonomy or calibrated
confidence. Optional lexical analysis is bounded; the surrounding media planner
still inventories files and decodes/validates media. Synthetic CPU protection
does not qualify pretrained model effectiveness or GPU execution. A future
accuracy evaluation needs held-out filename families and explicit human category
labels, separately from filesystem safety and human terminal acceptance.
