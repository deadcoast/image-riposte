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
