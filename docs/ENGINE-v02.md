# RIPOSTE 0.2 — implemented engine and qualification contract

## 1. Scope

`coupled-v1` is original experimental RIPOSTE code. Its implemented output is a constrained raster whose changes are optimized through selected local model components. Its score is a **proxy**. It does not establish failed recognition, failed copying, failed style learning, failed editing or failed video generation.

The source separates `models.py` (fixed local adapters), `views.py` (codecs, masks, budgets and controls), `coupled.py` (optimization), `qualification.py` (controlled encoder comparison) and `generation.py` (five-arm output review). `lab.py`, `server.py` and `cli.py` connect those functions to existing cleaned assets. No replacement directory scheme is introduced.

## 2. One raster and one visual budget

Let `x` be the 8-bit public RGB image scaled to [0,1]. It has already been flattened on white and resized down to the selected publishing edge. Let `b(x)` be the integer spatial channel budget in normalized units. Smooth near-white areas can have zero budget and high-contrast edges receive a reduced budget. The implementation projects every update onto:

```
C = { y : max(0, x-b) <= y <= min(1, x+b) }
Q(y) = round(255*y)/255
```

The optimizer evaluates `Q(y)`, not only fractional changes. Because `x` and the budget boundaries are on the 8-bit lattice, final rounding remains admissible; final integer channel differences are independently checked. The configured maximum is 1–16 levels; default four. A completely zero editable budget stops with `NO_EDITABLE_PIXEL_BUDGET`.

This is not an imperceptibility guarantee. Fine line work, flat areas, gradients and textured art may need different artist-approved limits. No aesthetic-quality claim follows from PSNR alone.

## 3. Coupled contexts

Every encoder gets nine branches: identity/JPEG85/75%-resize × whole/center/left mask families. A keep-mask leaves selected source pixels visible and fills the removed region with normalized gray for the encoder proxy. Seeds make the geometry reproducible.

An optional `LocalInpaintProbe` adds four branches: identity/JPEG85 × two masked early-step conditions. The probe uses a fixed nine-channel Stable Diffusion inpainting UNet, its VAE, tokenizer and text encoder. It concatenates shared seed noise, edit mask and masked-image latents. Two shipped non-personal prompt keys and early fractions 0.90/0.98 vary conditioning. This is an early-conditioning displacement experiment, not a complete denoising loss or a reproduction of DiffusionGuard.

For branch `j`, with clean reference feature `z_j`:

```
d_j(y) = mean((F_j(Q(y)) - z_j)^2) / max(mean(z_j^2), 1e-6)
tau = stop_gradient(max(mean_j(d_j), 1e-6))
L(y) = -tau * log(mean_j(exp(-d_j(y)/tau)))
```

Ascent emphasizes the contexts with weaker measured displacement. The gradient uses `softmax(-d/tau)` as detached weights. The normalized losses are a heuristic scale alignment, not an empirical guarantee that different components contribute equal real-task protection.

### Sequential two-pass implementation

Pass one computes the context scores without retaining their graphs. Pass two recomputes one branch at a time and adds its weighted gradient. Clean feature references reside on CPU. The result avoids retaining all branch graphs at publishing resolution, at the cost of additional forwards and transfers. This is an implementation property; no GPU speed or memory benchmark is claimed. There is no branch minibatching, tiled large-image engine or arbitrary model offloading in this release.

## 4. Real forward transformations, approximate gradients

The forward JPEG branch actually encodes and decodes Pillow JPEG with 4:2:0 subsampling. A differentiable 4:4:4 DCT/straight-through approximation supplies the backward direction. Forward resize likewise uses actual image resampling with a differentiable surrogate backward. This BPDA-style construction optimizes through an approximate gradient: it is **not** a derivative of JPEG bytes and can mislead the search.

A block-DCT frequency weighting damps high-frequency components of the search gradient before its sign update. The candidate itself remains pixel-projected. This is **not** a strict frequency-domain feasible set, a proof of compression robustness, or DCT-Shield's algorithm. UI labels and research records maintain this distinction.

Detached/nonfinite gradients, missing models, incompatible devices, invalid dimensions or zero useful gradients fail with code-only errors. There is no noise-only fallback. Progress callbacks allow cancellation between branches and before final commit; an individual model forward is not preempted.

## 5. Local models and runtime preflight

The fixed encoder adapters support `AutoencoderKL` and `AutoencoderTiny`. KL uses latent means; Tiny uses its deterministic latent output. Inputs are padded to the class's spatial factor, not silently distorted to a square. Model weights receive an aggregate fingerprint. No source-image hash or local model pathname enters reports.

`inspect_vae` reads bounded configuration and checks safetensors presence. Its status is `FILES_PRESENT_NOT_EXECUTED`; it is not a successful load certificate. Actual execution still can fail for dependency incompatibility, model shape, memory or device reasons. Model config and runtime trust remain separate from image-container cleaning. No remote models or custom pipeline code are fetched.

## 6. Controlled encoder qualification

Create three controls with seeds 101, 211 and 307 by randomizing the sign of each observed clean-to-candidate channel delta. Keep its exact absolute magnitude. If a chosen sign would leave [0,255], use the feasible sign instead. Thus `|control-x| = |candidate-x|` for every channel before transport. Peak change and RMS match exactly; boundary pixels can be forced to use the same direction. These controls are not iid Gaussian and need not be perceptually equivalent to the candidate.

Eight real views are evaluated: identity, JPEG85, 75%-resize, JPEG70, JPEG60, 50%-resize/JPEG80, offset crop, and mild blur. Each is paired with whole/right/bottom keep-mask contexts: **24 cells per encoder**. The same transformation, mask and seed apply to clean, candidate and all controls.

Each cell records the candidate's normalized feature displacement, all three controls, strongest control, signed margin, and ratio when its denominator is nonzero. An above-control count is descriptive. It is not a p-value, confidence interval, protection percentage or defense certificate.

Scope is explicit:

- Known optimization view families can be separated from held-out transform families. A new JPEG quality is a held-out transform **parameter setting**, not a wholly unseen transform category.
- External candidates and the legacy baseline can lack a recorded optimization protocol. They must display `OPTIMIZATION_PROTOCOL_UNKNOWN`, not silently inherit RIPOSTE's defaults.
- Identical weight fingerprints mean the same weights. Different weights do not establish a different architecture or independently held-out training data. Unknown identities remain unknown.
- Whole is the unmasked context, not a held-out mask.

Qualification cannot establish full-edit outcomes because no editing generator is scored here. Even a pretrained encoder advantage would remain `CONTROLLED_ENCODER_PROXY` and `UNVERIFIED`.

## 7. Five-arm generation review

The new `challenge` command and generation UI run a selected fixed local baseline with five inputs: clean, candidate and three magnitude-matched controls. Every arm uses the same generation seed for a group. Default two seeds × two publication views × five arms = 20 calls. Control equality is before publication transforms; prepared-input fidelity records its changes after codecs/resizing.

Supported reference adapters:

| Task | Fixed adapter | Input preparation | Important limit |
|---|---|---|---|
| edit | SD img2img | Maximum edge 768, sides snapped to multiples of eight | Fixed background-edit prompt and strength; not modern-family coverage |
| inpaint | Nine-channel SD inpainting | Same preparation plus reproducible right-region mask | Source-preserving mask task; not every mask or prompt |
| video | Stable Video Diffusion | White-padded 1024×576, 14 frames | Image-conditioned, not text-guided |

All use local safetensors, allowlisted components and CUDA float16. Runtime GPU support and full pretrained operation are unqualified here. Same seeds do not eliminate nondeterminism from CUDA kernels or make output divergence synonymous with successful defense.

Reports store safe model-component hashes, protocol/version, predefined conditioning, seeds, view names, clean-output/frame hashes, comparisons, task and explicit evidence scope. Source paths and image metadata dumps are never needed. Model weight fingerprints do not fingerprint every possible library/kernel/configuration effect; environment and full model configuration qualification remain required before reproducible efficacy claims.

Review frames are fresh date-only PNGs. Every served frame must match a committed report's allowlisted relative name, date and hash. An interrupted/failed generation never publishes a final report; caught failure removes its partial run. A power loss can leave clean orphan images, not contaminated backups. The UI does not treat those as a committed review.

When a pipeline returns content-filter flags, they are recorded separately. A flagged/filtered result is not evidence of adversarial disruption. Output RMSE, adjacent-frame RMSE and five-arm differences are descriptive. Human review must judge the intended edit or animation, preservation of source features, useful motion, instruction following and quality. Review judgments are not yet a persisted annotation workflow.

## 8. What has actually been executed

Real PyTorch autograd, integer projection, codecs, control construction, branch aggregation, state binding and API/UI flows were executed on synthetic fixtures. Fixed model adapters were exercised using explicit stubs. No pretrained encoder, UNet or video pipeline ran; no real-model efficacy number is supplied. See the release validation records rather than the synthetic demonstration's proxy values.

## 9. Next substantive experiment

Freeze a local model configuration and dependencies on a real CUDA installation. Run the existing and coupled engines on representative artist-approved illustrations at several admissible budgets. Qualify different encoder weights, then review all five arms through actual editing/inpainting and video baseline runs. Include published/downloaded derivatives and an adaptive removal arm. Record failures and visual costs equally with successes.

Only then promote an empirically useful recipe to a default. The next algorithmic addition should be a genuine temporal/text-conditioning objective with independently evaluated video models, not a cosmetic filter or another unmeasured proxy relabeled as protection.
