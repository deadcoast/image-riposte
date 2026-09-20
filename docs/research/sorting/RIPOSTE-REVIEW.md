# Research review and integration / 2026-09-20

The user supplied `sorting-method01.md` (general filename NLP) and
`sorting-method02.md` (directory-specific categorization), authorizing useful
integration while retaining year/month organization. These source documents are
retained unchanged. This review distinguishes their recommendations from tested
RIPOSTE behavior. Implementation evidence belongs in `evidence/sorting-research/`.

## Critical assessment

| Research proposal | Assessment for RIPOSTE | Decision |
| --- | --- | --- |
| Preserve raw names; compare normalized filename features | Directly useful. Existing private title records already preserve originals. CamelCase is currently missed. | Add a versioned comparison view; retain Unicode and original names. Preserve old saved-rule matching alongside new CamelCase boundaries. |
| Suppress dates, counters, dimensions and export boilerplate | Useful for automatic discovery, but words such as `old`, `new`, or product model numbers can be meaningful. Removing tokens before n-grams fabricates phrases. | Conservative noise recognition for discovery only; removed tokens break phrases. Explicit rules remain authoritative. |
| Document frequency and IDF | Useful corpus-relative evidence, already partly present in simple discovery. Copies can inflate support. | Count normalized filename families once; require recurring support; exclude ubiquitous vocabulary from automatic groups. |
| NPMI term graph | Useful association evidence, not proof of semantic equivalence. Phrases and their constituent words create tautological edges. The sample NPMI function divides by zero when joint probability is one. | Sparse observed-pair graph, explicit degenerate handling, no overlapping-term edges. Use deterministic anchor neighbourhoods, not a claim to implement modularity optimization. |
| Automatic community naming | Statistical centrality cannot establish a desired taxonomy. Stable ordering is not stability under corpus changes. | Use literal supported terms as proposed folder labels. Keep existing catalog categories on subsequent runs; never rename them because a new automatic label wins. |
| Confidence threshold and UNKNOWN/REVIEW | Good abstention principle. Values .25/.05 and .35/.08 are inconsistent illustrative thresholds, not calibrated probabilities. | Report weighted lexical coverage and margin as heuristics. Abstention means ordinary year/month/media/size, never a blocked sort or mandatory review folder. |
| Cosine classification | The prose describes cosine; the prototype implements IDF overlap divided by total file weight instead. These are different scores. | Name the implemented score IDF coverage, expose evidence and margin, and do not call it a probability or measured accuracy. |
| NER, CRF, SVM, fuzzy aliases, NMF/HDBSCAN, embeddings | Some techniques may be useful after local labels/benchmarks exist. The supplied documents contain no labeled RIPOSTE corpus or measured comparison. | Defer model training and automatic fuzzy/entity claims. No new model downloads, cloud calls, or runtime dependencies. |
| Million-file scalability | The prototype materializes all records and potentially quadratic per-title pairs. An earlier helper iterates every vocabulary pair. Library choice alone does not qualify scale. | Bound optional analysis explicitly; on resource exhaustion return to ordinary sorting. Retain cancellation and measure tested sizes. No million-file acceptance claim. |
| Journals, collision checks, source identity, manifest-first apply | Already stronger in RIPOSTE than the prototype. Reverse moves alone do not safely undo sanitized images, occupied originals, interrupted operations or changed files. | Integrate proposals into existing exact receipts and private recovery, never introduce a second mover. |
| Long paths and Windows naming | A fixed 260-character check is not a universal modern Windows capability test. The prototype silently skips unreadable paths and does not fully establish junction safety. | Reuse current path/slug/link checks and visible scan errors; no guessed platform limit or silent omission. |
| Category folders instead of chronology | Conflicts with the user's desired outer structure. Current source also hard-codes just 2024-2026 and merges other years. | Retain Year/Month/img-or-vid/[Category if found]/Size and use actual four-digit calendar years. Read legacy EVERYTHING_ELSE catalogs; relocation remains previewed and undoable. |

## Integration contract

The existing three actions remain Sort, Dry Run and Enter Path. Category-enabled
sorting computes a deterministic local corpus proposal in the existing preview.
Manual choices and saved rules take precedence. Existing categories survive
automatic rediscovery; contradictory saved rules abstain rather than being
overridden. New automatic categories use vocabulary not claimed by saved rules.
Unknown titles, small/homogeneous corpora, weak evidence and analysis limits all
retain ordinary sorting. No rule file is silently saved.

The corpus uses eligible filenames and available private original-title records,
not parent-folder names, image pixels, EXIF semantics or a downloaded model.
`_float_`, `__float__`, private history and linked paths cannot supply vocabulary.
Year/month still comes from the selected date policy, not guessed filename dates.
Scores, matched terms, algorithm version and proposed destinations enter the
preview receipt. Changing relevant inputs invalidates Apply as before.

Discovery exposes the same group evidence for optional reusable-rule editing.
Discovery reads current basenames; the sort planner also consults existing private
original-title records. Neither invents descriptive titles for untracked numbered
files. Established category anchors are preferred on later imports; equivalent
phrases and words are suppressed when they supply the same group evidence.
The browser and terminal retain their canonical controls and tokens. No extra
mandatory workflow, filesystem category duplication or generated public tags.

Automatic analysis requires six distinct normalized filename families, support
from three families per anchor, NPMI at least .3 for associated terms, weighted
coverage at least .6 and a lead of .15 over the next group. These are conservative
engineering starting values, **not calibrated acceptance thresholds**. New
anchors occurring in more than 80% of families are treated as boilerplate;
existing category anchors can survive that filter. A group contains its anchor
and at most eleven directly associated terms; it is not a transitive community.

Limits are 50,000 families, 100,000 distinct terms, 200,000 observed pairs,
48 terms per title and 32 groups. Exceeding a limit discards automatic proposals
without disabling saved rules or ordinary sorting. These bounds apply to the
optional lexical stage, not the entire media inventory or image decoding. The
new module does not promise million-file or constant-memory folder processing.

Executed results, retained failures, scaling measurements and qualification
limits are in [the evidence record](../../../evidence/sorting-research/README.md).

## Source checks

The [scikit-learn feature extraction reference](https://scikit-learn.org/stable/modules/feature_extraction.html#tf-idf-term-weighting)
confirms smoothed IDF and distinguishes it from L2-normalized vectors. Its stopword
guidance cautions against a universal English list. Those primitives support this
design; they do not establish filename-classification accuracy.

The [NetworkX greedy-modularity reference](https://networkx.org/documentation/stable/reference/algorithms/generated/networkx.algorithms.community.modularity_max.greedy_modularity_communities.html)
describes a graph partition objective and resolution-dependent groups. That
objective does not validate category names or human usefulness. This integration
uses bounded anchor neighbourhoods instead, making its different behavior explicit.

Research 01 contains non-resolvable conversation citation markers; they are not
standalone provenance. Research 02 includes usable links, but its performance
and preference adjectives remain hypotheses. Synthetic regressions will qualify
mechanics and counterexamples only. A labeled, family-separated local corpus is
still needed to estimate precision, coverage and taxonomy usefulness.
