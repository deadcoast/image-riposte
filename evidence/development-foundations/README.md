# Development foundations follow-up

Continuation of the authorized audit repairs and existing PAC-005 inventory task.
The application changes and full-suite results remain in
[development-repairs](../development-repairs/README.md). This follow-up changes
typing tools, their regressions and PACER records; all 47 application files still
match the reviewed repair snapshot.

## Implemented

- `typing/check.py --source` explicitly selects the application's `.venv` Python,
  even when invoked from the isolated typing project. `--source-python` permits
  a deliberate comparison. The command, interpreter, dependency versions and
  source hashes are retained in `typing/evidence/source-current-command.json`.
- `typing/pacer_inventory.py` requires individual records for every module-level
  source declaration and direct class method, including private helpers and
  constants. It checks owner and statically identifiable local dependencies.
  Imported aliases and direct method references resolve; locally shadowed names
  do not create false imported dependencies. PACER's CONFIG type represents
  module data declarations. Existing reviewed extra edges remain intact.
- Missing symbols and required edges fail reconciliation. File export lists
  cannot satisfy symbol coverage. Nested closures and external declarations are
  represented by their owners; this is a static index, not a runtime call graph.

## Executed checks

| Check | Result |
| --- | --- |
| Source and stub signatures | 318 matched; 38 importable leaf modules |
| Contract mypy, tooling mypy and stubtest | PASS |
| Runtime contract fixtures | 9 passed |
| Tooling regressions | 10 passed, including missing symbol and missing edge controls |
| Invalid consumer fixtures | All 13 expected line/code diagnostics matched |
| Inventory reconciliation | PASS: 143 files, 440 source symbols, 9 inventory-tool functions, 1,723 symbol dependencies |
| Reviewed application source | All 47 files unchanged |

Commands:

```powershell
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/pacer_inventory.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py --source
```

[contracts.txt](contracts.txt) and [inventory.txt](inventory.txt) retain the final
outputs. Initial tooling failures and the pre-registration inventory failure are
retained separately. The source audit ran in application Python 3.14.3 with mypy
2.3.1, Torch 2.14.0, Diffusers 0.40.0 and Transformers 5.17.0. It reports 973
annotation diagnostics (exit 1), compared with 980 in the earlier isolated core
environment. These counts are environment-specific typing observations, not
counts of runtime failures. The exact current output and environment are in
`typing/evidence/source-current.txt` and `typing/evidence/source-environment.json`;
[app-source-initial.txt](app-source-initial.txt) retains the initial application
environment check. Source annotation cleanup is separate from this repair scope.

## Remaining register correction

PAC-006 retains the historical NDL-003 `NewAssets` correction. That field contains
prose and OVR identifiers where the installed PACER absorption validator expects
literal asset paths. Its guarded setter rejects removal or replacement of any
admitted token. Completing PAC-005 removes the inventory prerequisite; it does
not by itself repair this older nodule field. A supported history-preserving
correction is still needed. No register guard was bypassed and no admitted scope
was removed.
