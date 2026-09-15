## RIPOSTE — first executable release

I built **RIPOSTE v0.1.0**: a local application with an artwork browser, metadata cleansing and organization, a before/after protection lab, transport testing, and an experimental model-driven image optimizer.

**[Download RIPOSTE v0.1.0 — application, source, tests, and documentation](sandbox:/mnt/data/RIPOSTE_v0.1.0.zip)**

The important distinction: **the cleansing and organizer are implemented and tested; the anti-AI engine is implemented experimentally, but its effectiveness against pretrained models has not been demonstrated.** This environment could not install the optional model stack and has no CUDA device. I have not relabeled a noise filter—or passing software tests—as effective protection.

The interface shown above is the running application, using clearly identified synthetic artwork. No images were supplied from your collection, so your actual files have not been touched.

---

## 1. The organization checkpoint is implemented

RIPOSTE recursively processes the selected artwork folder, including existing nonconforming subfolders. It rebuilds supported images, assigns their date and resolution category, renames them, and places them into your structure:

```text
Artwork/
├── 2026/
│   └── September/
│       ├── SML/
│       │   ├── SML01.png
│       │   └── SML02.png
│       └── LRG/
│           └── LRG01.png
├── 2025/
│   └── January/
│       └── MED/
│           └── MED01.png
└── EVERYTHING_ELSE/
    └── December/
        └── XTL/
            └── XTL01.png
```

**No empty calendar scaffold is created.** Months and size folders appear only when required. Empty former directories are removed. Numbering avoids collisions and continues beyond 99. Repeating the operation does not continually rename unchanged, already-clean files.

### Size classifications

The same thresholds apply to every month:

| Folder  |  Total pixels: width × height |
| ------- | ----------------------------: |
| **SML** |               Below 1 million |
| **MED** |  1 million to below 4 million |
| **LRG** | 4 million to below 16 million |
| **XTL** |            16 million or more |

These are **resolution categories**, not unsupported judgments about artistic quality. Compressed file size is displayed separately.

The default date basis is filesystem creation/birth time where available. Otherwise, modified time is used and explicitly labeled as a fallback—not presented as a known download date. Embedded-date and modified-date modes are also available.

### Source replacement is explicit

**Applying the migration removes each successfully processed original after its sanitized replacement has been written and verified.** No metadata-bearing backup, quarantine copy, or Trash copy is created.

A read-only scan comes first. The interface requires explicit source-removal confirmation before applying changes.

Unreadable images, unsupported formats, changing files, and unresolved non-image files remain untouched and keep the checkpoint **INCOMPLETE**. The application will not call a folder clean while silently leaving unprocessed material behind.

---

## 2. Metadata cleansing reconstructs the image

RIPOSTE does not merely delete a few EXIF tags. Its implemented sequence is:

**Decode → apply orientation → convert usable color profile to sRGB → reconstruct fresh pixels → encode fresh PNG → independently audit.**

The output retains **one date field: `YYYY-MM-DD`**. Source EXIF, GPS, XMP, comments, thumbnails, software information, embedded profiles, and unknown ancillary chunks are not copied. RGB values concealed behind fully transparent pixels are zeroed.

The application also avoids persisting raw source metadata, source filenames, original paths, or raw-source hashes in its catalog. Hashes are calculated from the **cleaned output**.

Known metadata sidecars can be explicitly discarded. Layered project formats, animations, unsupported bit depths, and other inputs that cannot satisfy the current reconstruction contract are blocked rather than silently damaged.

**One deliberate format choice:** cleaned masters are uniform, lossless PNGs. That does not change your classification scheme into extension-based sorting.

This removes the supported containers’ metadata—not information drawn into the visible picture, arbitrary pixel steganography, other copies elsewhere, or operating-system recovery traces. Those boundaries are documented rather than hidden behind “complete security.”

---

## 3. Research: the relevant methods are not interchangeable

The research dossier separates training interference, editing disruption, and video disruption. That distinction matters to your specific case.

| Method             | Actual target and relevance                                                                                                                                                                                                                                    |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Glaze**          | Artist-style mimicry. Its own current FAQ explicitly says it does **not** provide consistent protection against image-to-image editing, style transfer, or inpainting. It is not a complete answer to someone directly reusing your illustration. ([Glaze][1]) |
| **Nightshade**     | Training-data poisoning. It acts through subsequent model training; it is not an immediate shield against an already-trained generator processing your uploaded image. ([arXiv][2])                                                                            |
| **DiffusionGuard** | Unauthorized diffusion editing. Its early-stage diffusion objective and mask augmentation are relevant to edits that target only part of an illustration. ([arXiv][3])                                                                                         |
| **DCT-Shield**     | Frequency-domain protection against editing, with JPEG robustness directly relevant to public image distribution. This is a more pertinent research direction than adding arbitrary grain. ([arXiv][4])                                                        |
| **I2VShield**      | A July 2026 approach targeting transformer-based image-to-video systems through text-adaptive perturbations and multimodal-attention disruption. It is a video-specific research candidate, not an installed RIPOSTE engine. ([arXiv][5])                       |
| **Anti-Prompt**    | Text-guided image-to-video protection, targeting the model’s text-conditioned interactions. This addresses a different mechanism from a still-image encoder defense. ([arXiv][6])                                                                              |

The dossier additionally covers **PhotoGuard, Mist v2, I2VGuard, Vid-Freeze**, and evaluation literature. The application includes a **12-record research register**, not a misleading claim that twelve protection engines are installed.

### The difficult evidence is included

Glaze’s authors describe robust protection for their intended style-mimicry threat. Independent researchers, however, report successful removal or bypass attacks against the artist-protection methods they evaluated. Those findings concern the tested methods and versions—not proof that every future approach must fail. ([Glaze][1])

For video, the August 2026 revision of **IPV-Bench** evaluated five methods across four generators. It reports poor transfer, frequent failure to outperform noise, and preprocessing failures in the effective cases. That makes matched noise controls, held-out models, and post-processing tests essential—not optional polish. ([arXiv][7])

**My development decision is therefore to optimize and measure specific defenses, rather than stack named filters and assume their protection adds together.**

---

## 4. The protection lab contains working implementation

### Model-driven candidate generation

The built-in experimental engine, **EOT-VAE**, optimizes pixel changes through one or more local variational autoencoders.

Its implementation includes bounded per-channel changes, gradients through multiple transformed views, 8-bit quantization during optimization, reduced budgets around high-contrast edges, and preservation of white canvas where its mask applies. Multiple local encoders can be supplied through the CLI.

**No model means no generated defense.** There is no fallback that adds random noise and calls the image protected.

This is an original experimental baseline—not a reproduction of Glaze, DiffusionGuard, or DCT-Shield. Its objective targets encoder representations, not general visual understanding. Dedicated recognition, style-training, and temporal-defense objectives remain separate development work.

### Real transport tests

Every candidate is compared against its corresponding clean image after eight actual processing conditions:

**Unchanged; JPEG 95, 85, and 70; 75% resize; 90% crop; mild blur; and resize followed by JPEG.**

Both images receive the same transformation. The interface reports fidelity and remaining differences, with a before/after divider and amplified-difference view.

These are generic transport tests, **not verified replicas of particular social platforms**. Nor does a surviving pixel difference prove that an AI model was prevented from copying the artwork.

### External candidates and paired generation

Images processed by other tools can be imported, sanitized again, inspected, and tested through the same comparison workflow.

Optional editing and video benchmark adapters are also included. They use matched seeds and save sanitized output frames for review. Their orchestration was tested with stub generators; actual pretrained pipelines were not executed.

Candidate exports remain explicitly **UNVERIFIED**. There is no fabricated “98% protected” indicator.

---

## 5. Run it on Windows

Extract RIPOSTE somewhere **separate from your artwork and model folders**. With Python installed, open PowerShell in the extracted project and run:

```powershell
.\START.ps1 -ArtworkFolder "D:\Artwork\SocialSamples"
```

This creates a project-local environment, installs the core application, and opens the local interface. **Launching does not reorganize or delete your images.**

The first workflow is:

**Scan & organize → read-only preview → inspect blockers → explicitly confirm source replacement → Apply → Audit.**

The model-dependent lab requires an additional installation and compatible local weights:

```powershell
.\.venv\Scripts\python.exe -m pip install ".[lab]"
```

Weights are not bundled or automatically downloaded. The core organizer does not require them. Manual launch instructions are included for systems whose PowerShell policy blocks scripts.

---

## 6. Validation and handoff

| Executed check                                            |                      Result |
| --------------------------------------------------------- | --------------------------: |
| Source test suite                                         |              **194 passed** |
| Separately installed wheel, sharing existing dependencies |              **194 passed** |
| Final delivered ZIP, freshly extracted                    |              **194 passed** |
| Browser interaction/rendering checks                      |               **13 passed** |
| Actual loopback HTTP checks                               |                **9 passed** |
| Source/wheel package-file comparison                      | **17 byte-identical files** |

The browser checks used Chromium with an in-process transport to the real backend; separate HTTP checks exercised the running server. Tests establish implementation behavior, **not adversarial effectiveness**. Native Windows execution, CUDA, pretrained-model performance, and independent security auditing remain unvalidated.

The complete handoff is included in the ZIP and available individually:

**[Start guide](sandbox:/mnt/data/RIPOSTE/README.md)** · **[Development specification](sandbox:/mnt/data/RIPOSTE/docs/DEVELOPMENT-SPEC.md)** · **[Research dossier](sandbox:/mnt/data/RIPOSTE/docs/RESEARCH.md)** · **[Threat model](sandbox:/mnt/data/RIPOSTE/docs/THREAT-MODEL.md)** · **[Validation record](sandbox:/mnt/data/RIPOSTE/docs/VALIDATION.md)** · **[Final archive verification](sandbox:/mnt/data/RIPOSTE_v0.1.0_release_report.json)**

**The next substantive milestone is real-model qualification, followed by combined editing/mask/compression defenses and genuine text-guided video protection.** The acceptance criterion is demonstrably reduced reuse after processing, at an illustration quality you approve—not merely altered pixels or a completed render.

[1]: https://glaze.cs.uchicago.edu/faq.html "Glaze - Protecting Artists from Generative AI"
[2]: https://arxiv.org/abs/2310.13828 "[2310.13828] Nightshade: Prompt-Specific Poisoning Attacks on Text-to-Image Generative Models"
[3]: https://arxiv.org/abs/2410.05694 "[2410.05694] DiffusionGuard: A Robust Defense Against Malicious Diffusion-based Image Editing"
[4]: https://arxiv.org/abs/2504.17894 "[2504.17894] DCT-Shield: A Robust Frequency Domain Defense against Malicious Image Editing"
[5]: https://arxiv.org/abs/2607.25522 "[2607.25522] I2VShield: An Efficient Proactive Defense Framework against DiT-based Image-to-Video Models"
[6]: https://arxiv.org/abs/2607.01499 "[2607.01499] Anti-Prompt: Image Protection against Text-Guided Image-to-Video Generation"
[7]: https://arxiv.org/abs/2603.26154 "[2603.26154] IPV-Bench: Benchmarking Image Protection Methods under Diverse Image-to-Video Generation Scenarios"
