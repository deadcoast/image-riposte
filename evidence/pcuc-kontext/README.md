# PCUC-005: explicit local Kontext editing experiments

Development intake, 2026-09-19. INFERRED scope of the user's continuing PCUC
authorization: integrate one modern edit backend into the existing committed
generation, cohort and reviewer-panel workflows. PAC-034 remains shelved and all
four PACER registers remain frozen. Prior PCUC-004 identity verification passed.

OBSERVED at intake: LocalGenerator accepted only SD img2img, nine-channel SD
inpainting and SVD. Its shared conditioning record always describes SD strength
and guidance for editing. The installed Diffusers 0.40.0 has FluxKontextPipeline,
but CUDA is unavailable. No pretrained-model or independent-rater qualification
can be inferred from this implementation assignment.

Research -> theory -> formulation -> critique -> development:

- [The authors' Kontext paper](https://arxiv.org/abs/2506.15742) describes image
  context conditioning in a flow transformer. An SD img2img strength setting does
  not describe this task. This integration is one architecture path, not proof
  of family holdout, pretrained weight provenance or modern-family coverage.
- [Diffusers 0.40.0 Kontext implementation](https://raw.githubusercontent.com/huggingface/diffusers/v0.40.0/src/diffusers/pipelines/flux/pipeline_flux_kontext.py)
  and the installed implementation define guidance, latent packing, input resize
  and output-area behavior. Explicit settings must be used in both execution and
  committed records. Default pipeline resizing would otherwise make the measured
  prepared input differ from what the model actually sees.
- A four-level VAE downsamples by 8; packing 2x2 latent patches requires dimensions
  divisible by 16. Choose the nearest aspect ratio from the 17 documented Kontext
  buckets using exact rational distances and lexical ties. Every bucket lies on
  that lattice. Disable automatic input resizing and set output area to prepared
  width*height: sqrt(wh*w/h)=w and sqrt(wh/(w/h))=h, so the pipeline returns the
  same lattice point. Verify the real installed pipeline's numerical path, not
  only a mock keyword dictionary. Initial consideration of reusing the SD 768-pixel
  cap was rejected: it needlessly moves away from Kontext's preferred geometry.
- Pin exact component roles/classes, local safetensors and native CUDA bfloat16.
  Capture names and bytes of component assets including binary tokenizer files;
  recheck after loading. Existing configuration_fingerprint covers JSON/TXT, so
  its scope alone is insufficient for SentencePiece assets. Keep that historical
  function/identity unchanged and use a complete named bundle receipt here.
- Critical limits: a tiny randomly initialized real pipeline can verify loading,
  tensor geometry, deterministic paired inputs and output plumbing; it cannot
  qualify useful editing, pretrained weights, CUDA numerics, memory sufficiency,
  reviewer reliability or protection efficacy. No downloads, dependency changes,
  remote code, automatic adapters or model acquisition are part of this work.

Phases: fixed local bundle and backend; model-aware conditioning/preparation in
ordinary and cohort execution; numerical/library and failure regressions;
existing-workflow, contract, package and frozen-register verification.

## Implemented and verified, 2026-09-19

`kontext.py` implements the fixed local editing backend. `generation.py` selects
it only for a local `FluxKontextPipeline` edit model. `experiment.py` and `cohort.py`
commit its actual settings; all five paired arms use the same prepared geometry
and seed. Existing experiment and panel packets carry that conditioning. SD/SVD
paths retain their existing preparation and execution. CLI usage and local model
requirements are in [CLI.md](../../docs/CLI.md#local-kontext-editing).

Bundle validation fixes seven component roles and permits local safetensors only.
The receipt includes component asset names and bytes, including tokenizer binary
files, and is checked again after loading. Bulk weights are read once per receipt;
no duplicate read is needed for the retained component fingerprints. The complete
receipt is linear in total asset bytes plus sorting of their names. Rename, drift,
unsupported components, alternate executable/weight formats, nested directories
and linked paths fail closed. The public identity exposes hashes and counts,
not arbitrary local filenames or configuration contents. These receipts identify
local bytes; they do not authenticate pretrained weights or establish ownership.

| Executed check | Result and actual scope |
| --- | --- |
| Archived baseline | Two new functional checks failed against retained PCUC-004 source; original missing-stub/signature rejection is preserved |
| Focused backend suite | 25 passed; local loader, preparation, drift, invalid inputs, CUDA/bfloat16 gates, ordinary/cohort/panel integration |
| Exact geometry | 4,115 aspect cases and all 17 lattice/area cases passed; buckets equal the installed library's table |
| Actual tiny library pipeline | Locally serialized random CLIP/T5/VAE/Flux models load and execute on CPU with test-only placement overrides; same seed gives identical pixels, changed image changes output |
| Real tensor path | 32x48 input produces six target and six image-context tokens, width 64; observed `(1,12,64)` at each of six transformer calls across three two-step runs |
| Final Windows full suite | 1,311 passed, 9 platform skips, 3 dependency warnings; 66-file source identity unchanged throughout |
| External contracts | Seven stages passed; 473 signatures, 56 leaf modules, 66 application files; 13 expected negative consumer diagnostics retained |
| Raw-source audit | 772 errors in 36 files, 59 checked; still FAIL, unchanged diagnostic count and settings, no Kontext diagnostics |
| Fresh distribution | Source/sdist/wheel/isolated installed target match all 66 application files; source and installed operation/packet/review checks passed using synthetic generators and existing Windows dependencies |
| PACER | Structurally valid; all four CSV hashes unchanged; 11 stale requirement evidence records remain visible and coordinated registration is deferred |

The actual library test constructs random models in temporary test storage; there
are no example weights or device overrides in application source. Runtime still
requires native CUDA bfloat16 and a complete local bundle. This host has CPU-only
Torch 2.14.0, Diffusers 0.40.0 and Transformers 5.17.0. The declared Diffusers 0.35
minimum was inspected for the explicit geometry parameters, but only the installed
versions were executed. The `torch_dtype` compatibility argument emits a Diffusers
deprecation warning; the two other warnings concern existing test dependencies.
No dependency, lockfile, typing setting or allowlist changed.

## Retained evidence and reproduction

`source-before.zip` and `source-before.json` preserve the prior 65-file source.
`source-changes.diff` records exactly the four changed/added application files.
The original failures, focused runs, raw diagnostics, reviewed external contracts,
geometry proof, native run command/source hashes, build/install logs and package
checks are retained here. `acceptance.json` binds current source and evidence;
`deferred-inventory.json` and `deferred-operations.json` retain unapplied registration
work. Their FAIL result reflects unreconciled frozen registers, not a passed
governance milestone. `RELEASE-MANIFEST.json` remains a development snapshot.

From the project root, the existing environment can reproduce the principal checks:

```powershell
.venv/Scripts/python.exe evidence/pcuc-kontext/prove.py
.venv/Scripts/python.exe evidence/pcuc-kontext/run_full.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
.venv/Scripts/python.exe evidence/pcuc-kontext/verify.py
```

The full runner needs permission to create operation workspaces outside the
protected application root. The final identity check reads retained evidence;
it does not repeat inference or upgrade that evidence's scope. Regenerating test
records changes their hashes and requires an explicit reviewed checkpoint refresh.
Package reproduction additionally requires an offline build and a no-dependency
isolated target at the paths in `verify_package.py`; `build.txt` and `install.txt`
retain the executed tools' output.

Next qualification action: execute the committed editing/cohort/panel workflow
with an independently selected local pretrained bundle on native CUDA/bfloat16,
record hardware and weight provenance, and recruit separate reviewers before
interpreting task outcomes. Useful editing, protection efficacy, runtime memory
sufficiency, pretrained-family coverage, reviewer reliability, clean installation
and native Linux/macOS remain unqualified. PAC-034 stays shelved; the overall
audit/release milestone remains open.
