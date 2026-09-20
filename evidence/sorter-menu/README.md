# Riposte Sorter and terminal input repair / 2026-09-19

The user's requested default is **Riposte Sorter** with **Sort**, **Dry Run** and
**Enter Path**. **Full Sort Workshop** retains the existing configurable flow.
The preset explicitly selects the existing saved-category engine with download
dates and Year/Month/img-or-vid/Category/Size. Unmatched titles use uncategorized;
ambiguous matches and missing original titles remain blockers. No category rules
are inferred or silently saved. Sidecar deletion stays opt-in in the workshop.
Paths are session-only. Sort reviews an exact plan before REPLACE; Dry Run has
no apply action. Both keep the existing shared service and journal-backed undo.

## Repairs and reproduction

- `before.txt`: two failing pre-repair regressions. Ignored input replaced drive
  location rows with directory rows; Windows zero-timeout polling could not read
  queued keys. The old live loop read one key per complete redraw.
- The loop now drains at most 128 queued events before repainting, without
  consuming an unprocessed event at the bound. Nonblocking reads preserve partial
  escape sequences. Static screens repaint on input/resize instead of forever.
- Picker activation uses the displayed rows. Ignored input cannot rescan/reorder
  them. Folder-only discovery uses directory-entry attributes and avoids probing
  every media file. Direct `s` accepts the highlighted directory, including a
  parent row. Failed navigation preserves focus and exposes its error.
- `g` starts with an empty field, accepts quoted paths, and works at every
  picker depth, in Full Sort Workshop, and in Riposte Sorter/results. It no longer
  appends a pasted path to the previous one. Sorter path selection does not load
  unrelated catalog or publication history. Invalid paths preserve the old root.

## Executed evidence

All commands used the existing environments and synthetic temporary media.
No user artwork was sorted as part of development.

| Evidence | Result and scope |
| --- | --- |
| `final-focused.txt` | **197 passed, 4 POSIX skips** on the final source: `python -m pytest tests/test_sorter_menu.py tests/test_menu_startup.py tests/test_v04_terminal_core.py tests/test_v04_terminal_host.py tests/test_v04_product_terminal.py tests/test_workflows.py -q` |
| `final-suite.txt` | **1325 passed, 9 platform skips, 2 deselected**: `python -m pytest -q -k 'not native_browser and not category_browser_native'`. This precedes the final bounded parent/disappeared-folder correction; the 197-test affected suite and native runs were repeated after that correction. |
| `native-browser-rerun.txt` | Both deselected native browser scenarios passed outside the sandbox; initial sandbox `Page.navigate` timeouts remain in `full-suite.txt` (1323 passed, 2 failed, 9 skipped before the added listing/path regressions). Browser source was unchanged. |
| `native-console-powershell.json`, `native-console-cmd.json` | Actual Windows ConPTY, START.ps1 and START.cmd, raw keyboard loop, default action, pasted paths, nested `g`, direct folder selection, Dry Run, preserved protection workflows, idle static screen, safe exit and unchanged synthetic files. A single burst of 25 arrows plus Enter reached the exact folder path in about 0.05 s at the harness's 0.05 s observation interval. This is a local fixture measurement, not a general latency guarantee. |
| `home-small.png`, `sorter-small.png`, `sorter-wide.png`, `picker-small.png` | Visually inspected production cell renders, 72x24 and 100x34; simulated terminal host, not native screenshots. All menu choices and the three sorter actions remain visible. |
| `contract-review.json`, `contracts.txt` | Eight changed application files reviewed; all other application hashes unchanged from Kontext. **478 signatures, 56 leaf modules, 66 application files**; all seven external contract stages pass, with all 13 negative consumer diagnostics retained. |
| `raw-source.txt` | **782 errors in 36 of 59 checked files**, still FAIL. Ten new call-site diagnostics concern the preset's use of existing untyped terminal helpers. No suppression, new dynamic declaration or configuration relaxation. Previous 772-error evidence retained in `typing-before/`. |
| `build.txt`, `packages.json` | Fresh uv wheel and sdist contain identical reviewed bytes for all 66 application files. Native startup uses the existing editable installation; this is not clean-install or release qualification. |
| `premium-audit.json` | Static web scanner still reports 66 findings on unchanged browser files (handler-detection limitations, native ownership and existing textarea findings). It does not inspect Python terminal controls. The maintained design/UX contracts remain under docs as required; no blanket static UI compliance claim. |
| `registers-before.json`, `registers-after.json` | Four CSVs byte-identical. PACER structural validation valid, no errors/warnings, 11 stale evidence records retained. |

`first-focused.txt` is also retained: its repository-local basetemp violated the
application-root safeguard and caused fixture failures, alongside old menu
shortcut assertions. Subsequent runs used the system temp directory and updated
the assertions to the requested menu. `second-focused.txt` retains a wrong test
keyword and the last two stale shortcuts; those fixture corrections are explicit.

`review_contracts.py` verifies the admitted source-file set and source/stub
parameter parity before writing the new reviewed snapshot. `verify_packages.py`
compares actual archive bytes. Neither script proves runtime or model acceptance.
No clean-install, POSIX terminal, assistive-technology, large real user-library,
pretrained-model or protection-efficacy qualification is claimed.

## Deferred governance

The task and exact user wording are retained in `todo-audit.PACER.md` under the
four-register freeze. Source/symbol rows, new tests, contract/evidence files and
reciprocal references must be reconciled together at the authorized milestone.
PAC-034 remains shelved. The wider audit/release milestone remains open.
