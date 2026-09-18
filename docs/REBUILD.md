# Build and run this checkout

Use the existing uv-managed project and lockfile:

```powershell
uv sync --frozen
uv run --frozen riposte --version
uv run --frozen riposte
```

The default palette is `goks`; `--theme light`, `--theme mono` and `--theme dark`
select foreground alternatives. The host terminal owns every background.
`uv sync --frozen --extra lab` installs optional processing dependencies without
downloading model weights. Selecting a workspace and previewing organization
remain read-only; source replacement requires an explicit Apply request or REPLACE.

For development checks, use `uv sync --frozen --extra test`, then
`uv run --frozen --extra test python -m pytest`. See [PATCH-v05-MERGE.md](PATCH-v05-MERGE.md)
for known baseline failures and the scope actually verified on this host.

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
