# RIPOSTE v0.2.0 — executed validation and evidence limits

**Validation date:** September 14, 2026. This record concerns the actual delivered-source continuation, not a hypothetical implementation. The original SHROUD archive was extracted and tested before edits. No user artwork was processed.

## Executed checks

| Check | Actual result | Evidence |
|---|---:|---|
| Original SHROUD 0.1.0 source baseline | 194 passed | `evidence/baseline-tests.txt` |
| Identity-renamed baseline before feature changes | 194 passed | `evidence/rename-tests.txt` |
| RIPOSTE 0.2.0 source suite | 332 passed | `evidence/source-tests.txt` |
| Separately installed wheel suite | 332 passed | `evidence/installed-wheel-tests.txt` |
| Inherited test files | 8 files, all identical after identity/version substitutions | `evidence/release-qualification.json` |
| New test cases | 138 | Current total less inherited total |
| Source / wheel / installed package payload | 22 files byte-identical, including 18 Python modules | `evidence/release-qualification.json` |
| Chromium interface/interaction checks | 30 passed | `evidence/browser-qa.json` |
| Actual Uvicorn loopback HTTP checks | 16 passed | `evidence/http-qa.json` |
| JavaScript parse and shell syntax | Passed `node --check` and `bash -n` | Release qualification command record |

The final ZIP is extracted and tested after packaging. Its exact hash, manifest verification, extracted-source test result and package equality are recorded in the adjacent **`RIPOSTE_v0.2.0_release_report.json`** supplied with the release. The manifest intentionally excludes its own bytes; the external report hashes the final ZIP without a self-reference cycle.

## Source provenance

The baseline archive SHA-256 and normalized per-file change map are included. Eight inherited test files comprise seven test modules and their fixture module; they are preserved under the required application/package/version changes, not claimed to be byte-identical to the old SHROUD names. The current 22-file package has seven identity-only files, ten modified files and five new files relative to that normalized baseline. There are 18 Python package modules.

The installed-wheel test used a separate target directory and a different working directory, with an explicit import-path check. It did **not** use the source package. Existing host dependencies were shared; this is not a freshly resolved clean operating-system environment or an independently solved dependency matrix.

## Environment actually available

Python 3.13 on Linux; exact versions are captured in `evidence/release-qualification.json`. PyTorch was `2.10.0+cpu`. No CUDA or MPS device was available. Diffusers, Transformers and Accelerate were absent. Optional package/model access attempts failed because the runtime could not resolve the required package/download hosts. The delivered package does not include pretrained weights or a claim that missing dependencies were installed successfully.

`evidence/runtime.json` is the real read-only `riposte doctor` output, not a synthetic GPU-capability fixture.

## What the numerical/model tests establish

Actual PyTorch tensors, gradients, quantization, integer pixel limits, deterministic contexts, matched controls, actual Pillow codec operations, report commits and cancellation boundaries were exercised. Tests include failures for missing/constant/detached/nonfinite model gradients, unsupported model layouts, wrong scopes, altered artifacts, report-write rollback and interrupted state upgrade.

Pretrained VAE/UNet/pipeline objects were replaced by explicitly labeled test doubles where necessary. This exercises actual adapter arguments, nine-channel-mask code, seed matching, five-arm serialization, frame hygiene and API behavior. It does **not** establish that any supported pretrained model successfully loaded, that its gradients give useful protection, or that editing/video reuse became harder.

The synthetic demonstration additionally runs real coupled optimization through a small differentiable averaging oracle. Its scoped evaluation and generation-review frames are test data. Their numerical values are not pretrained-model results, dataset statistics or an efficacy claim.

## Browser boundary

Chromium rendered and executed the actual application HTML/CSS/JavaScript. The browser harness used an `about:blank` document with fetch dispatched to the actual FastAPI TestClient. It verified the live catalog, real double-click selection, zoom/pan, native fit, keyboard divider, codec previews, qualification/report scope, five-arm synchronized frame controls, runtime preflight, export/source-removal gates, research register and no JavaScript errors. Responsive checks include 1512, 1024 and 390 pixel widths; no page-level horizontal overflow was found at the tested states.

A separate script launched a real Uvicorn listener and sent real loopback HTTP requests using httpx. It verified token/host/origin/fetch checks, no-store/CSP, audited thumbnails/transformed views, checkpoint behavior, gated writes, scoped evaluation and hash-bound generated frames.

**Direct Chromium navigation to localhost was blocked by the runtime's administrator URL policy.** No policy bypass was used. Therefore these are separate browser-interaction and live-HTTP qualifications, not a successful native browser-to-live-server end-to-end run. Native Windows/macOS launch and browser behavior still need qualification on the user's machine.

## Reproduction

Run the numerical suite from the extracted source with its optional test dependencies and PyTorch installed:

```bash
PYTHONPATH=src python -m pytest -q
```

With an installed package, `python -m pytest -q` uses that package. Model tests explicitly skip when PyTorch is absent; do not report the full count as exercised in that case.

Synthetic browser/HTTP evidence is generated only in a separate, disposable fixture workspace:

```bash
PYTHONPATH=src python scripts/make_demo.py /path/to/new-demo
PYTHONPATH=src python scripts/make_test_evidence.py /path/to/new-demo
PYTHONPATH=src python scripts/browser_qa.py --in-process-root /path/to/new-demo
PYTHONPATH=src python scripts/http_qa.py /path/to/new-demo
```

`make_test_evidence.py` requires the synthetic workspace marker. Do not run these scripts on real artwork. Browser checks require Playwright and the configured Chromium executable; the delivered QA environment used `/usr/bin/chromium`. The HTTP script creates and terminates its own test server. It may need an unused port 8765.

## Not established

No pretrained protection efficacy, current proprietary-model coverage, actual text-guided-video defense, GPU throughput/memory benchmark, native Windows/macOS execution, complete cross-platform dependency lock, external penetration test, full WCAG audit, forensic erasure, or automatic protection-certification result is supplied. No live social-platform processing profile was measured. Unit tests, code review and output hashes cannot substitute for those claims.

The release can support a real-model experiment; it cannot turn an unexecuted experiment into evidence. `UNVERIFIED` remains the correct AI-protection status.
