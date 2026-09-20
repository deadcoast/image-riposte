# PAC-038 / consistent error and recovery guidance

User authority: "Next: PAC-038 — consistent error and recovery guidance."
NDL-024 admits this implementation; OGM-025 defines the bounded requirement.
The active development record is [todo-audit.PACER.md](../../todo-audit.PACER.md).

## Implemented

`src/riposte/static/recovery-catalog.json` is the single packaged source of
explanations, safe next actions, informational states and operation overrides.
Python `recovery.py` and browser `recovery.js` consume it. Error construction and
presentation retain only bounded uppercase machine codes; machine envelopes stay
code-only. Unknown codes retain their safe identity and receive conservative
operation-specific guidance. Missing catalog data cannot block startup/error
reporting. The browser load has a two-second abort deadline.

CLI, terminal screens, blocked reports, browser transport/jobs, sorting dialogs,
publication blockers and duplicate scan failures share that meaning. Browser
errors persist until dismissed and remain inside an open dialog. Terminal error
text scrolls at 72×24 while the code stays visible. Category ties, unknown titles
and unmatched filenames stay informational; the ordinary dated route remains
available. Guidance never retries, changes consent, deletes a lock or bypasses
history/revision checks. Draft input survives errors and dismissal.

## Executed evidence

- `before.txt` / `before.xml`: two reproduced pre-fix failures (raw error text and
  missing fallback action), with the existing machine envelope already passing.
- `suite.xml`: **1,519 passed, 9 platform skips**; `native.xml`: **3 passed** in
  isolated Chromium. `suite-first.*`, `browser-unit-first.txt`, `native-first.txt`
  retain failures found during integration. Request dispatch remains immediate;
  guidance loading is awaited at response presentation, not before sending.
- `focused-final.xml`: 58 targeted checks. `tests/recovery_guidance.cjs` compares
  Python and actual browser lookup outputs across every catalog entry and six
  operation contexts, including unknown codes, private text and unavailable data.
  Actual FastAPI/job tests verify sanitized direct and asynchronous errors and
  serving the canonical catalog. Small-terminal tests scroll complete guidance,
  preserve the machine code and prove Return does not retry.
- `live_browser.py`, `live_probe.js`, `browser-live.json`: actual authenticated
  local server and Chromium, without fetch mocks. A concurrent save is rejected
  with draft-preserving recovery; missing consent is rejected with actionable
  guidance. Generated 58-file sort/undo restores original bytes and mtimes;
  `_float_` and `__FLOAT__` contents remain untouched. Retained screenshots include
  wide/narrow recovery notices; the lock notice shown for layout is a presentation
  fixture, not a new live lock qualification.
- `contract-review.json`, `contracts-first.txt`: explicit review of 17 changed/new
  application owners, **536 signatures, 63 leaf modules, 76 source files**; seven
  external stages pass and 13 expected negative-consumer diagnostics remain.
  `contracts-before.txt` retains the expected source/stub drift rejection.
- `raw-source.txt`: strict implementation typing remains **FAIL: 825 diagnostics
  in 36 of 66 files**. Two added diagnostics are calls to existing untyped report
  helpers; the new recovery module has none. `raw-delta.json` records the comparison
  with PAC-037. No ignores, strict-setting relaxation or dynamic declarations added.
- `build.txt`, `verification.json`: wheel/sdist byte equality for all 76 application
  files (including catalog/loaders) and current README/design/UX/status guides.
  Existing environments and offline package build only; no clean installation.
- `ui-static.json`, `ui-review.json`: 82 generic static findings retained and
  dispositioned. No claim of a global UI static pass or human accessibility proof.
- `inventory-final.txt`, `acceptance-review.json`, `OGM-*.json`, `governance.json`:
  guarded source registration, scoped revalidation, PAC-038 closure and NDL-024
  absorption. Prior requirement evidence is retained, not overwritten.

Run `.venv/Scripts/python.exe evidence/recovery-guidance/verify.py` to check retained
evidence and package/source parity. These checks do not establish independent human
usability, other hosts, classification accuracy, real-model protection efficacy or
the shelved PAC-034 clean-install qualification.
