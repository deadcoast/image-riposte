# PAC-040 / reusable publishing recipes

Authority: "CONTINUE development utilizing the NEXT PAC", following PAC-039.
NDL-026 admits this stage and OGM-027 defines its bounded requirement. The exact
checkpoint is [todo-audit.PACER.md](../../todo-audit.PACER.md).

## Implementation

One bounded version-1 library stores eight supported publishing settings in the
workspace's private state. List, inspection and draft previews create no state.
An explicit save validates the complete library, takes the workspace lease,
checks the reviewed revision again, flushes a private temporary file, rechecks
the revision and atomically replaces the library. Unknown/private fields,
duplicate keys/names, unsupported versions, hard links, bad settings and stale
revisions are rejected. Existing path guards cover linked ancestors; this is
cooperation with the application's locks, not hostile operating-system isolation.

CLI `recipes`, publishing `--recipe`, terminal l/s controls and browser recipe
controls use the same backend. Explicit flags override named settings; omitted
flags retain them. Terminal/browser loads pin the selected entry, preserve paths,
models and selection, and never approve images or start processing. Current
engine validation, per-batch model identities and combined-sort preview binding
remain in force. Custom sizes, edge order and seed survive browser loading.
The library supports replacing a named recipe; deletion/import/export is outside
this stage's admitted scope.

## Executed evidence

- `focused.xml`: 58 passed, one Windows symlink privilege skip. Storage privacy,
  corrupt/versioned state, stale saves, replace failures, legacy namespace,
  leases, command/API adapters, shutdown rejection and terminal interactions.
- `suite.xml`: 1,578 passed, ten platform skips, four native tests run separately.
  `suite-first.xml` retains an earlier state-polling failure during a sort: the
  response did not contain `jobs`. Its cause is unconfirmed. The four affected
  parametrizations pass in `sort-poll-recheck.xml`; the full rerun also passes.
  No test assertion was weakened for that failure.
- `native.xml`: four real Chromium tests passed. The recipe case uses the actual
  authenticated local server for preview/save/load, a concurrent save conflict
  and a catalog publishing preview. Slow-load and offline responses are injected
  only for those recovery checks. Other tests cover category, duplicate and
  publication-review workflows. Wide, 390px and open-select screenshots were
  inspected. No claim of the user's live VS Code or terminal host acceptance.
- Initial browser startup/CDP failures under the restricted sandbox are retained
  in `interfaces-second.xml`, `browser-first.xml`, `browser-baseline.xml` and
  `browser-edge-first.xml`. Existing category startup also failed there. The
  first unsandboxed attempt hit a shared pytest-directory permission failure;
  an isolated temporary directory allowed the native checks to run.
- `contracts-first.txt`: seven external declaration stages passed, 554 signatures,
  64 importable modules and 77 application files; all 13 negative consumers keep
  their exact expected diagnostics. `contracts-before-review.txt` retains the
  detected source drift and missing declarations before review.
- `raw-source.txt`: strict implementation typing remains **FAIL**, 841 diagnostics
  in 36 of 67 Python files. Sixteen added diagnostics concern interface functions
  and calls to existing untyped rendering helpers. The new storage module has
  no raw diagnostics. No typing configuration, suppression or dynamic declaration
  allowance was relaxed. `raw-source-first.txt` is a rejected command option,
  not a completed audit; `raw-source-second.txt` retains the earlier 844 result.
- `documentation.json`, `build.txt`, `verification.json`: shipping parser and
  command inventory, local links, historical payload preservation, fresh
  wheel/sdist byte equality and current guide inclusion. This uses existing
  dependencies and does not qualify a clean installation (PAC-034 is shelved).
- `ui-static.json`, `ui-review.json`: 84 generic static findings with scoped
  dispositions; no global static UI pass. Optional design.md lint was unavailable
  offline (`design-lint.txt`, ENOTCACHED); the existing project prose contract was
  reviewed directly. No independent human accessibility,
  useful editing or protection efficacy claim follows from these checks.
- `inventory-final.txt`, `acceptance-review.json`, `OGM-*.json`, `governance.json`:
  guarded source/symbol registration and scoped requirement acceptance. Earlier
  evidence and the failed attempts remain intact.

## Reproduction

From the repository root, using the existing uv environments:

```powershell
.venv/Scripts/python.exe -m pytest -q tests/test_recipes.py tests/test_recipe_interfaces.py -k "not browser_native" --junitxml=evidence/publishing-recipes/focused.xml
.venv/Scripts/python.exe -m pytest -q -k "not browser_native and not native_browser and not browser_review_in_real_chromium" --junitxml=evidence/publishing-recipes/suite.xml
.venv/Scripts/python.exe -m pytest -q -k "browser_native or native_browser or browser_review_in_real_chromium" -o cache_dir=.tmp/publishing-recipes/native-cache --junitxml=evidence/publishing-recipes/native.xml
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py --source --source-python .venv/Scripts/python.exe
uv build --offline --no-build-isolation --cache-dir typing/.cache/uv --out-dir .tmp/publishing-recipes/dist
.venv/Scripts/python.exe evidence/publishing-recipes/verify.py
```

The native test needs local Node/Chromium and permission to start an isolated
browser profile. This run used a new dedicated pytest temporary directory to
avoid crossing ownership with the sandbox account's shared pytest directory.
Final verification compares retained test results and current package/source
bytes; it does not rerun every test or promote synthetic models to efficacy proof.
