# Windows isolated-key and direction-reversal repair / 2026-09-19

The user reported that the first change of direction seemed ineffective, with
highlight and activation apparently offset, in both Windows Terminal/PowerShell
and VS Code's terminal using START.ps1. Their explanation was explicitly a
theory. Investigation reproduced a specific native input failure before editing
the application; no color/highlight mechanism was assumed.

## Observed cause

A single Down arrow sent to the real Windows ConPTY application produced no
updated focus for the entire 15-second observation. The forwarding input trace
recorded `getwch -> U+00E0`, then `kbhit -> false`. Windows had consumed the
physical event and cached its second, wide-character scan code. The application
incorrectly polled kbhit again before reading that code. A later physical key
could release the previous direction instead of immediately delivering its own.

[Microsoft's getwch contract](https://learn.microsoft.com/en-us/cpp/c-runtime-library/reference/getch-getwch?view=msvc-170)
requires two reads for an extended key: the prefix followed by its scan code.
The fix reads both together and removes the obsolete pending-prefix field.
No controller, renderer, palette, sorting policy, consent or engine behavior was
changed in this follow-up. The prior three-action sorter remains intact.

The previous native checks sent arrows followed immediately by Enter in a burst.
That later input allowed the pending scan code to advance, hiding the isolated
keypress failure. Earlier test passes did not qualify this missing case.

## Retained evidence

- `before-native.txt`: actual unmodified START.ps1 launch fails after one Down
  with no second key supplied. `before-traced-native.txt` repeats the failure
  with forwarding-only input instrumentation; `before-input-trace.jsonl` records
  the prefix and false keyboard-availability result.
- `before-unit.txt`: all 24 added cases fail using separate physical-event and
  cached-wide-code queues. Unlike the earlier simple list mock, keyboard
  availability does not incorrectly include the cached scan code.
- `focused.txt`: **193 passed, 4 POSIX skips**, from
  `.venv/Scripts/python.exe -m pytest tests/test_terminal_direction.py tests/test_sorter_menu.py tests/test_menu_startup.py tests/test_v04_terminal_core.py tests/test_v04_terminal_host.py tests/test_v04_product_terminal.py -q`.
- `native-console-powershell-motion.json` and `native-console-cmd-motion.json`:
  actual default START.ps1 and START.cmd through Windows ConPTY with animation
  enabled. Isolated Down/Up and repeated first reversals move the displayed `>`
  focus; Enter opens that exact main action and folder. The three-action sorter,
  path entry, burst input, Dry Run, independent protection workflows and exit
  remain verified on synthetic folders. `native-console-powershell.json` retains
  the no-animation run. Raw `.ansi` captures retain terminal style/control bytes.
- `after-input-powershell-still-trace.jsonl`: prefix and scan-code reads occur
  consecutively while kbhit remains false, without needing another physical key.
  This uses a direct CLI launch with wrappers forwarding every actual getwch
  call; the uninstrumented launcher runs are separate evidence.
- `contract-review.json`, `contracts.txt`: only the keyboard module differs
  from the prior reviewed sorter snapshot; the removed private field is removed
  from its external stub. **478 signatures, 56 leaf modules, 66 application
  files**; seven external stages pass, including all 13 negative diagnostics.
- `raw-source.txt`: **782 errors in 36 of 59 files**, unchanged and still FAIL.
  No type configuration, suppression or dynamic-boundary relaxation.
- `build.txt`, `packages.json`: all 66 reviewed application files match fresh
  wheel/sdist bytes. This is not clean-install qualification.
- `registers-before.json`, `registers-after.json`: all four frozen CSVs remain
  identical. PACER structural validation is valid with the same eleven stale
  evidence records. Registration/reconciliation remains deferred together.

This qualifies the reproduced shared Windows input path, native console output
and synthetic menu/folder activation. The user's actual VS Code window and real
artwork library were not controlled, and POSIX native execution was not tested.
The full application suite from the prior task was not rerun for this single
keyboard-module repair; affected tests and native isolated-key tests were run.

Reproduce the native checks with
`.venv/Scripts/python.exe evidence/terminal-direction/native_console.py --motion`
or append `--entry cmd`. Omit `--motion` for static startup; `--trace` separately
uses the forwarding-only direct CLI probe. `review_contracts.py` checks the exact
admitted source change; `verify_packages.py` compares current archive bytes.
