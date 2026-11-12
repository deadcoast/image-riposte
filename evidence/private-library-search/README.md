# PAC-042 — private original-title and category library search

`riposte library-search ROOT`, **s** in the terminal library, and browser
**Private library search** provide explicit local access to private provenance.
Search matches literal Unicode-normalized text and exact category slugs, combines
date/size/title-availability filters, and returns bounded pages. One SQLite read
transaction joins catalog and provenance; page revisions reject stale results.
Missing, malformed, oversized or identity-mismatched provenance cannot supply a
title/category match. Default catalogs, image metadata and publishing state are
not enriched. Selecting a result passes only its image ID to existing operations.

The baseline reproduction in `baseline.json` shows a saved original filename
that ordinary canonical-name search cannot find. That ordinary search remains
private-field-free. `prepare.py` creates an isolated synthetic reproduction.

## Evidence and boundaries

Final executed runs: **90 focused passes / 1 privilege skip**, **1,637 full-suite
passes / 12 platform or privilege skips**, and **6 native browser passes**. All
seven external contract stages pass for 81 application files and 564 signatures.

- `focused.xml`, `suite.xml`, `native.xml`: focused, full non-browser and actual
  Chromium regression runs. `native-keyboard.xml` retains the earlier isolated
  native-select keyboard check; the final browser run includes that check too.
- `contracts-final.txt`, `contract-review.json`: reviewed source/stub contracts;
  `typing/evidence/source-reviewed-private-library-search.json` binds application
  hashes. External contracts are not a claim of clean source-body typing.
- `raw-source.txt`, `raw-delta.json`: strict source typing remains **FAIL**, 873
  diagnostics in 36 of 69 Python files. Eleven added calls reach existing
  untyped report helpers. `library_search.py` has no raw diagnostics. No strict
  options, exclusions or suppression policy were weakened.
- `wide.png`, `narrow.png`, `ui-static.json`, `ui-review.json`: inspected workbench
  layout and scoped dispositions for the static scanner's 91 findings. The
  scanner does not resolve external ID-bound event handlers; this is not a global
  UI compliance pass. Native popups are deliberately platform owned. The optional
  design.md linter could not run offline (`ENOTCACHED`); no dependency was installed.
- `build.txt`, `verification.json`, `documentation.json`, `launcher-help.txt`:
  package byte parity, maintained-doc parser/link checks, historical preservation
  and actual Windows launcher help in the existing environment.
- `requirement-review.json`, `OGM-*.json`, `governance.json`: scoped source-bound
  acceptance, current source references and final task checkpoint.

The browser uses the real authenticated local server for title search, filtering,
paging and image selection. Delayed/offline replies, a stale-page response and
composition events are injected. Native keyboard and viewport tests do not
establish physical IME, screen-reader, human usability or user terminal-host
acceptance. Search matches stored catalog identity; it does not audit all current
image bytes or authenticate historical source filenames. Existing image
inspection still rejects changed bytes. No pretrained-model efficacy, different
OS or clean-install qualification is claimed. PAC-034 remains shelved.

## Retained failures

The first focused run used an undeclared fixture category (14 failures, 12 passes).
The second passed 26 tests. The first expanded focused/full run used a changed PNG
fixture containing forbidden metadata, so inspection correctly rejected metadata
before the intended hash check; the fixture now uses a valid date-only PNG.
Those runs remain in `focused-third.*` and `suite-first.*`.

The first native run found that an invalid year hidden in collapsed filters could
not receive focus. The implementation now opens the disclosure before focusing.
The second native run found an incorrect test selector; the corrected third run
passed. All original reports remain separate from the final evidence.

The initial contract check rejected the new module and stale source snapshot;
declarations were reviewed before admission. The initial raw check found three
new TypedDict update-call diagnostics; explicit field assignments removed them.
An early guarded PACER demotion was rejected as stale while raw evidence was
still being generated. It changed no registers; reconciliation runs after checks.

The final delta review corrected seven interface annotation diagnostics (service
optional-limit narrowing, endpoint/CLI return declarations and a controller local
name collision). `raw-source-second.txt` and `raw-delta-before-annotation.json`
retain the prior 880-diagnostic state and its incorrect preliminary summary.
`annotation-regression-final.*` passes after correction; the earlier annotation
probe named a nonexistent test file and ran no tests. Full/native runs were also
repeated on the final source.
