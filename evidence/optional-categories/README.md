# Optional categories / user correction / 2026-09-20

The user clarified that categories apply **if found** and must not prevent a
sort. Earlier tests explicitly asserted mandatory original titles and unique
category assignments. Passing those tests did not establish the intended
workflow. That semantic acceptance is withdrawn; historical evidence remains.
Exact user wording and the active checkpoint are in `todo-audit.PACER.md`.

## Corrected behavior

- No saved rules, empty rules, unmatched titles, tied matches and numbered names
  all remain sortable. Use Year/Month/img-or-vid/Size when no category is found.
  Do not create an automatic `uncategorized` layer.
- Clear matches use the existing saved-rule matcher and optional category layer.
  Explicit manual assignments remain available. Unknown titles remain unknown.
- Preserve existing catalog category folders when no new match is available,
  including legacy rows without title records. Saved manual choices survive
  rule removal. An explicit `=auto` clears a saved choice and uses current
  matching, falling back to the ordinary route.
- Shared planning supplies terminal, CLI, API and combined sorting. Preview
  receipts use version 2; source/private-state integrity, explicit REPLACE/UNDO,
  date-only image output, video byte preservation and recovery remain intact.
- Both float folder names remain excluded from sorting; standalone image
  RIPOSTE intake remains available. This correction adds no configuration step.
- Terminal, browser, discovery and help copy consistently describe categories
  as optional. Reports show ordinary destinations and retained category choices.

## Executed evidence

All media below are generated temporary fixtures outside the application root.
No user artwork was sorted.

- `before-tests.txt`: all **8** initial regressions failed on the rejected
  implementation. `after-tests.txt`: the same **8 passed** after repair.
  `tests/test_optional_categories.py` subsequently adds a ninth case for a
  legacy categorized catalog with unavailable title records.
- `affected-tests.txt`: **188 passed, 1 Windows symlink skip, 1 deselected**.
- `full-suite.txt`: **1,412 passed, 9 platform skips, 2 deselected** using
  `.venv/Scripts/python.exe -m pytest -q -k 'not category_browser_native and not native_browser'`.
  This run predates only final help-copy edits, a local-variable rename and the
  additional legacy-category case; final affected tests cover those changes.
- `final-focused-tests.txt`: **56 passed** for optional categories, real video
  sorting/undo, terminal product rendering and title discovery.
- `final-affected-tests.txt`: **236 passed, 1 Windows symlink skip, 1 deselected**
  on final source. Command: `.venv/Scripts/python.exe -m pytest
  tests/test_optional_categories.py tests/test_category_sort.py
  tests/test_category_rules.py tests/test_category_sort_interfaces.py
  tests/test_video_sort.py tests/test_workflows.py tests/test_sorter_menu.py
  tests/test_float_sort.py tests/test_terminal_polish.py
  tests/test_v04_product_terminal.py tests/test_title_categories.py
  -q -k 'not category_browser_native'`.
- `native-powershell.txt` and `native-cmd.txt`: actual Windows ConPTY execution
  of START.ps1 / START.cmd with default motion. Select a generated folder, Sort
  without rules, type REPLACE, verify three ordinary date/media/size outputs,
  repeat Sort with NO CHANGES, type UNDO, verify exact original bytes/names,
  verify float storage unchanged, and exit with cursor restored. Raw ANSI,
  stripped output and JSON checks are retained. These are actual launcher/input
  loop checks; the user's Windows Terminal and VS Code windows were not operated.
- `native-browser.txt`: **2 passed, 27 deselected** using
  `.venv/Scripts/python.exe -m pytest tests/test_category_sort_interfaces.py
  tests/test_browser_review.py -q -k 'category_browser_native or native_browser'`.
  Real Chromium exercises the production DOM and unknown-category apply state
  with fixture transport. Separate CLI/API tests execute actual engine apply and
  undo. Browser permission was already qualified outside sandbox restrictions.
- `capture.py`: production cell renders at 72x24 and 100x34 for sorter, preview
  and confirmation. These PNGs are simulated host renders, not native screenshots.
- `contract-review.txt`: exactly eight reviewed application owners; callable
  signatures remain unchanged. `contracts.txt`: all seven external stages pass,
  **479 signatures, 56 leaf modules, 66 application files**, retaining all 13
  negative-consumer diagnostics. Reports remain existing dynamic boundaries;
  this is not source-body or product-acceptance certification.
- `raw-source-first.txt`: initial raw audit, **789 diagnostics / 37 files**.
  The new optional slug reused a string-only local name; it now has its own
  name. `raw-source.txt`: **788 diagnostics / 36 of 59 files**, still FAIL.
  `raw-source-difference.json` identifies three added calls into existing
  untyped report helpers compared with the prior 785. No typing suppressions,
  dynamic declarations or configuration relaxations were introduced.
- `build.txt` and `packages.json`: fresh wheel/sdist hashes match all **66**
  reviewed application files. Native execution uses the existing editable
  environment. Clean-install qualification (PAC-034) remains shelved.
- `premium-audit.json`: static scanner still reports the **same 66 findings**
  as the prior snapshot, byte-equivalent finding records. Handler detection,
  native ownership and textarea findings remain bounded separately; no clean
  scanner claim. Canonical UI/design documents intentionally stay in `docs/`.
- `design-lint.txt`: the optional external design-document linter could not
  execute offline because its package is not cached (ENOTCACHED). No package
  dependency was installed. Design copy and runtime token ownership were
  reviewed directly; no schema-lint compliance is claimed.

The broad run retains dependency deprecation warnings; the native browser run
also retains a pytest-cache concurrency warning. Two invocation errors are kept
in `native-cmd-argument-error.txt` and `focused-test-path-error.txt`; corrected
commands pass. `whitespace-line-ending-option-error.txt` retains a failed check
that disabled the checkout's CRLF normalization; the normal scoped `git diff
--check` passes in `source-whitespace-check.txt`. These were command errors, not
application failures.

Synthetic CPU protection/combined tests qualify their exercised codec/storage
paths, not pretrained model efficacy or GPU execution. No human usability or
whole-product acceptance is claimed. Frozen-register reconciliation and release
completion remain separate. All four CSV before/after hashes match. Read-only
PACER validation is valid with no errors/warnings and the same eleven historical
stale-evidence records; source/test/evidence registration remains deferred.
