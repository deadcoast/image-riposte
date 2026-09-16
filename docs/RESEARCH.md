# Image-integrated protection: research and implementation decisions

**Reviewed 14 September 2026.** Primary publications and official project documentation only. A method being listed here does not mean its code is installed, its license permits redistribution, or its claims have been reproduced in RIPOSTE.

## 1. The threat is not one thing

A model can describe an image, use its composition as a reference, edit its pixels, learn a style from a collection, or animate a single frame. A defense optimized for one pathway need not disrupt the others. RIPOSTE therefore treats recognition, reference-driven generation, editing, style learning, and video conditioning as separate evaluation targets.

The artist's constraint is also explicit: the published raster must remain an acceptable illustration. There is no watermark payload, hidden authorship code, viewer-side account, or expectation that an external model obey a “do not train” instruction. The mechanism under investigation is a **calculated change to the pixels consumed by the model**.

The system must not rename generic noise “protection.” It must also not interpret a parser failure, unreadable image, extreme distortion, or merely different generated output as successful protection. Those outcomes can fail the artist's requirement even when a numerical attack metric improves.

## 2. Methods worth distinguishing

| Method | Mechanism and relevant target | RIPOSTE decision |
|---|---|---|
| **Glaze** | Image-specific feature displacement aimed at learning an artist's style. The official FAQ expressly distinguishes this from unreliable img2img protection. | An external-candidate path for style experiments; not the default editing/video engine. [Official FAQ](https://glaze.cs.uchicago.edu/faq.html) |
| **Nightshade** | Prompt-specific poisoning intended to influence later model training on the processed examples. | A separate training-data research track; not immediate protection against an already-trained image editor. [Paper](https://arxiv.org/abs/2310.13828) |
| **PhotoGuard** | Encoder-directed and end-to-end diffusion perturbations for editing resistance. | A useful editing baseline and reason to test the full generator rather than stop at encoder features. RIPOSTE's baseline is not a reproduction. [Paper](https://arxiv.org/abs/2302.06588) · [Official code](https://github.com/MadryLab/photoguard) |
| **Mist / Mist v2** | Adversarial preprocessing targeting mimicry and editing. Its own documentation uses watermark terminology. | No bundled default under the no-watermark constraint. Review the mechanism and distribution terms before adapting it; the repository's licensing language is ambiguous. [Official repository](https://github.com/psyker-team/mist-v2) |
| **DiffusionGuard** | Early-diffusion attack objective and mask augmentation, aimed at mask-guided editing. | Mechanism reference for the new optional masked early-conditioning probe. RIPOSTE's proxy is not a reproduction or a verified use of the paper's defense. [Paper](https://arxiv.org/abs/2410.05694) · [Official code](https://github.com/choi403/DiffusionGuard) |
| **DCT-Shield** | Adversarial optimization in discrete-cosine-transform coefficients, with compression robustness as a central concern. | Compression/frequency reference. RIPOSTE now has real JPEG-forward views and frequency-weighted search; it does not implement this paper's DCT-coefficient method. [Paper](https://arxiv.org/abs/2504.17894) |
| **I2VGuard** | Spatial, temporal, and diffusion attack components for misuse of a still image by image-to-video systems; CVPR 2025. | A substantive video-defense implementation target, requiring generated-video evaluation rather than single-frame inspection. [CVPR paper](https://openaccess.thecvf.com/content/CVPR2025/html/Gui_I2VGuard_Safeguarding_Images_against_Misuse_in_Diffusion-based_Image-to-Video_Models_CVPR_2025_paper.html) |
| **Vid-Freeze** | Suppresses video motion through an attention-oriented objective. | A distinct outcome: preventing useful animation is not the same as preventing recognition of the illustration. Keep both measurements. [Paper](https://arxiv.org/abs/2509.23279) |
| **Anti-Prompt** | July 2026 paper examining text conditioning and attacking text-related interactions during video denoising; its arXiv record reports ECCV 2026 acceptance. | A current text-guided-video research candidate, not an established production winner. [Paper](https://arxiv.org/abs/2607.01499) |
| **I2VShield** | July 2026 preprint proposing a text-adaptive perturbation generator and multimodal-attention disruption for diffusion-transformer video models. | Investigate scalable per-image rendering after independent reproduction. Code readiness and deployment performance are not established by this release. [Paper](https://arxiv.org/abs/2607.25522) |

### Conflicting evidence must remain visible

The Glaze project claims transfer and resistance to common preprocessing. An independent style-mimicry evaluation reports that the protections it tested could be weakened by adaptive approaches including image upscaling. These are not grounds to assert that every later implementation is broken—or that every current cloak is reliable. They require version-specific, adversarial evaluation. [Glaze FAQ](https://glaze.cs.uchicago.edu/faq.html) · [Hönig et al.](https://arxiv.org/abs/2406.12027)

The **August 19, 2026 revision of IPV-Bench** compares five defenses across four video models and reports weak transfer, frequent failure to outperform noise, and preprocessing failures in effective cases. Its older title was IP-Bench; the current revision must not be described using the older version's model/method counts. This is a benchmark result for the tested methods, not a proof that further development cannot improve defenses. [IPV-Bench, current v3](https://arxiv.org/abs/2603.26154)

## 3. What this research changes in the product

**No single “protection strength” percentage.** One candidate can be visually acceptable, alter an encoder strongly, survive compression, and still produce an excellent copied animation. Those observations belong in separate fields.

**Do not stack filters blindly.** Successive optimizations can spend the same visual budget, destroy an earlier perturbation, or target incompatible pathways. A stronger design optimizes a shared final raster against multiple objectives, then evaluates the combined result. The relative weights must be justified by held-out performance, not by the number of techniques named in the interface.

**Optimize the actual publication representation.** Flattening transparency, resizing, quantization, compression, and platform conversion are part of the path to the attacker. Protection calculated for a 4000-pixel master is not automatically evidence about its 1080-pixel social derivative. The current lab standardizes the public raster before optimization and tests it after real codec operations.

**Keep meaningful negative controls.** Compare the clean image, a matched random-noise control, a visually comparable non-adversarial alteration, and the calculated candidate. A perturbation should outperform a quality-matched control on the actual misuse task. Merely changing a generator's random trajectory is not enough.

**Separate optimization and evaluation.** Never optimize against all images, prompts, masks, seeds and models and call that a transfer test. Reserve held-out illustration styles and at least one architecture outside the optimizer. Record unsuccessful cases with the same visibility as successes.

These are RIPOSTE design decisions informed by the distinctions and evaluations above, not claims of a newly proven defense.

## 4. Built now: coupled optimization and controlled evidence

The original EOT-VAE baseline remains available. RIPOSTE's new `coupled-v1` jointly evaluates one quantized, spatially bounded raster across real-codec views and multiple masked encoder contexts, with an optional nine-channel early-inpainting probe. A sequential two-pass gradient reduces retained branch graphs; a frequency-weighted direction changes the search, not the fundamental pixel-domain constraint. Real JPEG4:2:0 is used on the forward path; a DCT4:4:4 approximation supplies gradients. This is an original experiment, not a faithful named-paper reproduction.

The fixed encoder loader follows the official [AutoencoderKL](https://huggingface.co/docs/diffusers/api/models/autoencoderkl) and [AutoencoderTiny](https://huggingface.co/docs/diffusers/api/models/autoencoder_tiny) interfaces. Tiny is a distilled encoder proxy, not independent proof about full diffusion systems. The probe follows the fixed [Stable Diffusion inpainting](https://huggingface.co/docs/diffusers/api/pipelines/stable_diffusion/inpaint) component pathway.

Controlled encoder qualification uses three feasible sign-scrambled controls preserving exact absolute channel changes. It evaluates 24 contexts per encoder, distinguishes known from unknown optimization protocols, and does not confuse different weight hashes with unseen architectures. This is stronger experimental bookkeeping, not a claim that the candidate protects an image.

The full generation review now contains five arms and fixed local [SD img2img](https://huggingface.co/docs/diffusers/api/pipelines/stable_diffusion/img2img), [SD inpainting](https://huggingface.co/docs/diffusers/api/pipelines/stable_diffusion/inpaint) and [SVD](https://huggingface.co/docs/diffusers/api/pipelines/stable_diffusion/svd) reference adapters. These baseline families do not establish coverage of current proprietary models. SVD is not text-guided. Generated outputs, masks, seeds, pre/post-transform fidelity, pipeline filter flags and explicit unscored status stay separate.

No pretrained model ran in this delivery environment: package/model access failed and available PyTorch was CPU-only. Numerical tests exercise actual autograd/codec/control code with synthetic oracles; generation adapters are tested with explicit doubles. Neither inherits the cited papers' efficacy claims. [Engine contract](ENGINE-v02.md) and [validation](VALIDATION.md) define the exact implementation and execution limits.

## 5. The next experiment should answer a concrete question

> On acceptable-quality illustrations after the actual publishing transform, does the candidate reduce a specified misuse task's success more than a matched perturbation control—and does that result transfer beyond the optimizer's model?

A proposed evaluation set should include line art on white, flat/cel shading, textured illustration, subtle gradients, fine hatching, and small-format samples. Each image needs an artist-acceptable visual budget rather than an assumed universal imperceptibility threshold.

For editing, vary masks, preservation instructions and editing strength. Review whether recognizable source composition and characteristic details survive the intended edit. For reference generation, test whether distinctive design elements survive re-prompting. For video, review source fidelity, meaningful motion, instruction following, temporal consistency and useful output quality separately. A frozen frame is a motion-specific result, not evidence that the model cannot perceive the image.

Apply the transformations an attacker could plausibly use: actual published/downloaded file pairs, screenshots at different scales, crop/resampling, JPEG/WebP transcoding, denoising and upscaling. The current release implements smaller generic transport and qualification suites; it does not claim that suite fully reproduces platform processing or adaptive removal.

Model versions, safe model identifiers/fingerprints, code version, seeds, prompts, masks, transform parameters, quality reviews and clean-output hashes are necessary before a reproducible protection claim. No source-image metadata or raw image-path history is needed to record those experiments.

## 6. Next integration order and source review

First qualify the actual pretrained local encoder, optional inpainting probe and five-arm generation pathways. Compare the legacy and coupled engines under the same visual budget and after measured social derivatives. The experimental coupled code already exists; running it on real models and judging misuse outcomes is the next missing evidence, not a reason to claim it has already succeeded.

Next implement a genuine temporal/text-conditioning or attention-based video objective and evaluate against held-out architectures. Keep the common raster budget and existing control protocol. Only after results justify it should fast perturbation generators, broad batch rendering and platform-specific profiles become defaults.

Source records were reviewed September 14, 2026. DiffusionGuard's canonical record is v2 (September 29, 2025); DCT-Shield is v2 (July 31, 2025). IPV-Bench's canonical current record is v3 (August 19, 2026); its v2 full HTML was also consulted for protocol details, not mislabeled as latest. Anti-Prompt and I2VShield are research candidates; upstream model compatibility, reproducibility and licensing must be qualified before integration. Official library API pages are living documentation and are not substitutes for a frozen tested dependency environment.

Audience friction and watermarks remain excluded. Do not add a defense name to the UI as an installed engine unless its actual code, conditions and evidence exist in the release.
