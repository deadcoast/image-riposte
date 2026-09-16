# RIPOSTE 0.3.0 — release validation

## Executed software checks

| Check | Result |
|---|---:|
| Actual 0.2 archive baseline | 332 passed |
| Final 0.3 source unit/integration suite | 449 passed |
| Independently installed 0.3 wheel | 449 passed |
| Fresh final delivered ZIP extraction | 449 passed — external final release report records the actual run |
| Inherited test files | All 15 byte-identical; 332 inherited cases retained |
| New test cases | 117 across four new files |
| Existing library/workshop browser scenarios | 30 passed |
| Main publishing browser scenarios | 23 passed; repeated using installed-wheel runtime/assets |
| Existing live HTTP scenarios | 16 passed |
| Main publishing live HTTP scenarios | 16 passed |
| Package files across source/wheel/installed/extracted | 29 byte-identical; see external release report |

The final-extraction assertion is backed by the external release report produced after ZIP creation and extraction. The manifest inside the release is checked against the actual files. A failed final check must prevent delivery; it must not be relabeled as a planned check.

## What the tests actually exercised

Real CPU PyTorch autograd, quantized spatial projection, actual JPEG/resize processing, local-tile and colour quality measures, useful-gradient refusal, best-checkpoint selection across restarts, deterministic per-item seeds without global RNG mutation, and coupled temporal/image objectives were executed. The temporal adapter graph is tested with explicit synthetic components for frame-axis correctness, CFG separation, image-conditioning gradients, augmentation seeds, local component allowlists and safe loader options. None of those substitutes is a production fallback.

Publishing tests cover read-only/no-model planning, independently optimized distinct resolutions, no-upscale deduplication, model reuse, per-item failure, cancellation/resume, uncommitted orphan recovery, committed-file preservation, model mismatch, source/baseline integrity, quality refusal, exact-file approval, revocation, date-only pack membership, code-only errors, actual API/CLI orchestration and the optional exact-output workshop bridge. Automation scripts refuse a workspace without its explicit synthetic-demo marker.

Browser QA uses Chromium and the actual HTML/CSS/JavaScript against the real FastAPI backend through a TestClient fetch bridge. Primary QA executes the real optimizer on synthetic illustrations through a labeled synthetic encoder, including actual browser PNG-pack downloads. This was repeated with `riposte` loaded from the independently installed wheel. It is not a mocked interface or a screenshot of a nonfunctional design. Source-library/workshop tests also use explicitly labeled synthetic oracles and generator substitutes.

Separate Uvicorn subprocesses exercise actual loopback TCP HTTP, authentication/origin/host handling, exact candidate bytes, codec previews, approval/revocation, download membership and metadata audits. Direct Chromium navigation to localhost is blocked by this runtime's administrator policy. The browser-bridge checks and live HTTP checks are reported separately rather than claimed as a native end-to-end browser listener test.

Desktop and 1024/390-pixel publishing and review layouts were exercised and screenshots inspected. Final screenshots show synthetic art, not the user's illustrations.

## Runtime and unavailable qualification

Python 3.13, PyTorch 2.10.0+cpu and safetensors 0.7.0 were available. Diffusers, Transformers and Accelerate were absent. An explicit optional-dependency installation attempt failed; its output is included without inventing a successful model setup. CUDA and MPS were unavailable. The core installed-wheel tests reuse the host's third-party dependencies; they are not a new operating-system/dependency-isolated installation.

**Not executed:** real pretrained encoder/inpainting/SVD loading or protection outcomes, native Windows/macOS launchers, CUDA gradients/memory/timing, real artist-approved artwork evaluation, actual social-platform uploads/downloads, modern text-guided video objectives or independent-family transfer. No real image-to-video generation was performed by the new temporal objective. No efficacy percentage, imperceptibility guarantee, general-recognition block or recommended protection recipe is inferred.

The prior 0.2 archive remains the comparison baseline. No user artwork or raw personal image metadata was used in these runs. All publishing and test-copy artifacts are already reconstructed, date-only synthetic images.

## Evidence files

`evidence/source-tests.txt`, `installed-wheel-tests.txt`, `baseline-tests.txt`, `inheritance.json`, `runtime.json`, `optional-dependencies-attempt.txt`, `package-equivalence.json`, `publication-browser-qa.json`, `library-workshop-browser-qa.json`, `publication-http-qa.json`, and `library-workshop-http-qa.json` record the executed checks. `RELEASE-MANIFEST.json` describes the exact delivered file bytes. The external `RIPOSTE_v0.3.0_release_report.json` records final ZIP hash, final-extraction test output, manifest verification, and source/wheel/installed/extracted equivalence.
