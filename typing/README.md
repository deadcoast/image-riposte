# MIVIM.spec mypy-engineer / source-derived typing

The original typing assignment defined existing RIPOSTE interfaces without
changing application source. PAC-004 subsequently authorized the selective 0.5
terminal patch; the affected declarations were re-reviewed and extended.
[`../AGENTS.md`](../AGENTS.md) preserves both the original boundary and that
scoped exception. The subsequent user instruction, "Implement the listed repairs,
including source and test changes", authorizes the development-audit repairs.
Affected declarations and fixtures were reviewed against those changes. The live PACER registers index the existing contracts and
their evidence; they do not certify application behavior.

The external stub tree covers all 41 Python modules. The shared declarations in
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

[`mypy-contracts.ini`](mypy-contracts.ini) integrates the stubs through `mypy_path`
and enables strict checking of the declarations and static consumer fixture. This uses
[mypy's documented external-stub mechanism](https://mypy.readthedocs.io/en/stable/stubs.html).
The directory is not on Python's runtime import path, is not packaged into the
application wheel, and does not add `py.typed` or claim installed-package support.
Consumers that need helper records should import them inside `TYPE_CHECKING`.

The default [`../mypy.ini`](../mypy.ini) checks application implementation.
From the repository root, both commands reach the same 41 source modules:

```powershell
mypy
mypy .
```

Recursive discovery excludes build/distribution/history copies and the separate
tests, scripts and typing trees. No application module is excluded and the
default configuration does not load the external stubs. The configured target
remains Python 3.13, including when mypy runs in the Python 3.14 environment.
The patch-era commands exited 1 with 962 strict diagnostics in the core
environment; those results are historical, not a passing-contract shortcut.
The pre-patch 817-diagnostic discovery results are retained in
[`evidence/pac-003-before.json`](evidence/pac-003-before.json) and
[`evidence/pac-003-root-audit.json`](evidence/pac-003-root-audit.json).
Historical results are in [`../evidence/patch-v050/root-mypy.json`](../evidence/patch-v050/root-mypy.json).

Run the independent external contract suite from the repository root:

```powershell
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
```

The isolated uv project and lockfile pin mypy 2.3.1 and Typer 0.26.8. The checker
uses the available Python 3.13 interpreter and its own environment. The
typing runner does not synchronize the application environment or modify source.
The separate PAC-004 merge updated the application version and installed locked
test dependencies. The subsequent authorized audit repairs modify backend source
and tests; their evidence is in [`../evidence/development-repairs/README.md`](../evidence/development-repairs/README.md).
The inherited `VIRTUAL_ENV` warning is expected: do not use `--active`, which
would select the application environment instead.

For only the declaration/consumer check, use
`uv run --project typing --frozen --cache-dir typing/.cache/uv python -m mypy --config-file typing/mypy-contracts.ini`.

The suite checks source hashes and 318 source/stub signatures, runs strict
mypy on contracts and its three tooling modules, checks 38 leaf modules with
stubtest, verifies nine offline fixture tests and ten tooling regressions,
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
| Strict declarations and consumer fixture | 43 files; no errors |
| Strict typing of the checker, inventory and tooling tests | 3 files; no errors |
| Source parameter parity | 318 signatures |
| Runtime signature comparison | 38 leaf modules; four documented exceptions |
| Incorrect consumer calls | All 13 expected errors; exact line and error-code match |
| Offline record fixtures | 9 tests passed |
| Tooling regressions | 10 tests passed, including discovery, interpreter selection, source identity and missing-symbol/dependency detection |
| Application source identity | All 47 application files match the reviewed snapshot |

The fixtures use temporary artwork only. Publication states and the export
record use synthetic data; the export test injects ZIP bytes. They do not run
models, establish real publishing success, open viewers, or launch the UI.
The records module is loaded privately by the fixture validator solely to inspect
its `TypedDict` declarations; application code never imports it.

The source implementation has a separate audit:

```powershell
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py --source
```

This command explicitly uses the application's `.venv` Python, even when its
runner starts in the isolated typing project. It removes ambient `MYPYPATH`
and uses [`mypy-source.ini`](mypy-source.ini). Interpreter identity, dependency
versions, the exact command and source hashes are saved in
[`evidence/source-current-command.json`](evidence/source-current-command.json).
For a deliberate comparison, pass `--source-python PATH_TO_PYTHON`.

The application-environment run reports 973 diagnostics; the earlier isolated
core run reported 980. They include annotation errors and untyped calls, not
equivalent counts of runtime defects. The prior core output remains in
`../evidence/development-repairs/raw-source.txt`; current output is in
[`evidence/source-current.txt`](evidence/source-current.txt). The original
817-error source audit remains in `../evidence/patch-v050/before-source-current.txt`.

The first Python 3.11 target attempt stopped before a complete check because
installed NumPy 2.5.3 declarations use newer syntax. That failure is preserved in
[`evidence/source-baseline.txt`](evidence/source-baseline.txt). The source's
declared Python 3.11 minimum was not changed or certified by this work. The
validated typing configuration targets Python 3.13.

The contract layer is not fully free of dynamic types. The current
[`evidence/dynamic-boundaries.json`](evidence/dynamic-boundaries.json) lists 92
declarations containing explicit `Any`, `Report`, or `ModelTensor`. They cover
optional Torch/Diffusers internals, extensible JSON reports/model configuration,
dynamic form state, decorators and platform-specific terminal state. Model
protocols check callable shape; `ModelTensor = Any` does not check tensor dtype,
dimensions, gradients, or optional provider APIs. The service dispatcher and
worker results are opaque `object` values that require caller narrowing.
The inventory resolves shared dynamic aliases by their imports; the new fully
structured terminal `Report` dataclass does not count as the shared dynamic report type.

Source bodies remain authoritative. The runner rejects application hashes that differ from
[`evidence/source-reviewed-repairs.json`](evidence/source-reviewed-repairs.json).
The repair review covered streamed-body middleware, version re-exports, optional
gradient probes, source identity, and publication status/revocation fixtures.
The previous [`evidence/source-reviewed-v050.json`](evidence/source-reviewed-v050.json)
is retained as historical evidence.
PAC-004 reviewed the incoming terminal implementation, matched its signatures and
re-exports, added three module stubs and new consumer assertions, and ran stubtest
before accepting this 47-file baseline. The original
[`evidence/source-before.json`](evidence/source-before.json) retains all 50 entries,
including six generated `.egg-info` files, and is not replaced. Generated metadata
and bytecode remain outside application identity. Review affected declarations
and fixtures before deliberately admitting another source revision; do not refresh
the baseline just to silence drift. The selective patch and its proof boundary are
recorded in [`../docs/PATCH-v05-MERGE.md`](../docs/PATCH-v05-MERGE.md).
Regression tests prove that changed, added and deleted application files still
alter source identity. `stubgen` output alone is not sufficient: this review corrected
omitted tuple-assigned fields, callback shapes, dictionary schemas, Pydantic
defaults, enum constructors, preview-cache keys, and actual optional-path values.

The original source finding was: on this Windows host,
`decode_clean(...).source_stat` comes from `os.fstat`, while the organizer later
compares it with `Path.stat()`. Their `st_ctime_ns` values differed for unchanged
temporary inputs under both Python 3.13.9 and the application's Python 3.14.3.
The Python 3.13 fixture observed `SOURCE_CHANGED_OUTPUT_RETAINED`, leaving
organization `INCOMPLETE`. The authorized repair now compares descriptor state
with descriptor state and pathname state with pathname state, retaining replacement
and in-place mutation detection. The fixture now requires successful organization.
[`probe_windows_stat.py`](probe_windows_stat.py) reproduces the stat comparison;
the evidence is in [`windows-stat-probe.txt`](evidence/windows-stat-probe.txt) and
[`windows-stat-probe-app-py314.txt`](evidence/windows-stat-probe-app-py314.txt).
The latter proves the mismatch in the application interpreter, not a complete
organization run there. Its temporary paths and image data are synthetic.

Initial stub, consumer-harness, and runtime-fixture failures remain in `evidence/`
alongside the final results. Later passing contract checks do not supersede the
source audit or erase the original Windows finding. Pre-repair typing evidence is
also retained in `../evidence/development-repairs/typing-before/`.

The PACER file inventory can be reconciled without importing application code:

```powershell
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/pacer_inventory.py
```

It compares scoped files, static declarations/imports, local module dependencies,
source/stub pairing, and the reviewed source snapshot with `overlord.PACER.csv`.
It also requires individual source symbol rows for module-level declarations
(including constants and private helpers) and direct class methods. Dependencies
include statically named local declarations and imported symbols. File exports
alone cannot satisfy symbol coverage. Nested implementation closures and external
library declarations remain represented by their owners; computed runtime dispatch
is not asserted to be a complete static call graph.
`--plan typing/.cache/pacer-index-plan.json` writes proposed guarded operations;
it does not edit the registers. Inspect and apply the plan through PACER with a
current task receipt. A failing audit returns a nonzero exit status even when a
plan was written. Renames and removed assets need explicit review.

`Exports` records syntactic declarations, including class methods and private
names; it is not a guarantee about Python's dynamic export behavior. The index
excludes build/history trees and caches. Run the external contract checker before
acceptance: a recorded pass read by the inventory is not a fresh test execution.
The inventory still registers and hashes generated `.egg-info` inputs separately;
its application identity comparison uses the same 47-file scope as the checker.
Source/stub definitions are indexed in FILE exports and the JSON report, with
source symbol rows checked independently. Previously authored extra dependency
edges are retained. Missing, duplicate, retired or insufficiently linked symbol
records cause a nonzero result.
