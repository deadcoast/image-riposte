# Duplicate Finder / 2026-09-20

Implemented an independent read-only detector and review workflow across the CLI,
terminal and authenticated local browser/API. The source contract is
[DUPLICATES.md](../../docs/DUPLICATES.md); controls are in
[CLI.md](../../docs/CLI.md#duplicate-finder). No user artwork was processed by
these checks. The existing large synthetic fixture was read without modification.

## Executed evidence

| Check | Result and actual boundary |
| --- | --- |
| `focused-final.txt` | 49 passed, one native test separately selected. Real temporary files, image decoders, CLI, shared service, terminal controller, authenticated API and local FFmpeg; synthetic content. Includes all-member search/paging, stale previews, exports, foreign private state, hardlinks, incomplete results, limits and cancellation at five scan stages. |
| `suite-final.txt` | 1,484 passed, nine platform skips, three native browser tests separately selected; 286.19s. This broad run preceded the final endpoint return annotations, service-local variable rename and five additional cancellation cases; the final focused run covers those changes. |
| `native-browser-final.txt` | Four selected checks passed, including the three real Chromium harnesses for duplicate review, category sorting and publication review. Duplicate UI fixtures exercise inline validation, double submission, partial results, literal paths, group paging, unavailable previews, empty filters and out-of-order responses. Network fixtures isolate those UI states; this run alone is not backend integration proof. |
| `browser-live-final.txt`, `browser-live.json` | Actual FastAPI server, shared scanner, authenticated browser requests and six synthetic artwork files; no fetch/controller mocks. All three labels, filters, paired decoded images, measured evidence and full JSON export verified. Sources and mtimes unchanged. |
| `wide.png`, `narrow.png`, `wide-review.png`, `narrow-review.png` | Actual live-run screenshots at 1100×900 and 390×844, reduced motion; no horizontal document overflow. Paired imagery stacks on narrow screens. Screenshots were visually inspected. |
| `native-console-powershell.json`, `.txt`, `native-first.txt` | Actual START.ps1 and raw Windows ConPTY input: d entry, quoted/pasted folder, real scan, label filter, path search, evidence/coverage, g re-entry, return, zero exit and restored cursor. Synthetic inputs unchanged. This does not claim direct control of a VS Code terminal window or user acceptance of navigation. |
| `large-scan.json` | 5,101 inventoried/hashed files, 30,300,128 bytes; 322 media fingerprints collapsed into 47 content groups. 856 candidate pairs / 6,300 view comparisons yielded 39 exact groups, 16 MAYBE relationships and 279 RELATED relationships in 62.674s. Content/mtime inventory of 5,102 non-private files (including the excluded lease) matched before/after. Private state was excluded. This repetitive synthetic dataset is not an independent accuracy benchmark or general timing guarantee. |
| `contracts-final.txt`, `contract-review.json` | All seven external stages pass: 531 signatures, 62 leaf modules, 73 source files and 13 exact negative-consumer diagnostics. Twenty changed/new application owners explicitly reviewed against the retained sorter snapshot. |
| `raw-source-final.txt`, `raw-source-delta.json` | Strict implementation audit remains failing: 823 diagnostics in 36 of 65 files, versus 797 before. The 26 additions are calls into existing untyped presentation helpers. The five new detector modules have no diagnostics. No ignores, configuration relaxation or new stubtest exceptions. |
| `build-final.txt`, `packages.json` | Fresh offline build with repository-local uv cache. All 73 application bytes match reviewed source, wheel and sdist. Current README and Duplicate Finder guide are included in sdist. Native execution used the existing editable environment; PAC-034 clean installation remains shelved. |
| `governance.json` | Four frozen CSV hashes unchanged. Read-only PACER validation valid, no structural errors/warnings, twelve stale evidence records retained. Registration/reconciliation remains deferred. |

The full suite's nine skips are five unavailable Windows symlink privileges and
four POSIX terminal cases. FFmpeg and native Chromium were available and executed;
they were not substituted with model or decoder stubs. Dependency deprecation
warnings remain in the logs.

## Retained failures and repairs

- `interfaces-first.txt`: exporter treated a nonexistent target as a linked path;
  command construction dropped the optional report path. Both were repaired.
  The unauthorized-response assertion was corrected to the existing 401 contract.
- `video-first.txt`: a near-end seek on a one-FPS clip returned no frame. Bounded
  earlier seeks now retain their requested positions. The fixture helper's list
  return was also corrected in the new assertions. `video-second.txt` passes.
- The first large-directory attempt stopped at `STATE_DIRECTORY_CONFLICT` because
  the scanner used the general workspace-state validator. The independent
  `scan_root`/`scan_path` boundary now retains application/link protections without
  opening private state. Foreign `.riposte`/`.shroud` fixtures and the actual large
  directory pass; no unknown marker was edited, repaired or removed.
- `browser-first.txt`: sandbox blocked Chromium Page.navigate. The same isolated
  local check ran with the granted process permission. `browser-permitted.txt`
  then exposed an opaque nested evidence display, repaired to show named signals.
- `contracts-first.txt`: runtime alias introspection rejected two unnecessary
  public type aliases. Direct NDArray/Literal declarations preserve the types
  without a new exception. Initial raw diagnostics exposed missing API annotations
  and a service-local `options` name collision; both were repaired.
- `build.txt`: the shared user uv cache was inaccessible. The existing repository
  cache built successfully; no dependency installation or replacement environment.

## UI audit and remaining qualification boundaries

`design-audit-final.json` retains 73 report-mode findings: 70 static action-handler
false positives (handlers live in external JavaScript), one constructed-hash-link
false positive, one root DESIGN.md lookup despite the canonical docs location,
and one pre-existing publication textarea resize finding. The canonical ownership
map and native selects are in `docs/UX-CONTRACT.md`; new duplicate form validation
is explicit. New controls were traced to their handlers and exercised at the
scopes above. This is not a clean global design-audit claim. No native screen
reader, Japanese IME, independent human usability or all-platform acceptance is
claimed.

Similarity confidence is a weighted evidence score, not a calibrated probability.
No precision/recall qualification on independently labeled artwork was performed.
Only byte/full normalized pixel equality earns DUPLICATE. RELATED is bounded
perceptual overlap, not arbitrary semantic relatedness. Videos compare sampled
visual sequences, not audio or every frame. Crops/rotations, candidate retrieval,
image normalization and limits have the documented boundaries. Concurrent
filesystem activity is checked but is not an atomic snapshot. No removal or
automatic keeper decision was implemented or tested.

The task's integrated implementation is delivered at this evidence scope. Future
accuracy qualification needs a labeled independent collection; the project-wide
release milestone, typing debt and frozen-register reconciliation remain open.
