# Build and run this checkout

Use the existing uv-managed project and lockfile:

```powershell
uv sync --frozen
uv run --frozen riposte --version
uv run --frozen riposte ui "D:\Artwork\SocialSamples"
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

The independent Sort, RIPOSTE and Sort + RIPOSTE workflows add no dependencies
or workspace migration. `uv sync --frozen` already installs this checkout in
editable mode. `START.ps1` and `START.sh` now also check that the imported package
comes from this checkout's `src/riposte`; an older copied install is refreshed
in editable mode even if both versions are `0.5.0`. Later source-only edits are
then immediately visible. Existing `riposte.cmd` and console entry points route
to that same package and need no command-specific configuration.

For this Windows checkout, launch the interactive terminal with:

```powershell
.\START.ps1 -ArtworkFolder "D:\Artwork\SocialSamples"
```

Use an existing artwork folder outside the application directory. Select Sort,
RIPOSTE or Sort + RIPOSTE in the menu. Local models are needed only for protection;
previews and sorting work without them. Add `-Lab` only if the optional model
dependencies are not installed. Historical release archives remain historical;
build a fresh distribution to distribute the current workflows.
