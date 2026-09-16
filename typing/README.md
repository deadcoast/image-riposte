# MIVIM.spec mypy-engineer / source-derived typing

This work defines the existing RIPOSTE interfaces without changing application
source. The original typing review preceded PACER setup. The current
[`../AGENTS.md`](../AGENTS.md) preserves the user's source-change restriction
for this assignment. The live PACER registers index the existing contracts and
their evidence; they do not certify application behavior.

The external stub tree covers all 38 Python modules. The shared declarations in
[`stubs/_riposte_types.pyi`](stubs/_riposte_types.pyi) define 27 record shapes,
callback types, and callable model protocols. They preserve existing states such
as `UNVERIFIED`, `INCOMPLETE`, nullable PSNR, absent publication-item fields, and
empty optional model paths. Types do not confer model efficacy or visual approval.

| Source owner | Types derived from it |
| --- | --- |
| `sanitize.py`, `policy.py` | Audited PNG records, decoded image/stat data, date sources, size bins |
| `store.py`, `organizer.py` | Catalog rows, read-only plans, apply/audit/upgrade records, lock context manager |
| `metrics.py`, `quality.py` | Nullable fidelity measurements, transport rows, quality policy/results, uint8 budgets |
| `publication.py` | Recipe fields, plan tasks, optional item fields, batch summaries, export records |
| `models.py`, engine modules | Preflight/runtime records, configuration dataclasses, callable adapter protocols |
| `terminal/`, `cli.py`, `server.py` | Request values, callbacks, worker/state/renderer APIs, CLI aliases, request models, job records |

[`../mypy.ini`](../mypy.ini) integrates the stubs through `mypy_path` and enables
strict checking of the declarations and static consumer fixture. This uses
[mypy's documented external-stub mechanism](https://mypy.readthedocs.io/en/stable/stubs.html).
The directory is not on Python's runtime import path, is not packaged into the
application wheel, and does not add `py.typed` or claim installed-package support.
Consumers that need helper records should import them inside `TYPE_CHECKING`.

Run from the repository root:

```powershell
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
```

The isolated uv project and lockfile pin mypy 2.3.1 and Typer 0.26.8. The checker
uses the available Python 3.13 interpreter and its own environment. The
application environment, root `pyproject.toml`, and existing tests are untouched.
The inherited `VIRTUAL_ENV` warning is expected: do not use `--active`, which
would select the application environment instead.

The command checks source hashes and 286 source/stub signatures, runs strict
mypy, checks 35 leaf modules with stubtest, verifies nine offline fixture tests,
and requires exactly 13 expected diagnostics from invalid consumers. The two
package initializers and executable `__main__` are covered statically; they are
not passed to recursive stubtest. Importing `__main__` would launch the app.

Four exact entries in [`stubtest-allowlist.txt`](stubtest-allowlist.txt) account
for Typer's `Annotated` aliases and `ArgumentInfo` default sentinels. There are no
blanket module exceptions. Source-signature parity still checks the two affected
callback signatures, and consumer assertions check both aliases. As explained by
[mypy's stubtest documentation](https://mypy.readthedocs.io/en/stable/stubtest.html),
runtime introspection cannot prove function return types; the fixture checks
provide separate evidence for the particular record-producing paths they run.

Current verification is recorded in [`evidence/verification.json`](evidence/verification.json):

| Check | Verified result |
| --- | --- |
| Strict declarations and consumer fixture | 40 files; no errors |
| Source parameter parity | 286 signatures |
| Runtime signature comparison | 35 leaf modules; four documented exceptions |
| Incorrect consumer calls | All 13 expected errors; exact line and error-code match |
| Offline record fixtures | 9 tests passed |
| Application source identity | All 50 snapshotted files unchanged |

The fixtures use temporary artwork only. Publication states and the export
record use synthetic data; the export test injects ZIP bytes. They do not run
models, establish real publishing success, open viewers, or launch the UI.
The records module is loaded privately by the fixture validator solely to inspect
its `TypedDict` declarations; application code never imports it.

The source implementation has a separate, deliberately failing audit:

```powershell
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py --source
```

This command removes ambient `MYPYPATH` and uses
[`mypy-source.ini`](mypy-source.ini), so the external declarations cannot hide
implementation errors. It currently reports **817 errors in 34 of 38 files** in
the isolated core environment, including 25 missing optional ML-import errors.
This is a baseline, not 817 proven runtime defects. The largest categories are
373 untyped calls, 268 missing function annotations, and 60 bare generic types.
Full logs are in [`evidence/source-current.txt`](evidence/source-current.txt).

The first Python 3.11 target attempt stopped before a complete check because
installed NumPy 2.5.3 declarations use newer syntax. That failure is preserved in
[`evidence/source-baseline.txt`](evidence/source-baseline.txt). The source's
declared Python 3.11 minimum was not changed or certified by this work. The
validated typing configuration targets Python 3.13.

The contract layer is not fully free of dynamic types. The current
[`evidence/dynamic-boundaries.json`](evidence/dynamic-boundaries.json) lists 89
declarations containing explicit `Any`, `Report`, or `ModelTensor`. They cover
optional Torch/Diffusers internals, extensible JSON reports/model configuration,
dynamic form state, decorators and platform-specific terminal state. Model
protocols check callable shape; `ModelTensor = Any` does not check tensor dtype,
dimensions, gradients, or optional provider APIs. The service dispatcher and
worker results are opaque `object` values that require caller narrowing.

Source bodies remain authoritative. The runner rejects hashes that differ from
[`evidence/source-before.json`](evidence/source-before.json), including changes
made by the other active agent. Re-review affected declarations and fixtures
before replacing that reviewed snapshot. Do not regenerate it merely to silence
the drift check. `stubgen` output alone is not sufficient: this review corrected
omitted tuple-assigned fields, callback shapes, dictionary schemas, Pydantic
defaults, enum constructors, preview-cache keys, and actual optional-path values.

One source finding is left for the source-owning agent: on this Windows host,
`decode_clean(...).source_stat` comes from `os.fstat`, while the organizer later
compares it with `Path.stat()`. Their `st_ctime_ns` values differed for unchanged
temporary inputs under both Python 3.13.9 and the application's Python 3.14.3.
The Python 3.13 fixture observed `SOURCE_CHANGED_OUTPUT_RETAINED`, leaving
organization `INCOMPLETE`. No source repair or bypass was introduced.
[`probe_windows_stat.py`](probe_windows_stat.py) reproduces the stat comparison;
the evidence is in [`windows-stat-probe.txt`](evidence/windows-stat-probe.txt) and
[`windows-stat-probe-app-py314.txt`](evidence/windows-stat-probe-app-py314.txt).
The latter proves the mismatch in the application interpreter, not a complete
organization run there. Its temporary paths and image data are synthetic.

Initial stub, consumer-harness, and runtime-fixture failures remain in `evidence/`
alongside the final results. Later passing contract checks do not supersede the
source audit or the Windows finding.

The PACER file inventory can be reconciled without importing application code:

```powershell
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/pacer_inventory.py
```

It compares scoped files, static declarations/imports, local module dependencies,
source/stub pairing, and the reviewed source snapshot with `overlord.PACER.csv`.
`--plan typing/.cache/pacer-index-plan.json` writes proposed guarded operations;
it does not edit the registers. Inspect and apply the plan through PACER with a
current task receipt. A failing audit returns a nonzero exit status even when a
plan was written. Renames and removed assets need explicit review.

`Exports` records syntactic declarations, including class methods and private
names; it is not a guarantee about Python's dynamic export behavior. The index
excludes build/history trees and caches. Run the external contract checker before
acceptance: a recorded pass read by the inventory is not a fresh test execution.
The inherited 50-file identity snapshot includes six generated `.egg-info` files
alongside 44 application files; the inventory labels those generated inputs.
Existing source/stub definitions are indexed in FILE exports and the JSON report.
The new inventory tool's functions also have individual overlord symbol rows.
