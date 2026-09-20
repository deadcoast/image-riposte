# Duplicate Finder / implementation contract

Duplicate Finder is a separate local analysis operation. It does not depend on
a sorted catalog and never sorts, deletes, renames or rewrites scanned files.
The selected root and its descendants are the scope. Application roots and links
retain the existing protection; internal recovery state is excluded. Float
folders are included by default with an explicit exclusion option: their user
contract excludes sorting, not independent inspection.

| Label | Evidence | Confidence meaning |
| --- | --- | --- |
| DUPLICATE | Verified byte equality, or identical normalized full-resolution still-image pixels | 100/100 for the stated equality only; metadata/container equality is identified separately |
| MAYBE DUPLICATE | Strong agreement between perceptual retrieval and structural, colour, alpha and geometry checks; video additionally requires sampled temporal agreement | Heuristic evidence score, never calibrated probability or proof of equivalence |
| CLOSELY RELATED | Supported shared visual structure, common transforms/crops or image/video frame overlap | Heuristic relationship score; not a claim that either file can replace the other |

Exact equivalence can form a group. Similarity must remain a direct relation
between two groups; A resembling B and B resembling C does not establish A=C.
Filenames alone cannot establish any content match. Low-information/flat visual
inputs abstain from fuzzy matching. Animated/multipage images remain byte-only
unless their complete sequence is compared; never classify from only frame one.

Retrieval uses compact DCT hashes and a bounded Hamming-distance index, followed
by independent pixel/structural evidence. Transform/crop support is explicitly
bounded, not arbitrary semantic or adversarial robustness. Video fingerprints
sample multiple timestamps, retain duration checks and never assert byte or
full-frame equivalence from samples. No audio-equivalence claim is made.

Reports bind an algorithm version, options, source identities and content hashes.
Changed sources invalidate relevant findings and preview media. Limits and
unreadable/unsupported files are visible coverage gaps; partial results cannot
be labelled a complete scan. Cancellation uses the shared job boundary.

Terminal review uses the existing palette, actions, input loop and report views;
browser review uses the existing local transport/job/session and native controls.
Review supports the three labels, search, paging, full member paths, confidence
and evidence. Side-by-side media comes only from recorded scan members after
identity/content revalidation. JSON export contains the full recorded report,
not only the visible page. CSV exports every finding's summary and representative
paths; it does not enumerate every member of an exact group. There is no delete
or apply action. See [the command and terminal controls](CLI.md#duplicate-finder).

The [pHash design](https://www.phash.org/docs/design.html) motivates frequency
hash retrieval; its distances do not prove content equality. The
[original SSIM resource](https://ece.uwaterloo.ca/~z70wang/research/ssim/) describes
structural image-quality comparison, not a duplicate-probability calibration.
This implementation's small-grid structural score is explicitly an adaptation,
not a claim to reproduce a standard full-resolution benchmark. Video sampling
uses the installed [FFmpeg](https://ffmpeg.org/ffmpeg.html) with bounded subprocess
output/time and local-file protocol restrictions.

Implementation details and limits:

- Files are SHA-256 hashed and matching bytes are compared again. Exact groups
  collapse before decoding; complete normalized RGBA pixels establish the second
  equality basis. Color normalization, orientation and transparent RGB cleanup
  follow the existing clean decoder. Metadata may differ in a pixel-equal group.
  Hardlink counts remain visible; group membership is not a storage-saving claim.
- Visual retrieval uses a 63-bit DCT hash within Hamming distance 12. Confirmation
  combines 32×32 block structure, visible colour, alpha, gradient and aspect ratio.
  MAYBE requires whole-frame coverage and stricter agreement than RELATED.
  Rotation is in 90-degree steps; mirroring and fixed center/corner crops are
  supported. Arbitrary crops, small edits, overlays, semantic subject matches and
  adversarial changes can be missed. Similar filenames do not increase confidence.
- Flat/low-information images abstain from visual matching. Animated, multipage,
  high-bit-depth or unsupported decoder inputs can still produce byte matches;
  their missing visual comparison is reported, not used to block other findings.
- Videos need local FFmpeg and ffprobe. Five requested timestamps span 10–90% of
  duration. If a seek yields EOF, earlier bounded positions are tried and the
  successful seek is recorded. Video MAYBE requires four strong aligned samples,
  duration agreement and a distinctive sequence. Static repetitions are RELATED.
  Seek positions are not frame-accurate presentation timestamps; audio and
  unsampled frames are not compared. This does not establish full video equality.
- The index caps each query at 20,000 visited nodes / 10,000 returned references,
  keeps at most eight view candidates per file-group pair, and obeys the configured
  visual/file/pair/finding limits. Hitting a cap produces explicit missingness.
  This is bounded candidate retrieval, not an exhaustive all-pairs guarantee.
- Links, junctions and special files are skipped. `.riposte`, `.shroud`, `.git`,
  `__pycache__` and the operation lease are excluded. The standalone scanner never
  opens or repairs private sorting/publishing state. `_float_` and `__float__`
  follow the independent include-float option, with no change to sorting rules.
- Source identities are checked again at completion. A changed source removes its
  affected group/relationships; a changed directory set clears findings and asks
  for a rescan. This is not an atomic filesystem snapshot. Preview rehashes the
  requested source, emits a fresh metadata-free PNG thumbnail, and rejects stale
  evidence. A report is historical once files change.
- Reports contain paths, content fingerprints and file identities. They remain
  local unless explicitly exported. JSON is complete evidence; CSV is a summary
  with spreadsheet formula-prefix escaping. Export never overwrites a file.

The [validation record](../evidence/duplicates/README.md) distinguishes actual
local decoder/API/browser/launcher execution from classification qualification.
Synthetic fixtures qualify exercised mechanics. Precision/recall and calibrated
confidence on an independently labeled artwork collection remain unmeasured.
