# RIPOSTE 0.3.0

**Local artwork protection. Clean masters in; reviewed publishing files out.**

RIPOSTE reconstructs image containers with date-only metadata, organizes your collection, and optimizes bounded changes directly into publishing rasters using explicitly selected local models. The main application is **Protect & publish**. The workshop is an optional helper for advanced comparisons of those same files.

**The organizer and publishing workflow are implemented and tested. The protection engines are experimental. No pretrained-model/CUDA efficacy is established by this release.** Passing a pixel-quality check, producing a different latent representation, or completing a render does not establish resistance to copying, editing, recognition, style learning, or animation. There are no watermarks, audience logins, licensing gates, artwork uploads, or fake protection percentages.

## Start on Windows

Extract the application separately from your artwork and model folders. Python 3.11+ is required; the launcher's suggested installation version is 3.13.

```powershell
.\START.ps1 -ArtworkFolder "D:\Artwork\SocialSamples"
```

This creates a project-local environment and opens the local browser interface. Starting the application does not organize or remove your images. To also install the optional model-processing dependencies:

```powershell
.\START.ps1 -ArtworkFolder "D:\Artwork\SocialSamples" -Lab
```

The `-Lab` name is retained for launcher compatibility; these dependencies power the main protection workflow as well as the workshop. This installs packages, **not model weights**. Your PyTorch build must support the selected device. Native Windows/macOS startup and CUDA were not executed in the release environment.

When a PowerShell policy blocks the launcher, the equivalent manual setup is:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install ".[lab]"
.\.venv\Scripts\python.exe -m riposte serve "D:\Artwork\SocialSamples"
```

On macOS/Linux, run `bash START.sh /path/to/artwork`; install the optional dependencies into `.venv` before using models. Do not put the application or model checkpoints inside the actively maintained artwork folder.

## The main workflow

**Scan & organize → Protect & publish → Review actual pixels → Download approved PNGs.**

1. Preview the recursive organization. Resolve blockers. Only applying an explicitly approved migration removes successfully replaced source files. There are no raw backups or quarantine copies.
2. Choose cleaned illustrations and one or more publishing edges. Enter local VAE folders, one per line, and select a device. Models load once per batch. `Test model execution` actually runs a numerical forward/input-gradient probe rather than merely checking that files exist.
3. Preview the batch, then protect it. Each distinct output size is optimized from the clean master independently. Small images are not enlarged; duplicate effective sizes are skipped. White-preservation, spatial channel limits, local RMS and colour-difference limits constrain the output.
4. Inspect each output at fit or native-pixel size, with optional amplified differences and matched JPEG/resize/crop/blur previews. Accept visual quality and acknowledge the unresolved AI-resistance status. Rejecting a previously accepted output excludes it from future packs.
5. Download the approved-image pack. It contains **only date-only PNGs in the requested calendar/size structure**—not clean baselines, test reports, IDs, model configurations or location metadata. Downloaded bytes are the exact accepted candidate bytes, not a resized or recompressed re-export.

The default numerical limits are working settings, **not empirically qualified recommended protection recipes**. Stronger settings may visibly damage an illustration without improving resistance. Empty or unusable model selections never fall back to arbitrary noise.

## Clean organization remains the first checkpoint

```text
2026 / September / SML / SML01.png
2025 / January   / MED / MED01.png
2024 / December  / LRG / LRG01.png
EVERYTHING_ELSE / March / XTL / XTL01.png
```

Bins use pixel area: SML below 1 million; MED below 4 million; LRG below 16 million; XTL 16 million or more. Months are English names. Directories are created only when needed. Images are not sorted by extension. Clean masters and publishing outputs are uniform lossless PNGs; a publishing output is classified by its **own** resolution, not its master's.

Source reconstruction applies orientation, converts supported colour profiles, makes fresh pixel storage, clears concealed RGB in fully transparent pixels, and writes only `Creation Time: YYYY-MM-DD`. Raw EXIF/GPS/XMP, comments, thumbnails, profiles and unknown ancillary chunks are not carried forward. Known metadata sidecars require explicit deletion authorization. Unsupported or unreadable inputs keep the checkpoint incomplete rather than silently passing.

Date basis defaults to filesystem creation/birth time when available, with an explicitly recorded modified-time fallback. Embedded-date and modified-date modes remain available. Filesystem modification time is not falsely described as a known download time.

Metadata cleaning does not erase visible information, arbitrary pixel steganography, other copies, filesystem recovery traces, or operating-system caches outside this application. This is not forensic secure erasure or a claim to make a publicly readable illustration unrecognizable to all models.

## Local model inputs

The main workflow requires at least one compatible local `AutoencoderKL` or `AutoencoderTiny` directory with `config.json` and safetensors. Tiny is a distilled encoder proxy, not an interchangeable full generator. Up to four encoders may be combined. Local model paths remain transient; safe technical identities and model-weight hashes, not the paths, enter batch records.

Two additional objectives are optional under advanced settings:

| Input | Implemented pathway | Scope |
|---|---|---|
| Nine-channel SD inpainting pipeline | Early masked-image conditioning displacement | Inpainting component proxy; not a generated-edit result |
| Stable Video Diffusion pipeline | First-step predicted-latent temporal-energy reduction, coupled to the image objectives | Actual temporal computation graph, but not generated video, not text-guided protection, not verified motion suppression |

All model classes are fixed/allowlisted; loading is offline, local-only and safetensors-only. Remote custom code is not loaded. No weights are bundled or automatically downloaded. Licensed model access, compatible package versions, sufficient memory and device support remain necessary. Added models can substantially increase time and memory; no GPU-memory benchmark is claimed.

```powershell
.\.venv\Scripts\python.exe -m riposte doctor
.\.venv\Scripts\python.exe -m riposte doctor --vae "D:\Models\LocalVAE" --execute
```

`doctor` without `--execute` reports package/device availability and optional model-file presence. `--execute` actually loads the selected encoder and checks a finite, nonzero image gradient. Neither is an efficacy test.

## Batch commands and recovery

Read-only preview, no model required:

```powershell
.\.venv\Scripts\python.exe -m riposte publish "D:\Artwork\SocialSamples" --all --edge 1024 --edge 1536 --plan
```

Protect the selected collection (clean masters stay unchanged):

```powershell
.\.venv\Scripts\python.exe -m riposte publish "D:\Artwork\SocialSamples" --all --vae "D:\Models\LocalVAE" --edge 1024 --edge 1536 --epsilon 4 --steps 24 --restarts 2
```

Use repeated `--image ID` instead of `--all` to target individual catalog images; `riposte list ROOT` shows their IDs. `--inpaint PATH` and `--video PATH` add the optional objectives. The CLI supports up to three distinct edges from 64 to 4096; the UI offers 1024, 1536 and 2048. Up to 200 images can be selected per request.

`riposte publications ROOT` lists batches. `riposte publications ROOT BATCH_ID` shows their items, blockers and review states. The completion label `FINISHED` means the queue was traversed, **not** that every item succeeded; always read the counts.

```powershell
.\.venv\Scripts\python.exe -m riposte resume "D:\Artwork\SocialSamples" BATCH_ID --vae "D:\Models\LocalVAE"
```

Resume validates the stored recipe, selected model identities, cleaned master hashes and committed output files. Completed items are kept byte-identically; pending/failed items are retried with the same per-item seed. An uncommitted clean orphan directory is removed before retry. Models must be reselected because their paths are not stored. Cooperative cancellation stops between model/iteration checkpoints, not in the middle of an individual forward pass.

After an operating-system crash, a stale `.riposte/operation.lock` may remain. Stop all RIPOSTE processes and verify no operation is still running before manually removing that lock. The application deliberately does not guess that an active lock is stale. Changing or corrupting a committed master/output is not silently repaired on resume.

Batch review is also available through repeated item flags; only assert approval after inspecting those illustrations:

```powershell
.\.venv\Scripts\python.exe -m riposte review "D:\Artwork\SocialSamples" BATCH_ID --item ITEM_ID --visual-accepted --acknowledge-unverified
.\.venv\Scripts\python.exe -m riposte package "D:\Artwork\SocialSamples" BATCH_ID
```

`package` writes `.riposte/exports/BATCH_ID/RIPOSTE.zip`. To revoke an approval, use `review ROOT BATCH_ID --item ITEM_ID --decision REJECTED`. New packs exclude it; an already downloaded copy cannot be recalled. ZIP entries use midnight date stamps without extra fields. Dates outside the ZIP format's representable calendar range use a container-safe boundary date; the PNG retains its actual full `YYYY-MM-DD` date.

## The workshop remains a helper

`Advanced model testing in the workshop` opens the **exact committed publishing raster**, without regeneration, and reuses an existing handoff when possible. Existing external comparisons, controlled encoder challenges, five-arm generation review and experimental standalone guard commands remain available. They are not required for a normal publishing batch and do not secretly determine a protection certification.

The previous SHROUD `.shroud` state remains readable. Use the UI's explicit upgrade action or `riposte upgrade ROOT` to rename its application state to `.riposte`; artwork and IDs are not rewritten. Existing 0.2 workspaces require no migration for the new publishing namespace.

## Development and evidence

```text
publication.py   Main batch planning, independent renditions, resume, review and exact-byte packs
release_guard.py Shared-raster, best-feasible quantized optimization
quality.py       Local damage, colour diagnostics and integer spatial budget
runtime_probe.py Real model forward/input-gradient execution check
temporal.py     Fixed SVD first-step temporal pathway (experimental)
server.py / cli.py / static/publish.*   Product entry points
lab.py / qualification.py / generation.py   Optional workshop
organizer.py / sanitize.py / store.py / policy.py   Inherited clean foundation
```

Read [engine mathematics](docs/ENGINE-v03.md), [publication contracts](docs/PUBLISHING.md), [validation](docs/VALIDATION.md), and [next grouped work](docs/WAVE-03-HANDOFF.md). The prior detailed manual is preserved as [historical 0.2 documentation](docs/HISTORY-v02-README.md); current behaviour takes precedence where it changed.

The 0.3 release executes real CPU autograd/codecs and UI/HTTP/storage operations on synthetic illustrations. Model-adapter tests use explicitly identified substitutes. No user's artwork was processed, no pretrained model was qualified, and no CUDA or native Windows/macOS launcher run occurred. Synthetic fixture values and screenshots are not AI-protection evidence.
