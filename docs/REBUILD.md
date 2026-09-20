# Build and run this checkout

Current version and audit/milestone limits are in [PROJECT-STATUS.md](PROJECT-STATUS.md).
The root manifest is a development snapshot. Build and verify fresh artifacts at
the completion milestone; historical wheels are not current installation proof.

Use the existing uv-managed project and lockfile:

```powershell
uv sync --frozen --inexact
uv run --no-sync riposte --version
uv run --no-sync riposte
```

The default palette is `goks`; `--theme light`, `--theme mono` and `--theme dark`
select foreground alternatives. The host terminal owns every background.
`uv sync --frozen --inexact --extra lab` installs optional processing dependencies without
downloading model weights. Selecting a workspace and previewing organization
remain read-only; source replacement requires an explicit Apply request or REPLACE.

For development checks, explicitly install with `uv sync --frozen --inexact --extra test`,
then run `uv run --no-sync python -m pytest`. The inexact sync preserves existing
optional dependencies; no-sync runs use the installed environment unchanged.
Use the system temporary directory for test workspaces. A custom pytest
`--basetemp` must be outside this checkout: PAC-030 deliberately rejects image
workspaces under the application, including repository-local test directories.
See [PROJECT-STATUS.md](PROJECT-STATUS.md) and its linked evidence for current
scope. [PATCH-v05-MERGE.md](PATCH-v05-MERGE.md) preserves the earlier merge baseline.

Build a fresh distribution with `uv build`. Archived wheels and manifests inside
`packages/RIPOSTE_v0.5.0.zip` describe its original snapshot. They do not include
the later dependency, typing and selective-merge changes in this checkout.

The independent Sort, RIPOSTE and Sort + RIPOSTE workflows and menu browser add
no dependencies or workspace migration. `uv sync --frozen --inexact` installs this
checkout in editable mode and preserves already installed extras. INSTALL.ps1/sh
perform explicit setup; START.ps1/sh only verify this checkout is installed and
launch its menu. An older copied install requires an explicit INSTALL refresh,
even when its version matches. Source-only updates in an editable checkout are
visible immediately. Console entry points and `riposte.cmd` use the same package.

```powershell
.\INSTALL.ps1        # Setup or explicitly refresh an old installation
.\START.ps1          # Main menu first, no folder argument required
```

Use the menu to choose a workflow before browsing its images or folders. Keep
image/results folders outside the application directory. Optional model runtime
dependencies are installed with `INSTALL.ps1 -Lab`; model weights are selected
separately. Sorting and previews work without model weights. Existing command
names remain available. See [menu verification](../evidence/menu-startup/README.md)
for current scope; historical release archives do not contain these changes.

PAC-031 preview-binding evidence is retained under `evidence/sort-preview/`.
Direct sort fixtures and examples must obtain a fresh preview and supply its
`plan_id` to apply. The combined command uses its top-level combined ID. Source
fixtures still use external temporary workspaces because application-root guards
remain active. `verify.py` checks retained evidence identity; it does not rerun
the suite or reconcile frozen PACER registers.

Historical PAC-032 evidence is under `evidence/catalog-scaling/`. Its `verify.py`
binds the source at that checkpoint and will reject subsequent source changes.
Use the current task's verifier instead. Run its `measure.py`
to rerun the synthetic 16/32/64
image scaling probe in an external temporary workspace. It reports returned SQL
rows and logical JSON bytes, elapsed time and Python allocation peak. These are
not disk-I/O measurements or a whole-sort latency guarantee. The live SQLite
revision guard requires no catalog migration or new dependencies.

Current PAC-033 evidence is under `evidence/source-typing/`. Its `verify.py`
checks current source/evidence identity and the frozen CSV hashes. The ordinary
raw-source command remains `uv run --project typing --frozen --cache-dir
typing/.cache/uv python typing/check.py --source`; 876 diagnostics remain.
`check_consumers.py` checks positive/negative fixtures against explicit source
inputs and retains their output separately. Neither passing external contracts
nor passing consumer checks makes the remaining source-body audit clean.

PCUC-001 supersedes PAC-033 as the current source/evidence snapshot. Use
`evidence/pcuc-shared-views/verify.py` for retained identity checks and its
`--manifest` mode for the root development manifest. `prove.py` checks independent
gradient calculations and saved-tensor bounds; `measure.py` compares preserved
pre-change and current engines. Both use real CPU autograd/codecs and explicitly
synthetic models, not downloaded weights. PAC-034 clean installation qualification
is shelved by user direction; current package checks use existing dependencies.
