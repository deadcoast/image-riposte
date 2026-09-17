# Authorized development-audit repairs

User authorization: **"Implement the listed repairs, including source and test changes"**.
This supersedes the earlier source-read-only assignment for these repairs.
The original [audit](../development-audit/README.md), probes and failed runs remain historical evidence.

## Implemented behavior

| Task | Repair | Executed regression evidence |
|---|---|---|
| PAC-002 | Compare descriptor and pathname snapshots consistently on Windows, while retaining ctime and replacement checks. Unchanged imports finish and retries add no duplicate catalog rows. | Immediate and dated imports, three retries, replacement and in-place mutation restoring mtime; Windows Python 3.13.9 and 3.14.3. |
| PAC-008 | Decode shipped browser assets explicitly as UTF-8. | Actual homepage route under an intercepted cp1252 default; security headers retained. |
| PAC-009 | Report incomplete/blocked jobs as needing attention. Publication completion requests a real workspace audit; failed audit retrieval leaves the badge unknown. API and generated reports use the application version. | Job controls; exact browser completion callback in Node VM; synthetic generation reports. |
| PAC-010 | Verify committed artifacts before showing approval as current. Changed/missing artifacts become blocked/stale. Rejection revokes approval independently of artifact validity. | Clean/candidate/report mutation and removal; rejection succeeds; approval, serving and ZIP remain guarded. |
| PAC-011 | Bound actual consumed API bytes before parsing, including streamed bodies. | 32,768-byte boundary, 40,015-byte chunked body, missing/false Content-Length, early stream stop, authentication and origin controls. |
| PAC-012 | Use visible form fields for linear `focus N`. | Doctor and collapsed/advanced publishing forms, arrows, edits, invalid input and bounds. |
| PAC-013 | Execute selected inpainting and temporal input-gradient objectives before request commit. Reject legacy optimizer candidates without editable pixels, useful gradients or positive final proxy divergence. | Real Torch autograd with synthetic valid, constant, detached, unrelated, nonfinite and failing models. No pretrained model weights. |
| PAC-014 | Fix fake-stat and path-separator assumptions, explicitly skip unavailable symlink privileges, and move publication/API Torch skips to numerical cases. | Full suite plus an import-blocked Torch coverage probe. |

Source paths and hashes, commands and retained outputs are indexed in [report.json](report.json).
Regression tests are [core repairs](../../tests/test_development_repairs.py),
[numerical repairs](../../tests/test_development_model_repairs.py), and
[linear focus](../../tests/test_linear_focus.py), with adjustments to existing tests.

## Results and boundaries

- Full application suite with locked lab/test extras: **761 passed, 7 skipped**.
  Three skips require Windows symlink privileges; four require a POSIX pseudo-terminal.
  Two upstream deprecation warnings remain. [Output](full-final.txt), [JUnit](full-final.xml).
- Subsequent application-version assertion: **24 generation tests passed**;
  application source was unchanged after the full run. [Output](generation-version.txt).
- External typing checks: **PASS**; 318 source/stub signatures, 38 leaf modules,
  9 runtime fixtures, 6 tooling regressions and 13 expected invalid-consumer errors.
  The reviewed source snapshot contains 47 application files. [Output](typing-check.txt).
- File/export/dependency inventory reconciliation: **PASS**, 141 indexed files;
  this does not close the separate missing-symbol inventory task. [Output](inventory-final.txt).
- Separate strict source mypy audit: **980 diagnostics in 36 of 41 files**, exit 1.
  This remains typing debt, not 980 demonstrated runtime failures. [Output](raw-source.txt).
- Simulated unavailable Torch import: **53 passed, 31 individually skipped** in the
  two publication/API modules plus core repair regressions. This is an import-blocking
  simulation in the installed environment, not a fresh dependency-free installation.
  Six other numerical modules still use whole-module Torch skips. [Output](no-torch.txt).
- Windows Python 3.13 organizer controls: all four scenarios passed. The Python 3.14
  application suite exercises the same identity cases. [Probe](probe_windows_identity.py),
  [result](windows-py313.json).

The first and second regression attempts, zero-gradient reproduction, model pre-fix
failures and initial full-suite failures are retained here. Some intermediate
failures were test-harness assumptions; `report.json` distinguishes them. Pre-repair
typing artifacts are preserved under `typing-before/`.

No pretrained efficacy, artist visual acceptance, native console lifecycle, live
TCP/browser integration, GPU performance or clean-machine/Python 3.11 qualification
is established. Browser evidence uses ASGI routes and isolated JavaScript execution.
Fresh packaging was not repeated; the original audit's package equality is historical,
and a later attempt to read its wheel met a filesystem permission error.

PAC-015 retains model/native qualification. PAC-005/PAC-006 retain the earlier
symbol-inventory and selective-patch closure debt. This repair does not reaccept
their older source-bound organism claims or absorb their unfinished nodule.
