# Terminal polish and float storage / 2026-09-20

The user requested another UI/operation polish pass, then added reserved personal
storage folders `_float_` and `__float__`, explicitly retaining image RIPOSTE
processing for both. Original wording and frozen-register authority are in
`todo-audit.PACER.md`. This is a bounded implementation, not release completion.

## Implemented behavior

- Picker Page Up/Down uses its rendered row capacity. Parent navigation restores
  the child highlight, with the existing Windows isolated-key fix unchanged.
- Invalid path input is retained with a useful error. Enter correctly says
  Preview when choosing a folder continues a pending read-only preview.
- Blocked sorter results advertise Return and a direct Full Sort Workshop
  shortcut using the reviewed settings. Empty/already-sorted previews show
  NO CHANGES without opening REPLACE. Dry Run cannot apply.
- Confirmation shows its bound folder, complete operation warning and working
  help/command views. Submitted confirmations and consumed previews leave the
  back stack, including after failed writes. Failed sorter results retain `g`.
- Read-only sort/undo previews no longer load unrelated publishing history.
- Both exact float directory names match case-insensitively at every depth.
  Sorting prunes them before media inspection, including sidecars and videos;
  discovery and organization audit use the same exclusion. Sorting a float root
  or descendant is refused before workspace initialization. Near-matching names
  and files called `_float_` remain ordinary inputs. Direct protection intake is
  unchanged and supports float folders as input and/or results workspace.
- Sort + RIPOSTE retains the shared exclusion and protects eligible sorted
  images. Standalone RIPOSTE processes float storage without sorting it.
  Existing explicit undo follows its saved journal; old recovery is not rewritten.

## Evidence and limits

`before-tests.txt` retains 13 failing polish cases on the prior implementation.
`float-before-tests.txt` retains 19 failing / 4 already-passing float cases.
`float-tests.txt` retains the first post-change run: 78 passed, two failed because
the new protection fixture used default creation dates while asserting modified
dates. The fixture now explicitly selects modified dates and additionally covers
a results workspace inside float storage. No production date behavior changed.

`affected-tests.txt`: **293 passed, 4 POSIX skips** across the float, workflow,
category-sort and terminal suites. This precedes the final two normalized-path
cases. The full application run records those cases in `full-suite.txt`.

`full-suite.txt`: **1,400 passed, 9 platform skips, 2 deselected**, using
`.venv/Scripts/python.exe -m pytest -q -k 'not native_browser and not category_browser_native'`.
The two native Chromium scenarios passed separately in `native-browser-tests.txt`
outside the sandbox, whose navigation restrictions were established in the prior
task. That run retains two dependency deprecations and a concurrent pytest-cache
warning. The full suite precedes one final error-context copy correction (remove
the unavailable Overview/Details hint from stopped results).

`final-affected-tests.txt`: **295 passed, 4 POSIX skips** on the final source,
including both normalized-path cases and all affected sorter/workflow/terminal
suites. Native launcher checks, cell captures, contracts and packaging were also
repeated on that final source. No additional runtime failures remain in this scope.

`native-console-powershell-motion.json` and `native-console-cmd-motion.json`
record the actual START.ps1 / START.cmd through Windows ConPTY with default
animation, isolated/reversed arrows, exact Enter activation, parent focus,
visible-page movement, pasted-path correction, direct workshop recovery, direct
float-root refusal and path recovery, idle
screens and exit. `.ansi` and `.txt` retain raw and stripped output. Synthetic
inputs remain unchanged. The user's actual VS Code window was not controlled.

`capture.py` renders production terminal cells at 72x24 and 100x34. The PNGs are
simulated terminal host renders, not native screenshots. Sorter, empty, blocked,
preview, error and confirmation states were reviewed; no new palette, font
dependency or terminal toolkit was introduced.

`contract-review.json` admits exactly ten changed application files against the
previous keyboard snapshot. The external suite passes all seven stages:
**479 signatures, 56 leaf modules, 66 application files**, including all 13
negative-consumer diagnostics. `raw-source.txt` remains FAIL: **785 diagnostics
in 36 of 59 checked files**, versus 782 previously. `raw-source-difference.json`
identifies three new calls into existing untyped UI helpers. Historical evidence
is retained under `typing-before/`; no typing suppression/configuration relaxation.

`build.txt` and `packages.json` verify fresh wheel/sdist bytes against all 66
reviewed application files. This is not clean-install qualification. Native
startup uses the existing editable environment; PAC-034 remains shelved.

`premium-audit.json` retains the static web scanner's 66 findings on unchanged
browser source (handler-detection limitations, native ownership and textarea
findings). It does not scan Python terminal controls. Canonical design and UX
documents intentionally remain under `docs/`. This is not a clean scanner claim.

All media are synthetic temporary fixtures. CPU protection runs use the existing
synthetic oracle and real codec/storage paths; they do not qualify pretrained
model quality, GPU execution or protection efficacy. No user artwork was sorted.
Four CSV registers stay frozen; their reconciliation and broader release/audit
completion remain separate work.

`registers-before.json` and `registers-after.json` match exactly. Read-only PACER
validation is valid with no errors/warnings and the same eleven stale historical
evidence records. Source/symbol/test/evidence reconciliation remains deferred
together at the authorized milestone.

The scoped source/documentation `git diff --check` passes. The unscoped check
flags intentional fixed-width padding and terminal control output in raw text/
ANSI evidence; those captures are preserved verbatim rather than whitespace-cleaned.
