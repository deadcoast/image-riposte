# RIPOSTE
### Local artwork security workbench · v0.2.0

RIPOSTE continues the actual SHROUD v0.1.0 application. This release adds an image-first workbench, a coupled mask/codec optimization engine, noise-controlled qualification, and five-arm generation review. It is not a renamed screenshot or a replacement scaffold.

**Clean your images; inspect the candidate; challenge the evidence.** No watermarks, audience authentication, licensing gates, artwork uploads, telemetry, or automatic model downloads. The core organizer runs without machine-learning models. Model-dependent operations fail closed when a compatible local model is unavailable.

**Release boundary:** sanitation, organization, state migration, numerical algorithms, API behavior and browser interactions were exercised. Pretrained VAE/diffusion/video models and CUDA were not run in this environment. Every protection candidate remains `UNVERIFIED`. The included screenshots and demonstration evidence use original synthetic fixtures and explicitly labeled test doubles, not customer artwork or evidence of real-model protection.

## Start on Windows

Extract RIPOSTE separately from your artwork and model directories. Install Python 3.11 or newer; this release was tested with Python 3.13. Run from PowerShell in the extracted project:

```powershell
.\START.ps1 -ArtworkFolder "D:\Artwork\SocialSamples"
```

The launcher creates a project-local virtual environment, installs the core package when absent or at another version, and starts the local browser interface. First installation needs package-index access. Launching never organizes or deletes artwork automatically. The artwork directory must already exist. Keep the terminal running; Ctrl+C stops the server. Native PowerShell execution was not available for this release's tests.

Manual alternative when local PowerShell policy blocks the launcher:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe -m riposte serve "D:\Artwork\SocialSamples"
```

On macOS/Linux, `bash START.sh "$HOME/Artwork/SocialSamples"` provides the same local workflow. The shell script passed syntax inspection; native macOS execution was not tested. Manual commands are `python3 -m venv .venv`, `.venv/bin/python -m pip install .`, and `.venv/bin/python -m riposte serve "$HOME/Artwork/SocialSamples"`.

Only loopback is bound. The transient local session token secures editing controls; it is **not** an audience authentication requirement. No outside service is needed to view the interface after dependencies are installed.

**Use a dedicated artwork directory, not your home directory, Downloads root, application directory, virtual environment, or model directory.** All contents of the chosen artwork root are in scope. Unknown files block a complete cleanup checkpoint rather than being silently ignored or deleted.

## Existing SHROUD workspace

RIPOSTE recognizes the old `.shroud` state directory without rewriting it on a read. The interface offers an explicit upgrade, or run:

```powershell
.\.venv\Scripts\python.exe -m riposte upgrade "D:\Artwork\SocialSamples"
```

This changes application state to `.riposte` and updates its marker. Clean master images, asset IDs, dates, trial IDs and filenames are preserved. Do not manually rename the artwork hierarchy. Conflicting `.shroud` and `.riposte` directories, invalid markers or linked state directories fail closed. An interrupted directory/marker upgrade can be resumed. Rollback to the old application is not an automated feature.

## Workbench

The **Clean → Organize → Guard → Challenge → Export** sequence connects the existing catalog to actual actions. The left navigator contains only the real year/month/size hierarchy. The artwork inspector supplies a before/after divider, clean/candidate/amplified-difference views, actual transport previews, synchronized pan, fit and native-pixel zoom. `F` fits the view; `+` and `-` change zoom. The divider and zoom controls work with the keyboard as well as a pointer.

The right panel keeps Build, Challenge and Export adjacent to the image. Model challenge and generation review are distinct from the transport-fidelity table. Long jobs report their stage; model jobs can be cancelled at cooperative boundaries. Organizer source replacement is deliberately not cancellable from the interface halfway through a commit.

Metadata status and AI evidence are separate. A date-only image is not labeled protected. A runtime preflight is not labeled model execution. An external candidate's unknown optimization protocol is not labeled held out.

## First operation: scan, inspect, apply

Click **Scan & organize**, select the date basis, and run the read-only preview. Review the destination counts and blocker codes. The source-removal confirmation must be selected before Apply becomes available.

Or use the CLI:

```powershell
# Read-only: no files or folders created in a fresh workspace.
.\.venv\Scripts\python.exe -m riposte organize "D:\Artwork\SocialSamples"

# Explicitly authorize verified source replacement and known metadata-sidecar removal.
.\.venv\Scripts\python.exe -m riposte organize "D:\Artwork\SocialSamples" --apply --discard-sidecars

# Independent metadata/organization checkpoint.
.\.venv\Scripts\python.exe -m riposte audit "D:\Artwork\SocialSamples"
```

**`--apply` removes each successfully migrated original after a fresh, sanitized PNG has been written and verified. No raw originals are copied to a backup, quarantine directory, or Trash.** This is intentionally destructive to original metadata and filenames. Cleaned masters remain. Unsupported, changing, or failed inputs are not deleted; the checkpoint stays `INCOMPLETE`. Inspect a representative set before a large migration.

`--discard-sidecars` additionally authorizes deletion of `.xmp`, `.exif`, `.iptc`, `.aae`, `.DS_Store`, `Thumbs.db`, and `desktop.ini` files encountered in this dedicated artwork scope. Their contents are not retained. Without authorization they are blockers.

### Your directory scheme

```text
SocialSamples/
├── 2026/
│   └── September/
│       ├── SML/
│       │   └── SML01.png
│       └── LRG/
│           └── LRG01.png
├── 2025/
│   └── December/
│       └── MED/
│           └── MED01.png
└── .riposte/
    ├── WORKSPACE
    ├── catalog.sqlite3
    ├── last-run.json
    ├── lab/                 # Created only after a trial exists.
    ├── generations/         # Created only after a controlled generation run.
    ├── benchmarks/          # Earlier paired-runner compatibility outputs.
    └── exports/             # Created only after an explicit export.
```

The diagram is illustrative, not a folder template. Only needed year/month/size directories exist. Year roots are exactly `2026`, `2025`, `2024`, and `EVERYTHING_ELSE`; other years share the last root, with their exact dates retained inside files. English month names are displayed in calendar order in the application. Files are never classified by extension.

| Category | Total pixels, width × height | Example |
|---|---:|---|
| SML | Below 1,000,000 | 800 × 800 |
| MED | 1,000,000 to below 4,000,000 | 1600 × 1600 |
| LRG | 4,000,000 to below 16,000,000 | 3000 × 3000 |
| XTL | 16,000,000 or more | 5000 × 5000 |

These are consistent **resolution** categories, not judgments of artistic quality, sharpness, or AI resistance. Byte size is displayed separately. Filenames are collision-safe `SML01.png`, `SML02.png`, etc.; numbering expands beyond 99. Known, unchanged, clean catalog files are not renamed or re-encoded on repeated runs. Empty former directories are removed.

### Date behavior

Default `download` uses filesystem creation/birth time when available; otherwise it uses modified time and records that fallback. Filesystems do not always preserve the actual download date. This is not silently presented as known download history. `--date-mode modified` explicitly uses modified time. `--date-mode embedded` prefers supported embedded date fields before falling back.

The retained value is only `YYYY-MM-DD`: no time of day, timezone, camera serial, author, GPS, thumbnail, software name, comment, or source filename. The date-basis label is local catalog information, not image metadata.

## What the cleansing operation actually does

It decodes the visible raster, applies EXIF orientation, converts a usable source color profile to sRGB, rebuilds a fresh RGB/RGBA image, and writes a new 8-bit PNG. It does not edit an old EXIF structure in place. RGB values concealed behind fully transparent pixels are zeroed. A second reader verifies chunk types, CRCs, the date field, decompression bounds, invisible RGB, and absence of trailing data.

Only structural PNG chunks and one `Creation Time` date field are permitted. Embedded profiles, thumbnails, EXIF, XMP, comments and unknown ancillary chunks do not survive. Only **clean-output** hashes enter the catalog; raw source hashes, raw filenames, original paths and metadata dumps are never recorded by the application.

Fresh PNG is the intentional uniform output format in this release; this is not a type-based folder scheme. Existing JPEG samples are decoded once and saved without another lossy JPEG encoding. Clean masters keep their native dimensions and transparency. Public lab candidates are flattened on white and may be downscaled to the selected maximum edge; they are never upscaled.

Supported inputs: single-frame, supported 8-bit PNG, JPEG, WebP, BMP, TIFF, and GIF, identified by decoder content. High-bit-depth/HDR inputs, animations, layered project formats such as PSD, SVG, HEIC/AVIF/JXL, invalid color profiles, untagged CMYK/LAB, files above 512 MiB, and images above 60 million pixels require review. A failed input is not advertised as clean. Loss of layers, frames, bit depth, or color fidelity is not silently accepted.

This does **not** prove removal of information encoded in visible artwork or arbitrary pixel steganography. It does not erase other copies, SSD recovery data, operating-system caches, shell history, swap or backups. See [threat boundaries](docs/THREAT-MODEL.md).

## Install the optional laboratory

```powershell
.\.venv\Scripts\python.exe -m pip install ".[lab]"
.\.venv\Scripts\python.exe -m riposte doctor
```

For NVIDIA acceleration, select a compatible PyTorch/CUDA installation using the [official PyTorch installer](https://pytorch.org/get-started/locally/). `doctor` reports the actual installed build and CUDA availability. Installing the lab extra alone does not guarantee a CUDA-enabled torch build or compatible GPU. Do not substitute an unverified CUDA wheel command.

Weights are not bundled, fetched automatically or uploaded. Keep them outside the artwork folder. A supported local VAE directory contains `config.json` and safetensors weights. The new loader accepts fixed `AutoencoderKL` and `AutoencoderTiny` classes; Tiny is a distilled proxy, not a substitute for full-generator qualification. The optional early-edit probe needs a local Stable Diffusion **nine-channel inpainting** pipeline. Full generation adapters require the appropriate local pipeline components and CUDA.

```powershell
.\.venv\Scripts\python.exe -m riposte doctor --vae "D:\Models\local-model\vae"
```

`FILES_PRESENT_NOT_EXECUTED` means exactly that. File checks do not establish model compatibility, available GPU memory, useful gradients, or effective protection. No remote custom pipeline code or pickle-weight loading is requested by RIPOSTE. Use models from sources you trust and respect their separate license terms.

## Generate a candidate: coupled engine

List image IDs and choose an organized image:

```powershell
.\.venv\Scripts\python.exe -m riposte list "D:\Artwork\SocialSamples"
.\.venv\Scripts\python.exe -m riposte guard "D:\Artwork\SocialSamples" IMAGE_ID --vae "D:\Models\local-model\vae" --engine coupled --max-edge 1536 --epsilon 4 --steps 24 --device auto
```

Replace `IMAGE_ID` and `TRIAL_ID` placeholders with the IDs returned by the application. Multiple `--vae` arguments provide an encoder ensemble. The UI exposes one optimization VAE and an optional early-inpainting pipeline. Add `--pipeline "D:\Models\local-inpaint"` to use that probe from the CLI.

The original RIPOSTE `coupled-v1` experiment shares one constrained output raster across real JPEG-forward and resize views, masked encoder contexts, and optional early inpainting conditioning. It uses 8-bit quantization during optimization, integer spatial budgets, reduced edge changes, optional smooth-white preservation, and frequency-weighted search directions. The JPEG backward gradient is an explicit approximation, not a derivative of codec bitstreams. Default UI work is 24 iterations; the CLI retains its 48-iteration default unless `--steps` is supplied.

The default channel cap is `4/255`, not a promise of invisibility. White preservation can be disabled with `--no-preserve-white`. Final encoded channels are checked against the budget. Models with absent, detached, nonfinite or unusable gradients cannot silently turn into a noise-only result. CPU execution is allowed for optimization/encoder qualification but can be impractically slow. Full GPU performance is unmeasured.

`--engine encoder` retains the original EOT-VAE baseline for comparison. The new implementation is **not** a reproduction of DiffusionGuard, DCT-Shield, Glaze or any named paper. There is no built-in temporal or text-guided-video defense objective in v0.2.0. See [engine design](docs/ENGINE-v02.md).

## Challenge the candidate, not just its appearance

```powershell
.\.venv\Scripts\python.exe -m riposte qualify "D:\Artwork\SocialSamples" TRIAL_ID --vae "D:\Models\evaluation-model\vae" --device auto
```

Qualification compares the candidate with **three sign-scrambled controls preserving every absolute channel change**. This preserves original-raster peak change and RMS exactly, including pixels near channel limits. These are matched perturbation controls, not independent Gaussian noise and not additional defenses.

Each encoder is evaluated in 24 contexts: eight actual publication transforms × whole/right/bottom masks. Reports distinguish optimization transform families from held-out transform families only when that protocol is known. They distinguish identical model weights from different weights without asserting that different weights imply an unseen architecture. The strongest of the three controls is shown in each cell. These counts are descriptive; three controls do not establish a statistical security guarantee.

The qualification transforms include stronger JPEG compression, a resize/JPEG chain, an offset crop and blur. The transport-fidelity inspector separately retains the original eight-view suite, including JPEG 95/85/70. Both apply the same operation to clean/candidate rasters. Neither suite is advertised as a replica of a social platform's current processing.

## Review actual-generation experiments

The new five-arm runner uses clean, candidate and three matched controls with the same generation seeds in each arm:

```powershell
.\.venv\Scripts\python.exe -m riposte challenge "D:\Artwork\SocialSamples" TRIAL_ID --model "D:\Models\local-sd-pipeline" --task edit
.\.venv\Scripts\python.exe -m riposte challenge "D:\Artwork\SocialSamples" TRIAL_ID --model "D:\Models\local-inpaint-pipeline" --task inpaint
.\.venv\Scripts\python.exe -m riposte challenge "D:\Artwork\SocialSamples" TRIAL_ID --model "D:\Models\local-svd-pipeline" --task video
```

Defaults are two seeds, identity and JPEG 70, and five arms: **20 generation calls**, not one lightweight render. Use `--seed 7 --view identity` for five calls while checking a new local installation. `--seed` and `--view` can be repeated. Generation is CUDA-only in this release.

`edit` uses a reference SD img2img pipeline; `inpaint` uses a fixed nine-channel SD inpainting pipeline and reproducible right-region mask; `video` uses Stable Video Diffusion. These are reference baselines, not coverage of all modern generators. SVD is image-conditioned, **not text-guided video**. Output dimensions are standardized per task and recorded by the rendered frames; post-transform input fidelity is recorded separately because control equality need not survive codecs.

Generation review offers all five outputs, run/view/seed selectors and synchronized frame scrubbing. Outputs are date-only PNG frame sequences, not an MP4 export. Each frame is bound to the committed report hash. When a pipeline reports a content-filter flag, it is retained as such; a filtered output is not evidence of adversarial success. Same-seed divergence, output RMSE and adjacent-frame RMSE are descriptive only. Human review must judge source preservation, task success, instruction following, useful motion and quality.

The original `benchmark` command remains a two-arm compatibility path; prefer `challenge` for the controlled protocol. **Full pretrained pipelines were not exercised in this release environment.** Tests use explicit pipeline doubles and real tensor/mask/control-flow code.

## External candidate and export

```powershell
.\.venv\Scripts\python.exe -m riposte compare "D:\Artwork\SocialSamples" IMAGE_ID "D:\Candidate\processed.png" --max-edge 1536 --method external
.\.venv\Scripts\python.exe -m riposte export "D:\Artwork\SocialSamples" TRIAL_ID --acknowledge-unverified
```

Imported candidates are rebuilt and matched to the selected public raster, not blindly copied. The external input remains unchanged outside the workspace. A method name is a label, not proof that an upstream tool ran correctly. Unknown optimization settings remain unknown in evaluations.

Export requires a complete workspace checkpoint, intact trial images, a date-only audit, and explicit unverified acknowledgment. The exported `.riposte/exports/TRIAL_ID/candidate.png` contains the raster and retained date—not the lab report, model names, paths, or analysis. Nothing is automatically published.

## Development and evidence

The distribution includes source, tests, a wheel, screenshots, source provenance and verification records. See [validation](docs/VALIDATION.md) for exact executed counts and limits; [source map/specification](docs/DEVELOPMENT-SPEC.md), [engine contract](docs/ENGINE-v02.md), [research](docs/RESEARCH.md), [privacy boundaries](docs/THREAT-MODEL.md), [UI design](docs/UI-DESIGN.md), and [next grouped milestone](docs/WAVE-02-PLAN.md).

```bash
python -m pip install ".[test]"
python -m pytest -q
```

Numerical model tests need PyTorch and explicitly skip when it is absent. Browser QA additionally needs Playwright and Chromium. Test installation is optional and separate from the end-user core. There are no bundled font files or copied third-party reference artwork.
