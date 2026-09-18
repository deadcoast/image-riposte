# PAC-020 independent workflows

Implemented the user's explicitly requested Sort, RIPOSTE and Sort + RIPOSTE in
the existing interactive terminal and direct Typer CLI. Existing command names
remain registered. The browser retains its existing interface; adding browser
forms was not part of this two-interface change.

OBSERVED verification:

- Full application suite: **852 passed, 7 skipped, 1 failed**. The failure was
  the Chromium debugging connection inside the sandbox. Original output is
  retained in `pytest.txt` and `pytest.xml`.
- All browser regressions rerun outside the sandbox: **21 passed** in
  `browser.txt` and `browser.xml`, including the failed native-browser case.
- New workflow regressions: **28 passed**, included in the full-suite output.
  Real codecs, storage, CPU optimization, review and ZIP export ran with a
  synthetic differentiable encoder. Cases cover originals preserved, recursive
  selection, no-write previews, unrelated additions, selected-source tampering,
  snapshot tampering, interrupted resume after originals disappear, incomplete
  intake cleanup, incremental sort without models, combined consent/preflight/
  failure/retry, direct command parity, terminal controllers and linear input.
- External contracts pass all stages (`typing.txt`): 326 signatures, 39 leaf
  modules, 44 strict contract files, 9 record fixtures, 10 tooling regressions,
  and all 13 expected negative consumer diagnostics. This is separate from
  strict typing of implementation bodies: the fresh raw-source audit reports
  **1,013 errors in 37 files (42 checked)**, versus the previous 973 errors in
  36 files (41 checked). These diagnostics remain visible in
  `typing/evidence/source-current.txt`; passing external contracts does not
  resolve them.

Earlier attempts are retained here as observations: the initial compatibility
run had 70 passes and 75 fixture-setup errors because `.tmp` did not exist;
creating the temporary parent produced 145 passes. An initial new test asserted
mixed-case display text against an uppercase heading (19 passes, 1 failure);
correcting the assertion produced 20 passes. Expanded recovery tests exposed a
real missing-path diagnostic being reported as a link (27 passes, 1 failure);
explicit `lstat` error handling fixed it and all 28 passed. The first typing
check correctly rejected source drift before the reviewed declarations and new
snapshot were admitted. No failing check was converted into a product-success
claim.

Bounds: seven skips are three Windows symlink-privilege cases and four POSIX
pseudo-terminal cases. Terminal rendering was checked at 79x24, 100x34 and
132x46; no native Windows raw-keyboard acceptance or pretrained-model/GPU run
is claimed. Numerical quality, visual acceptance, and protection efficacy remain
separate. All model-executing workflow tests use a synthetic encoder. Optional
workshop qualification retains its existing separate contracts.

Reproduce from the repository root (create `.tmp` before using these basetemps):

```powershell
.venv/Scripts/python.exe -m pytest -q --basetemp .tmp/workflows-full-01 --junitxml evidence/workflows/pytest.xml
.venv/Scripts/python.exe -m pytest -q tests/test_browser_review.py --basetemp .tmp/workflows-browser-02 --junitxml evidence/workflows/browser.xml
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py --source
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/pacer_inventory.py
```
