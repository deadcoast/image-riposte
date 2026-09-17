# RIPOSTE 0.3 — original experimental publishing engine

The implementation is original RIPOSTE code. It is not a reproduction of a named research paper and inherits none of another method's reported efficacy. `release-v1` creates a single, finite, 8-bit-constrained raster. Every defence branch acts on that same raster. No wrapper policy, watermark, licensing system or audience authentication is embedded.

## One clean publishing raster per requested size

The canonical clean master is composited onto white if necessary and downsampled to the requested maximum edge. It is never enlarged. Two edges that produce the same raster dimensions are deduplicated. **Optimization happens after resizing**, independently for every distinct rendition. Resizing an already protected image is not used as a substitute for optimizing that rendition.

Let x be the RGB publishing baseline, scaled to [0,1]. A per-pixel integer cap b is epsilon everywhere except half epsilon, rounded down, around high-detail edges; smooth near-white pixels optionally receive cap zero. `quality.spatial_budget` uses the channel-mean image and its replicate-padded 3×3 local average. The hard-detail threshold is 0.08; the white rule requires minimum channel >0.97 and local difference <0.005. These fixed rules are operational heuristics, not biological vision or automatic identification of all line art.

```
C(x) = {y : max(0,x-b/255) <= y <= min(1,x+b/255)}
Q(y) = round(255*y)/255
```

Every forward objective receives Q(y); the search uses a straight-through quantization gradient. The bounded pixel projection occurs after each update. PNG serialization does not change the chosen pixels. Numerical quality is recomputed from the committed PNGs before approval, serving and export.

## Image branches and shared optimization

The inherited coupled contexts remain identity/JPEG85/75%-resize × whole/center/left for each encoder, with optional early nine-channel inpainting conditioning contexts. Forward JPEG really passes through Pillow's 4:2:0 encoder/decoder. Its backward pass is an approximate DCT/STE surrogate. Forward resizing is also matched to the actual Pillow transformation with a surrogate backward. This is not an exact derivative of either discrete codec.

For an image-component branch j:

```
d_j(y) = mean((F_j(Q(y)) - F_j(x))²) / max(mean(F_j(x)²), 1e-6)
```

Positive values mean component displacement, not inability to recognize or reuse the illustration. Norms align loss magnitudes heuristically; they do not calibrate real-task effectiveness across components.

A frozen clean reference is held on CPU. Each update scores all contexts without retaining their graphs, computes detached soft-min weights `softmax(-d / max(mean(abs(d)),1e-6))`, and then recomputes each branch's gradient individually. A DCT frequency weighting modifies the combined search direction. It does not impose a strict frequency-support constraint on the final image. The projected sign step is bounded by the shared spatial map.

## Restarts, candidate selection and refusal

Each restart has a deterministic CPU-seeded random initialization inside C(x). The initializer is only a search starting point and cannot become an output. A checked iterate is eligible only if:

- Its actual update had a finite, nonzero gradient in an editable pixel.
- Its minimum context score is positive and improves over that restart's initial minimum score by more than 1e-12.
- The quantized candidate passes all numerical fidelity limits.

Every iteration is checked for eligibility. Across all restarts, the solver maximizes `(minimum context score, mean context score)` lexicographically. `checkpoint_every` controls trace logging only; every newly selected candidate is also recorded, even between checkpoints. Changing trace cadence does not change the search or selected pixels. Two nonimproving iterations halve the step, down to 0.05/255.

Before committing an update, the solver checks its exact quantized pixels against the numerical quality limits. A failing proposal is retried from the same previous iterate with half the step, at most eight reductions and never below 0.05/255. Rejected proposals do not replace the current iterate or trigger model scoring. Cancellation is checked before each reduction. The report records the accepted step size and reduction count; exhausted retries retain the previous iterate without making it eligible. Initial, intermediate or final candidates are not automatically exported merely because a loop finished.

No eligible result means `NO_IMPROVED_FIDELITY_ACCEPTABLE_CANDIDATE`. Missing models, all-zero editable budgets, detached/zero/nonfinite gradients, device mismatch or unsuitable dimensions stop rather than silently adding noise. The optimizer's selected views were used for development and selection; they are **not held-out evaluation**.

Default solver settings: 24 iterations, two restarts, 0.75/255 step, checkpoint every four iterations plus first/last, frequency weight 0.65. These are unqualified starting settings, not recommended anti-AI recipes.

## Spatial and colour quality

`quality.py` independently measures full-image fidelity, every 32×32 tile's RMS (including partial boundary tiles), per-pixel spatial-cap violations, and 95th-percentile CIELAB ΔE76 on sRGB/D65. Defaults block worst-tile RMS above 0.95×epsilon or ΔE76 p95 above 6.0. A cap violation is always blocked. The retained white pixels must remain unchanged.

ΔE76 here is the 1976 Euclidean Lab measure, **not CIEDE2000, a learned perceptual measure, or an imperceptibility proof**. Local RMS reduces the risk of hiding concentrated damage in a global average. Neither substitutes for the artist's visual judgment; approval is separately recorded against the exact output and report bytes.

## Genuine temporal pathway, narrow evidence scope

`LocalTemporalProbe` directly calls fixed SVD components with image gradients enabled. It does not call a no-grad full inference pipeline and pretend its output is differentiable. The fixed local loaders are AutoencoderKLTemporalDecoder, CLIPVisionModelWithProjection, UNetSpatioTemporalConditionModel and EulerDiscreteScheduler. They require the SVD component contract, eight UNet input channels/four output channels, and v-prediction. No custom remote pipeline is imported.

The selected publishing image is differentiably letterboxed to 512×288 by default; CLIP receives a normalized 224/336-sized view. The CLIP resize/normalization path is explicitly a differentiable approximation, not a certified bitwise replica of every Diffusers preprocessing version. Shared-seed image augmentation is followed by deterministic VAE conditioning; the image-conditioning latents are not incorrectly multiplied by the VAE decoding scaling factor. Identical noise, timestep, frame count, guidance and micro-conditioning are used for the clean and candidate cases.

Default context: 14 frames, first step of a 25-step Euler schedule, 7 fps, motion bucket 127, noise augmentation 0.02, per-frame guidance 1→3. The unconditional branch is image-independent and computed without gradient; the conditional branch retains image gradients. With noisy sample z, sigma σ and the classifier-free-guided velocity v:

```
predicted_original = z / (σ² + 1) - v * σ / sqrt(σ² + 1)
E(y) = mean((predicted_original[:,1:] - predicted_original[:,:-1])²)
d_temporal(y) = 1 - E(y) / E(x)
```

Identity and actual JPEG85 supply two temporal contexts. A clean temporal reference with no usable signal is rejected. Both temporal and image scores must pass the shared eligibility condition; an image-only candidate is not silently substituted when the requested video objective fails.

**This optimizes an early predicted-latent temporal statistic.** It does not decode or generate a video, prove reduced useful motion, attack text conditioning, or establish transfer to another family. Suppressing this statistic could fail to affect actual animation or could damage a different property; those are experimental questions, not implied successes. The product records `TEMPORAL_AND_IMAGE_COMPONENT_PROXY` and `UNVERIFIED`.

No memory figure from an inference tutorial is attributed to this gradient-based optimizer. It retains model weights and one branch's graph at a time; CUDA memory/performance were not measured.

## Sources and independent evidence boundaries

Official SVD implementation/API: https://huggingface.co/docs/diffusers/api/pipelines/stable_diffusion/svd . The fixed component layout, conditioning structure and Euler v-prediction relationship inform the adapter; RIPOSTE's temporal objective and production integration are original experiments. Model weights are not redistributed.

DiffusionGuard, revised September 29, 2025: https://arxiv.org/abs/2410.05694 . Its early-step and mask-augmentation work motivates an editing-relevant component branch, not a claim that RIPOSTE reproduces its objective or performance.

IPV-Bench v3, August 19, 2026: https://arxiv.org/abs/2603.26154 . Its tested cross-generator, matched-noise and preprocessing failures motivate strict separation of pixel fidelity, component displacement and actual misuse-task outcomes. It does not establish that every future defense will fail.

## Executed vs pending

Real CPU autograd, actual codecs, seed isolation, best-feasible selection, shared spatial limits, temporal-axis gradients, CFG wiring, component allowlists, interruption/resume, output binding and publication UI/API are tested. Synthetic oracles and loader substitutes are explicitly identified; no substituted encoder is shipped as a production fallback.

Real pretrained loading, CUDA execution, useful-motion suppression, editing-task failure, modern text-guided video defense, published-platform derivatives and independent model-family transfer remain unqualified. See the executable tests and the current release validation, not screenshots or another paper's efficacy numbers.
