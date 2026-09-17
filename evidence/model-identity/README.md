# Model configuration identity

Continued application development: the fixed encoder, inpainting and temporal
adapters now include a `configuration_sha256` digest alongside their existing
weight identities. The digest binds relative file names and content for JSON
and text files at the bundle root and selected component directories. It does
not publish configuration text, resource paths or timestamps. Byte-identical
bundles can move between locations without changing identity.

The adapters compare the digest before and after loading. A detected change
raises `MODEL_CONFIGURATION_CHANGED`. Publication resume's existing identity
comparison now rejects configuration-only changes as
`PUBLICATION_RESUME_MODEL_MISMATCH` before generating further items. Already
committed outputs remain unchanged. This covers encoder configuration,
inpainting tokenizer vocabulary and merges, scheduler settings, component
configuration and temporal preprocessing normalization.

## Reproduction and execution

[Before the repair](red.txt), **12 regressions failed and one control passed**:
configuration-only changes left identities equal; changes during model loading
were accepted; an interrupted batch resumed with modified configuration.
Relocation with unchanged bytes was the passing control.

The final [test module](../../tests/test_model_configuration_identity.py) has 18
cases, including file addition/removal/rename, linked-configuration refusal,
three adapters, interrupted publication and unchanged relocation. Component
fixtures substitute library loaders while exercising the real adapters, CPU
gradients, optimizer and publication storage. A separate test constructs a tiny
randomly initialized AutoencoderKL locally, saves it with the installed
Diffusers serializer, and loads it through the real LocalEncoder. Changing only
`act_fn` from `silu` to `relu` keeps weight hashes equal but changes features and
configuration identity; the actual input gradient remains finite and nonzero.

- [Focused model, temporal and publication tests](focused.txt): **92 passed,
  2 skipped** for unavailable Windows symlink creation privileges.
- [Full application suite](full-suite.txt): **786 passed, 7 skipped**. The skips
  cover three Windows symlink privilege cases and four POSIX terminal host cases.
- [External contracts](contracts.txt): **PASS**, with 319 source/stub signatures,
  stubtest, runtime record fixtures, tooling tests and consumer checks.
- [Static inventory](inventory.txt): **PASS**, including the new helper and its
  adapter dependencies.

```powershell
uv run --frozen --no-sync --cache-dir typing/.cache/uv python -m pytest tests/test_model_configuration_identity.py tests/test_v02_models.py tests/test_v03_temporal.py tests/test_v03_publication.py -q --basetemp typing/.cache/model-identity/focused-final -o cache_dir=typing/.cache/model-identity/pytest-cache
uv run --frozen --no-sync --cache-dir typing/.cache/uv python -m pytest -q --basetemp typing/.cache/model-identity/full -o cache_dir=typing/.cache/model-identity/pytest-cache
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/pacer_inventory.py
```

## Compatibility and contract review

Existing VAE weight hashes retain their original meaning. Preflight without
fingerprinting remains lightweight and omits both digests. The external
`VaeInspection` record adds an optional configuration digest; the new helper
signature and temporal import are declared, and runtime record fixtures check
the optional field. The reviewed source manifest advances only models.py and
temporal.py after that contract review; [source-before.json](source-before.json)
retains the previous manifest.

Older unfinished batches lack the new configuration identity and must be
restarted as new batches. Committed candidates remain reviewable and exportable.
Identity is deliberately byte-sensitive, including JSON whitespace changes.
The digest does not bind installed library or kernel versions. Comparing before
and after loading detects persistent changes across those snapshots; it is not
an atomic filesystem snapshot.
