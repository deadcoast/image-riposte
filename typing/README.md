# RIPOSTE / source-derived external typing

Current project/milestone status is in [PROJECT-STATUS.md](../docs/PROJECT-STATUS.md).
The Markdown audit is active and the PACER CSV TODO is frozen. This guide's
current counts come from `evidence/verification.json`; earlier task records below
remain historical. On 2026-09-18 the 56 current application hashes and all 387
source/stub signatures were rechecked. The retained full contract result is
passing; the separately retained, source-matching implementation audit still
reports 1,103 diagnostics in 37 of 49 Python files.

PAC-027BB reviews frozen category plans, private title-table validation, journal
version 2 and exact assignment restoration, stable video relocation, category
path validation, and CLI/service/terminal/API contracts. The browser controller
has separate rule-draft and destination-preview consent with stale response
checks. `source-reviewed-category-sort.json` is the current reviewed source
identity; earlier snapshots remain historical. Original filenames are excluded
from public catalog rows, PNG metadata and publishing packs, and retained in the
private title table/recovery journals only. Per-file plans and private journal
records remain explicitly dynamic dictionaries at the external type boundary.
These declarations do not establish source-body type safety or model efficacy.
Current parity covers 387 signatures, 46 importable leaf modules and 56 application
files (49 Python modules). See `../evidence/category-sort/README.md` for runtime and browser proof boundaries.


Historical PAC-027BA added private versioned category rules and CLI/shared-service preview,
save and match review. `source-reviewed-category-rules.json` admits the new
`category_rules` module, the CLI command, service dispatch/effects and discovery
next-action copy; the other 49 application files match the preceding snapshot.
The immutable rule records and new command signature were reviewed against their
external declarations. That milestone covered 375 signatures, 44 importable leaf
modules and 53 application files (47 Python modules). Runtime persistence and
compatibility evidence lives in `../evidence/category-rules/`. Category movement,
original-title provenance and assignment recovery were left to PAC-027BB. Contract
passes remain separate from the failing raw-source audit and model acceptance.

PAC-027A implemented the first milestone of the user-resumed filename-category
plan: read-only discovery and session category drafts. The new `title_categories`
module and CLI signature were reviewed; the service, action schema, controller
shortcut, help and semantic report changes retain their existing signatures.
`source-reviewed-title-discovery.json` admits these seven application files after
checking every other application hash against the prior sort-collision snapshot.
The new stub exposes immutable draft records and existing dynamic report boundaries.
Runtime evidence is in `../evidence/title-discovery/`; saved rules, category routing,
private title recovery and undo integration were left to PAC-027B. External contract
passes do not imply a clean raw-source mypy audit or model qualification.
At that milestone parity covered 363 source signatures, 43 importable leaf modules and
52 application files. Its raw-source audit reported 1,073 errors in 37
files; the new filename module has no raw-source diagnostics.

The original typing assignment defined existing RIPOSTE interfaces without
changing application source. PAC-004 subsequently authorized the selective 0.5
terminal patch; the affected declarations were re-reviewed and extended.
[`../AGENTS.md`](../AGENTS.md) preserves both the original boundary and that
scoped exception. The subsequent user instruction, "Implement the listed repairs,
including source and test changes", authorizes the development-audit repairs.
Affected declarations and fixtures were reviewed against those changes. The live PACER registers index the existing contracts and
their evidence; they do not certify application behavior.

PAC-020's explicit user request authorizes the independent Sort, RIPOSTE and
combined workflows. The affected publication/CLI declarations, request and batch
records, terminal field exports, and new `intake` module were reviewed against
the implementation. `source-reviewed-workflows.json` records this reviewed state;
the earlier snapshots remain historical. Runtime workflow evidence is separate
in [`../evidence/workflows/README.md`](../evidence/workflows/README.md).

PAC-022 authorizes menu-first startup and an action-specific file/folder browser.
The new `terminal.paths` declarations, controller entry/browse methods, renderer
entry, and preserved command/form signatures were reviewed against the source.
`source-reviewed-menu.json` records that review; earlier snapshots remain
historical. Copy-only changes retain JSON keys and all model/engine contracts.
Runtime, launcher, and native Windows evidence is separate in
[`../evidence/menu-startup/README.md`](../evidence/menu-startup/README.md).

PAC-023 authorizes undo, preview validation and sort-only video compatibility.
The organizer, media paths, CLI and recovery/video modules were reviewed against
their implementation. Organization reports now declare private recovery history
and distinguish date-only image outputs from unchanged video bytes. New video
and undo report records describe that boundary. The current reviewed snapshot is
`source-reviewed-sort-recovery.json`; previous snapshots remain historical.
At that milestone, external validation covered 356 signatures, 42 importable leaf modules
and 51 application files. Source-body mypy remains a separate failing audit;
these external checks do not imply a clean implementation type check.

PAC-024 continues the authorized sort/recovery work by checking source identity
and bytes again after saving the removal-intent journal. The only application
change is inside `SortHistory.remove_source`; its parameters, return behavior
and journal record fields remain compatible with the reviewed declarations.
`source-reviewed-sort-commit.json` admits that specific change and verifies that
the other 50 application files match the preceding snapshot. Failed reproductions
and runtime checks are retained in
[`../evidence/sort-commit-safety/README.md`](../evidence/sort-commit-safety/README.md).

PAC-025 continues the requested core sorting work with per-operation destination
reservations and journal entries saved before post-backup source validation.
The organizer's private allocation helper gains an optional keyword-only counter
map; its declaration was updated. `SortHistory.prepare` retains its signature
and record shape. `source-reviewed-sort-partial.json` admits these two reviewed
modules and verifies the other 49 application files against the previous snapshot.
Failure reproductions and runtime evidence are retained separately in
[`../evidence/sort-partial-failures/README.md`](../evidence/sort-partial-failures/README.md).

PAC-026 continues core sorting polish with exclusive image publication and
recovery records that release confirmed rejected output paths. The store and
copy helper signatures remain compatible; `SortHistory.reject_output` is declared
with the existing journal entry record and a `None` return. Existing nullable
output/expected fields still describe the journal, without a format change.
`source-reviewed-sort-collisions.json` admits the three reviewed modules and
verifies that the other 48 application files match the previous snapshot.
At that milestone, external parity covered 357 signatures; runtime evidence remains separate
in [`../evidence/sort-collisions/README.md`](../evidence/sort-collisions/README.md).

The external stub tree covers all 49 Python modules. The shared declarations in
[`stubs/_riposte_types.pyi`](stubs/_riposte_types.pyi) define the shared record shapes,
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
From the repository root, both commands target the same 49 Python source files:

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

The suite checks source hashes and 387 source/stub signatures, runs strict
mypy on contracts and its three tooling modules, checks 46 leaf modules with
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

Retained verification for the current reviewed source is recorded in
[`evidence/verification.json`](evidence/verification.json). These full-suite
results are distinct from the fresh parity/hash review described above:

| Check | Verified result |
| --- | --- |
| Strict declarations and consumer fixture | 51 files; no errors |
| Strict typing of the checker, inventory and tooling tests | 3 files; no errors |
| Source parameter parity | 387 signatures |
| Runtime signature comparison | 46 leaf modules; four documented exceptions |
| Incorrect consumer calls | All 13 expected errors; exact line and error-code match |
| Offline record fixtures | 9 tests passed |
| Tooling regressions | 10 tests passed, including discovery, interpreter selection, source identity and missing-symbol/dependency detection |
| Application source identity | All 56 application files match the reviewed snapshot |

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

The current retained application-environment run reports 1,103 diagnostics in
37 files (49 checked). The historical repair-era application run reported 973
and its isolated core run reported 980. These include annotation errors and
untyped calls, not equivalent counts of runtime defects. The prior core output remains in
`../evidence/development-repairs/raw-source.txt`; current output is in
[`evidence/source-current.txt`](evidence/source-current.txt). The original
817-error source audit remains in `../evidence/patch-v050/before-source-current.txt`.

The first Python 3.11 target attempt stopped before a complete check because
installed NumPy 2.5.3 declarations use newer syntax. That failure is preserved in
[`evidence/source-baseline.txt`](evidence/source-baseline.txt). The source's
declared Python 3.11 minimum was not changed or certified by this work. The
validated typing configuration targets Python 3.13.

The contract layer is not fully free of dynamic types. The current
[`evidence/dynamic-boundaries.json`](evidence/dynamic-boundaries.json) lists 124
declarations containing explicit `Any`, `Report`, or `ModelTensor`. They cover
optional Torch/Diffusers internals, extensible JSON reports/model configuration,
dynamic form state, decorators and platform-specific terminal state. Model
protocols check callable shape; `ModelTensor = Any` does not check tensor dtype,
dimensions, gradients, or optional provider APIs. The service dispatcher and
worker results are opaque `object` values that require caller narrowing.
The inventory resolves shared dynamic aliases by their imports; the new fully
structured terminal `Report` dataclass does not count as the shared dynamic report type.

Source bodies remain authoritative. The runner rejects application hashes that differ from
[`evidence/source-reviewed-category-sort.json`](evidence/source-reviewed-category-sort.json).
The earlier [`repair snapshot`](evidence/source-reviewed-repairs.json) covered
streamed-body middleware, version re-exports, optional
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
its application identity comparison uses the same 56-file scope as the checker.
Source/stub definitions are indexed in FILE exports and the JSON report, with
source symbol rows checked independently. Previously authored extra dependency
edges are retained. Missing, duplicate, retired or insufficiently linked symbol
records cause a nonzero result.
