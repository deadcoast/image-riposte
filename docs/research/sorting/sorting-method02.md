# Technical report: deterministic filename intelligence for large Windows directories

Your problem has a fairly precise modern name:

**corpus-relative short-text categorization**, combining **keyword/phrase extraction, statistical term association, graph clustering, and sparse text classification**.

For your particular case, I would **not** start with NER, transformers, embeddings, or an LLM. Your strongest signal is exactly what you identified: **repeated words inside a locally coherent corpus**.

The directory itself becomes the statistical context.

A system can discover that:

```text
female_soldier_sniper_desert_01.png
female_soldier_sniper_uniform.png
male_soldier_sniper_desert.png

factory_pipe_rust_wall.png
factory_pipe_broken.png
factory_rust_floor.png

oak_tree_forest_autumn.png
pine_tree_forest_snow.png
forest_rock_moss.png
```

contains natural lexical structures resembling:

```text
SOLDIER
    female
    male
    sniper
    uniform
    desert

FACTORY
    pipe
    rust
    broken
    wall
    floor

FOREST
    tree
    oak
    pine
    autumn
    snow
    rock
    moss
```

without understanding English in the LLM sense.

The underlying machinery is counting, probability, information theory, sparse linear algebra, graph theory, clustering, and optionally classical supervised ML.

---

## 1. The architecture I recommend

For your directory, my default design would be:

```text
WINDOWS DIRECTORY
       │
       ▼
filename inventory
       │
       ▼
Unicode + filename normalization
       │
       ├── unigram extraction
       ├── bigram/trigram extraction
       └── character n-grams
       │
       ▼
document frequency / corpus statistics
       │
       ▼
phrase association
   PMI / NPMI / Dice
       │
       ▼
term co-occurrence graph
       │
       ▼
community detection
       │
       ├── category A
       ├── category B
       ├── category C
       └── noise
       │
       ▼
category naming
       │
       ▼
file → category scoring
       │
       ▼
multi-label / confidence / UNKNOWN
       │
       ▼
DRY-RUN MOVE MANIFEST
       │
       ▼
optional user approval
       │
       ▼
filesystem transaction
```

This approach is more appropriate than semantic AI when your files are already substantially self-describing.

The statistical corpus is effectively the classifier.

---

## 2. The key distinction: frequency is useful, but frequency alone is insufficient

Suppose your corpus contains 100,000 filenames.

You find:

```text
texture       61,200
factory       18,300
pipe           8,500
rust           7,900
wall           7,200
forest         6,900
tree           6,200
female         5,700
character      5,100
```

A naive program might create:

```text
TEXTURE/
FACTORY/
PIPE/
RUST/
WALL/
FOREST/
...
```

That is wrong.

`texture` may describe almost everything and therefore tell you almost nothing.

The useful question is not:

> How often does this word occur?

It is:

> Does this word identify a coherent subset of this corpus?

That is why **document frequency, inverse document frequency, co-occurrence, mutual information, entropy, and graph structure** matter.

---

## 3. Tokenization: filenames are not sentences

This is important.

Generic NLP tokenizers are usually designed for prose. Filenames have a different grammar:

```text
FEMALE_Soldier-DesertSniper_v03_FINAL_4k.png
```

A filename parser should recognize:

```text
FEMALE
Soldier
Desert
Sniper
v03
FINAL
4k
```

and separately identify likely metadata/noise:

```text
v03
FINAL
4k
```

while preserving the original string.

I recommend keeping three representations:

```text
RAW
FEMALE_Soldier-DesertSniper_v03_FINAL_4k

TOKENS
female soldier desert sniper v03 final 4k

SEMANTIC
female soldier desert sniper
```

Do not destructively rewrite the original filename during analysis.

For Unicode, preserve the original text and create a normalized comparison representation. Windows supports Unicode long filenames, but filenames still have reserved characters and names, and ordinary Windows behavior should be treated as case-insensitive unless you explicitly know otherwise. Microsoft also reserves names such as `CON`, `PRN`, `AUX`, `NUL`, `COM1`, `LPT1`, etc. ([Microsoft Learn][1])

---

## 4. A reasonable deterministic filename tokenizer

```python
import re
import unicodedata
from pathlib import Path


CAMEL_1 = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
CAMEL_2 = re.compile(r"(?<=[A-Z])(?=[A-Z][a-z])")

DATE = re.compile(
    r"""
    (?:
        (?:19|20)\d{2}[-_.]?\d{1,2}[-_.]?\d{1,2}
        |
        \d{1,2}[-_.]\d{1,2}[-_.](?:19|20)?\d{2}
    )
    """,
    re.VERBOSE,
)

RESOLUTION = re.compile(r"(?i)\b\d{3,5}x\d{3,5}\b")
VERSION = re.compile(r"(?i)\bv\d{1,4}\b")
PURE_NUMBER = re.compile(r"^\d+$")


NOISE = {
    "final",
    "copy",
    "edited",
    "edit",
    "image",
    "img",
    "photo",
    "export",
    "new",
    "old",
    "temp",
    "tmp",
}


def tokenize_filename(filename: str) -> list[str]:
    stem = Path(filename).stem

    # Preserve compatibility while normalizing visually equivalent forms.
    text = unicodedata.normalize("NFKC", stem)

    # CamelCase / PascalCase.
    text = CAMEL_2.sub(" ", text)
    text = CAMEL_1.sub(" ", text)

    # Metadata classes.
    text = DATE.sub(" ", text)
    text = RESOLUTION.sub(" ", text)
    text = VERSION.sub(" ", text)

    # Filename separators.
    text = re.sub(r"[_\-.+@()\[\]{}]+", " ", text)

    tokens = []

    for token in text.split():
        token = token.casefold().strip()

        if len(token) < 2:
            continue

        if token in NOISE:
            continue

        if PURE_NUMBER.match(token):
            continue

        tokens.append(token)

    return tokens
```

A system like this will behave identically tomorrow given identical inputs.

That reproducibility is one of the biggest advantages over LLM categorization.

---

## 5. Unigrams, bigrams, trigrams

Do not restrict the system to individual words.

These are unigrams:

```text
heavy
metal
female
soldier
machine
gun
```

But these may be far more meaningful:

```text
heavy metal
female soldier
machine gun
concept art
pixel art
wood floor
brick wall
```

You therefore want:

$$
n \in \{1,2,3\}
$$

grams.

Python:

```python
def ngrams(tokens, n):
    return [
        " ".join(tokens[i:i+n])
        for i in range(len(tokens) - n + 1)
    ]


tokens = ["female", "soldier", "heavy", "armor"]

print(ngrams(tokens, 1))
print(ngrams(tokens, 2))
print(ngrams(tokens, 3))
```

Output:

```text
['female', 'soldier', 'heavy', 'armor']

['female soldier',
 'soldier heavy',
 'heavy armor']

['female soldier heavy',
 'soldier heavy armor']
```

However, generating phrases is easy.

Determining which phrases are meaningful is the interesting part.

---

## 6. Document frequency: your first important statistic

For filenames, **document frequency** is usually more useful than raw token frequency.

Let:

$$
N = \text{number of filenames}
$$

and:

$$
df(t)=\text{number of filenames containing term }t
$$

If:

```text
forest forest forest tree.png
```

contains `forest` three times, document frequency still counts that filename once.

Python:

```python
from collections import Counter


def document_frequency(documents):
    df = Counter()

    for tokens in documents:
        df.update(set(tokens))

    return df
```

This immediately gives you the recurring vocabulary of the corpus.

---

## 7. TF-IDF

TF-IDF remains extremely useful for this problem.

For term \(t\) and filename \(d\):

$$
TFIDF(t,d)
=
TF(t,d)\times IDF(t)
$$

A common smoothed formulation is:

$$
IDF(t)
=
\log
\left(
\frac{1+N}{1+df(t)}
\right)+1
$$

Scikit-learn uses this general form and supports sublinear TF scaling:

$$
TF'=1+\log(TF)
$$

when requested. ([Scikit-learn][2])

### Numeric example

Assume six filenames:

```text
forest_wolf_hunting_night
forest_wolf_running
forest_deer_night
city_car_night
city_car_rain
city_bus_rain
```

Then:

$$
N=6
$$

For `wolf`:

$$
df(wolf)=2
$$

Therefore:

$$
IDF(wolf)
=
\log(7/3)+1
\approx 1.847
$$

For `night`:

$$
df(night)=3
$$

$$
IDF(night)
=
\log(7/4)+1
\approx1.560
$$

`wolf` receives greater specificity because it describes fewer documents.

---

## 8. Why character n-grams matter enormously for filenames

Word extraction fails on things like:

```text
cyberpunkFemale01
Cyber-Punk_Female
cybrpunk_fem
cyberpunkfemale
female-cyberpunk
```

Character n-grams recover much of the similarity.

For:

```text
cyberpunk
```

character trigrams include:

```text
cyb
ybe
ber
erp
rpu
pun
unk
```

Scikit-learn supports both raw character n-grams and `char_wb`, where character n-grams are generated inside word boundaries. ([Scikit-learn][2])

For messy filenames, I would often combine:

```text
word n-grams: 1–2
character n-grams: 3–5
```

This is one of the strongest classical text representations available for this problem.

---

## 9. PMI: discovering words that belong together

Raw co-occurrence can be misleading.

Suppose:

```text
female
```

and:

```text
soldier
```

occur together frequently.

Pointwise Mutual Information asks whether they occur together **more often than expected by chance**.

$$
PMI(x,y)
=
\log
\frac{P(x,y)}
{P(x)P(y)}
$$

Using the six-file example:

```text
forest_wolf_hunting_night
forest_wolf_running
forest_deer_night
city_car_night
city_car_rain
city_bus_rain
```

For:

```text
wolf
forest
```

we have:

$$
P(wolf)=2/6
$$

$$
P(forest)=3/6
$$

$$
P(wolf,forest)=2/6
$$

Therefore:

$$
PMI(wolf,forest)
=
\ln
\left(
\frac{2/6}
{(2/6)(3/6)}
\right)
$$

$$
=
\ln(2)
\approx0.693
$$

That is positive association.

Now `wolf` and `night`:

$$
P(wolf,night)=1/6
$$

Expected probability:

$$
P(wolf)P(night)
=
(2/6)(3/6)
=
1/6
$$

Therefore:

$$
PMI=0
$$

So although `wolf` and `night` appear together once, there is **no statistical evidence that they belong together beyond chance**.

That distinction is extremely useful.

---

## 10. NPMI is usually preferable

PMI can disproportionately reward very rare pairs.

Normalized PMI is:

$$
NPMI(x,y)
=
\frac{PMI(x,y)}
{-\log P(x,y)}
$$

Its range is approximately:

$$
[-1,1]
$$

where:

```text
+1    extremely strong association
 0    statistical independence
-1    mutually exclusive
```

For `wolf` and `forest`:

$$
PMI=0.693
$$

$$
-\log(2/6)=1.099
$$

therefore:

$$
NPMI
=
0.693/1.099
\approx0.631
$$

That is a substantial association.

This gives you an excellent automatic phrase/category detector.

---

## 11. Python implementation of NPMI

```python
from collections import Counter
from itertools import combinations
from math import log


def corpus_statistics(documents):
    """
    documents:
        list[set[str]]
    """

    n_docs = len(documents)

    df = Counter()
    pair_df = Counter()

    for terms in documents:
        terms = set(terms)

        df.update(terms)

        for a, b in combinations(sorted(terms), 2):
            pair_df[(a, b)] += 1

    return n_docs, df, pair_df


def npmi(a, b, n_docs, df, pair_df):
    key = tuple(sorted((a, b)))

    joint_count = pair_df.get(key, 0)

    if joint_count == 0:
        return -1.0

    px = df[a] / n_docs
    py = df[b] / n_docs
    pxy = joint_count / n_docs

    pmi = log(pxy / (px * py))

    return pmi / (-log(pxy))
```

This is fully deterministic.

---

## 12. Build a term graph

This is the part I think fits your directory especially well.

Represent each meaningful term as a graph node.

Connect two nodes when their NPMI exceeds a threshold.

For example:

```text
             sniper
             /    \
         rifle    soldier
                   /   \
                male   female
                  \     /
                   armor
```

Another component:

```text
rust ── pipe ── factory ── machinery
 │       │
wall   broken
```

Another:

```text
forest ── tree ── pine
   │       │
  moss    oak
```

At this point you are no longer trying to classify filenames directly.

You are discovering **communities in the vocabulary**.

That is a graph clustering problem.

NetworkX currently provides greedy modularity, Louvain, and—with a supporting backend—Leiden community detection. ([NetworkX][3])

---

## 13. Modularity

Community-detection algorithms often maximize modularity.

A standard generalized form is:

$$
Q
=
\frac{1}{2m}
\sum_{ij}
\left(
A_{ij}
-
\gamma
\frac{k_i k_j}{2m}
\right)
\delta(c_i,c_j)
$$

where:

$$
A_{ij}
$$

is the observed graph edge weight,

$$
k_i,k_j
$$

are node degrees,

$$
m
$$

is total graph weight,

and:

$$
\delta(c_i,c_j)=1
$$

when nodes belong to the same community.

NetworkX documents this formulation and exposes the resolution parameter \(\gamma\), which controls preferred community scale. ([NetworkX][4])

In practical language:

> Terms belong to the same category when they connect to one another substantially more than would be expected merely because they are common.

That is almost exactly your problem statement.

---

## 14. Deterministic graph categorization

For maximum reproducibility, I would initially use **greedy modularity** rather than a stochastic clustering algorithm.

```python
import networkx as nx


def build_graph(
    n_docs,
    df,
    pair_df,
    min_df=3,
    min_pair_df=2,
    min_npmi=0.20,
):
    G = nx.Graph()

    valid_terms = sorted(
        term
        for term, count in df.items()
        if count >= min_df
    )

    for term in valid_terms:
        G.add_node(term, df=df[term])

    for a, b in combinations(valid_terms, 2):
        count = pair_df.get((a, b), 0)

        if count < min_pair_df:
            continue

        association = npmi(
            a,
            b,
            n_docs,
            df,
            pair_df,
        )

        if association >= min_npmi:
            G.add_edge(
                a,
                b,
                weight=association,
                cooccur=count,
            )

    return G


communities = nx.community.greedy_modularity_communities(
    G,
    weight="weight",
    resolution=1.0,
)
```

Greedy modularity repeatedly joins communities where doing so most increases modularity. ([NetworkX][5])

---

## 15. Category names can also be deterministic

Suppose one vocabulary community contains:

```text
factory
industrial
pipe
rust
machinery
wall
broken
abandoned
```

You need to decide what to call it.

Do not ask an LLM.

Calculate a label score.

For example:

$$
LabelScore(t)
=
IDF(t)
\times
\log(1+df(t))
\times
C(t)
$$

where:

$$
C(t)
$$

is graph centrality inside its category.

The result tends to prefer terms that are:

```text
not extremely rare
not globally ubiquitous
strongly connected to the category
```

Python:

```python
from math import log


def idf(term, n_docs, df):
    return log((1 + n_docs) / (1 + df[term])) + 1


def category_labels(G, community, n_docs, df):
    members = set(community)

    subgraph = G.subgraph(members)

    centrality = nx.degree_centrality(subgraph)

    scores = {}

    for term in members:
        scores[term] = (
            idf(term, n_docs, df)
            * log(1 + df[term])
            * centrality.get(term, 0.0)
        )

    return sorted(
        scores.items(),
        key=lambda x: (-x[1], x[0]),
    )
```

You may get:

```text
factory      8.91
industrial   8.23
machinery    6.70
pipe         6.21
rust         5.81
```

The category becomes:

```text
factory
```

with aliases:

```text
industrial
machinery
pipe
rust
```

No generative AI required.

---

## 16. Category assignment

Once the categories exist, each category becomes a weighted vector.

Suppose category \(C\) contains:

$$
C=
\{
factory,
pipe,
rust,
industrial
\}
$$

and file \(d\) contains:

$$
d=
\{
factory,
rust,
wall
\}
$$

You can compare them using weighted cosine similarity:

$$
\cos(d,C)
=
\frac{
d\cdot C
}{
||d||\,||C||
}
$$

This is considerably better than:

```python
if "factory" in filename:
    move_to_factory()
```

because multiple pieces of evidence reinforce one another.

---

## 17. Multi-label categorization

A filename may genuinely belong to several categories.

```text
female_soldier_factory_sniper.png
```

Potential categories:

```text
CHARACTER
SOLDIER
FACTORY
WEAPON
```

Do not force a single category unless your filesystem requires one.

Internally:

```json
{
  "file": "female_soldier_factory_sniper.png",
  "categories": [
    ["soldier", 0.91],
    ["factory", 0.71],
    ["weapon", 0.68]
  ]
}
```

Then your physical folder policy can decide:

```text
primary category = SOLDIER
tags = FACTORY, WEAPON
```

or:

```text
SOLDIER/
    FACTORY/
```

This separation between **semantic classification** and **physical folder layout** is important.

---

## 18. Confidence margins

Suppose scores are:

```text
factory      0.82
industrial   0.79
mechanical   0.18
forest       0.03
```

The absolute best score is high, but the first two are nearly tied.

Define:

$$
margin=s_1-s_2
$$

Here:

$$
margin=0.03
$$

That is ambiguous.

Compare:

```text
factory      0.82
industrial   0.31
forest       0.07
```

Now:

$$
margin=0.51
$$

Much safer.

A deterministic rule might be:

```python
if top_score < 0.35:
    UNKNOWN

elif top_score - second_score < 0.08:
    REVIEW

else:
    ACCEPT
```

The actual thresholds should come from your corpus.

---

## 19. Corpus-relative reasoning is especially important for you

You said:

> the scope of the image directory is usually linear to what its theme is.

That is a major advantage.

Imagine a directory consisting entirely of industrial artwork.

Globally:

```text
factory
industrial
machinery
```

might be highly meaningful.

Inside that directory, though, they might occur in 80% of files.

They are therefore poor *internal* discriminators.

Inside the corpus, more useful divisions might be:

```text
pipe
boiler
conveyor
control panel
rust
vent
tank
furnace
```

So all weights should be calculated relative to the current directory.

You can formalize directory-specific lift:

$$
Lift(t,D)
=
\frac{P(t|D)}
{P(t|Global)}
$$

For example:

```text
P("boiler" | industrial_directory) = 0.18

P("boiler" | all_directories) = 0.006
```

Then:

$$
Lift
=
0.18/0.006
=
30
$$

`boiler` is thirty times more characteristic of that directory than of the global corpus.

This lets nested directories develop their own vocabulary automatically.

---

## 20. Entropy: finding terms that are too generic

Once rough categories exist, calculate the distribution of each term across categories.

For term \(t\):

$$
H(t)
=
-\sum_c
P(c|t)\log P(c|t)
$$

Suppose `texture` appears equally across four categories:

$$
P(c|texture)=0.25
$$

for each.

Then:

$$
H(texture)
=
-\sum_1^4 0.25\ln0.25
=
\ln4
$$

High entropy.

It does not distinguish categories.

Now suppose `sniper` occurs:

```text
94% SOLDIER
 4% WEAPON
 2% OTHER
```

Its entropy is much lower.

Therefore it is a strong category term.

A useful normalized form:

$$
H_{norm}
=
\frac{H}{\log K}
$$

Then:

$$
Specificity=1-H_{norm}
$$

Now your label score can become:

$$
Score(t)
=
IDF(t)
\times
Centrality(t)
\times
(1-H_{norm}(t))
$$

Very effective and still completely deterministic.

---

## 21. Chi-square once categories exist

If you have category labels—even labels automatically discovered and then reviewed—chi-square gives another way of identifying which terms discriminate categories.

$$
\chi^2
=
\sum_i
\frac{(O_i-E_i)^2}{E_i}
$$

where:

```text
O = observed count
E = expected count
```

Scikit-learn's `chi2` implementation explicitly supports term-count/frequency features against class labels and uses the statistic for feature selection. ([Scikit-learn][6])

Example:

```python
from sklearn.feature_selection import chi2

scores, pvalues = chi2(X_counts, labels)
```

This becomes especially useful after you have manually validated the first category taxonomy.

---

## 22. Mutual information

Mutual information measures how much knowing feature \(X\) reduces uncertainty about class \(Y\):

$$
I(X;Y)
=
\sum_{x,y}
P(x,y)
\log
\frac{P(x,y)}
{P(x)P(y)}
$$

It is zero for independent variables and increases as dependency increases. Scikit-learn exposes `mutual_info_classif` for feature selection. ([Scikit-learn][7])

This can answer:

> Which filename words tell me the most about the category?

That is almost the statistical formulation of your original question.

---

## 23. NMF: one of the better non-LLM topic-discovery methods for this task

Non-negative Matrix Factorization can factor a file-term matrix:

$$
X\approx WH
$$

where:

```text
X = filename × term matrix
W = filename × latent category
H = category × term matrix
```

Suppose NMF discovers:

```text
TOPIC 0
factory
rust
pipe
industrial
machine

TOPIC 1
forest
tree
moss
pine
rock

TOPIC 2
female
soldier
armor
sniper
uniform
```

That can be surprisingly effective.

The standard NMF objective minimizes reconstruction error between \(X\) and \(WH\), commonly via the Frobenius norm, with optional regularization. ([Scikit-learn][8])

Python:

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF


vectorizer = TfidfVectorizer(
    ngram_range=(1, 2),
    min_df=3,
    max_df=0.80,
)

X = vectorizer.fit_transform(filenames)

model = NMF(
    n_components=20,
    init="nndsvda",
    random_state=42,
    max_iter=500,
)

W = model.fit_transform(X)
H = model.components_

terms = vectorizer.get_feature_names_out()

for topic_id, topic in enumerate(H):
    best = topic.argsort()[::-1][:10]

    print(
        topic_id,
        [terms[i] for i in best],
    )
```

For this problem, I would test **NMF before LDA**.

---

## 24. Why I would not lead with LDA

Latent Dirichlet Allocation is elegant, but filenames are extremely short documents.

LDA assumes:

```text
document
    ↓
mixture of topics
    ↓
mixture produces words
```

That is much easier to infer from a 1,000-word article than from:

```text
female_sniper_desert.png
```

Scikit-learn provides both batch and online variational LDA, including incremental mini-batch learning for large corpora. ([Scikit-learn][9])

But I would treat it as an experiment rather than your primary method.

NMF, graph communities, and sparse clustering are better aligned with the sparse filename domain.

---

## 25. K-means / spherical K-means

Once every filename is represented by a TF-IDF vector:

$$
x_i\in\mathbb R^d
$$

K-means seeks:

$$
\arg\min
\sum_i
\left\|
x_i-\mu_{c_i}
\right\|^2
$$

With normalized TF-IDF vectors, Euclidean distance becomes closely related to cosine similarity.

For very large corpora, use `MiniBatchKMeans`.

Scikit-learn's implementation supports mini-batch training and `partial_fit`, so new batches can update the clustering without retraining from scratch. ([Scikit-learn][10])

```python
from sklearn.cluster import MiniBatchKMeans

clusterer = MiniBatchKMeans(
    n_clusters=50,
    batch_size=4096,
    random_state=42,
    n_init="auto",
)

labels = clusterer.fit_predict(X)
```

Use it when you know roughly how many clusters you want.

---

## 26. HDBSCAN

If you do **not** know how many categories exist, HDBSCAN is worth testing.

Unlike K-means, it can create:

```text
cluster
cluster
cluster
noise
noise
cluster
```

rather than forcing every filename into something.

That matters tremendously for filesystem organization.

Scikit-learn includes HDBSCAN, with `min_cluster_size` controlling the smallest retained cluster; smaller structures may be marked as noise. ([Scikit-learn][11])

Conceptually:

```python
from sklearn.cluster import HDBSCAN

clusterer = HDBSCAN(
    min_cluster_size=15,
    min_samples=5,
)

labels = clusterer.fit_predict(X_reduced)
```

I would generally reduce sparse TF-IDF first:

```text
TF-IDF
  ↓
TruncatedSVD
  ↓
L2 normalize
  ↓
HDBSCAN
```

---

## 27. Agglomerative clustering

Agglomerative clustering starts with individual files and recursively merges them.

That gives you a natural hierarchy:

```text
ART
├─ CHARACTER
│  ├─ SOLDIER
│  │  ├─ FEMALE
│  │  └─ MALE
│  └─ CIVILIAN
│
├─ ENVIRONMENT
│  ├─ FACTORY
│  └─ FOREST
│
└─ PROPS
   ├─ WEAPONS
   └─ MACHINERY
```

This is useful if the desired output is a **directory tree**, because your output is inherently hierarchical.

It is less attractive for millions of items unless used on summaries, centroids, or samples.

---

## 28. Co-occurrence graph clustering may be better than file clustering

This is a key architectural point.

You can cluster:

```text
FILES
```

or cluster:

```text
WORDS
```

For your case I prefer discovering **word communities first**.

Why?

Your own premise is:

> there’s an absolute ton of repeated words that can be identified as a category.

So model the repeated words directly.

Then use those categories to classify files.

That gives you explainability:

```text
CATEGORY: factory

anchors:
    factory        1.00
    industrial     0.91
    pipe           0.87
    machinery      0.81
    rust           0.74

reason this file matched:
    factory
    pipe
    rust
```

That is dramatically easier to debug than:

```text
cluster 37
```

---

## 29. Near-duplicate filenames: Jaccard

For token sets \(A\) and \(B\):

$$
J(A,B)
=
\frac{|A\cap B|}
{|A\cup B|}
$$

Example:

```text
female soldier sniper desert
female soldier sniper snow
```

Intersection:

```text
female
soldier
sniper
```

Union:

```text
female
soldier
sniper
desert
snow
```

Therefore:

$$
J=3/5=0.6
$$

Python:

```python
def jaccard(a, b):
    a = set(a)
    b = set(b)

    if not a and not b:
        return 1.0

    return len(a & b) / len(a | b)
```

---

## 30. MinHash + LSH for huge directories

Exact pairwise comparison of \(N\) filenames requires approximately:

$$
O(N^2)
$$

comparisons.

At:

```text
1,000,000 files
```

that is impossible to brute force.

MinHash approximates Jaccard similarity.

Locality-Sensitive Hashing then indexes the sketches so similar sets can be found with sublinear query cost instead of comparing against every file. The current `datasketch` documentation explicitly describes MinHash LSH for this use case and notes that the results are approximate. ([Ekzhu][12])

Typical Python:

```python
from datasketch import MinHash, MinHashLSH


def make_minhash(tokens, num_perm=128):
    m = MinHash(
        num_perm=num_perm,
        seed=42,
    )

    for token in sorted(set(tokens)):
        m.update(token.encode("utf-8"))

    return m


index = MinHashLSH(
    threshold=0.75,
    num_perm=128,
)

for file_id, tokens in items:
    index.insert(
        file_id,
        make_minhash(tokens),
    )
```

LSH's retrieval probability follows an S-curve based on banding:

$$
P(s)
=
1-(1-s^r)^b
$$

where:

```text
s = similarity
r = rows per band
b = number of bands
```

This makes MinHash/LSH excellent for:

```text
near duplicate names
renamed copies
variants
export copies
almost identical asset series
```

but not for discovering broad semantic categories.

---

## 31. Edit distance / fuzzy matching

Fuzzy matching should be used **after** statistical category discovery, not as the foundation.

Useful examples:

```text
indstrial   → industrial
factroy     → factory
solider     → soldier
cyperpunk   → cyberpunk
```

Levenshtein distance recursively measures insertions, deletions, and substitutions.

RapidFuzz provides practical ratios, partial ratios, token-set comparison, token-sort comparison, and score cutoffs. ([RapidFuzz][13])

```python
from rapidfuzz import process, fuzz

known_terms = [
    "factory",
    "industrial",
    "soldier",
    "forest",
]

result = process.extractOne(
    "factroy",
    known_terms,
    scorer=fuzz.ratio,
    score_cutoff=85,
)

print(result)
```

Do not globally fuzz every word against every word.

First block by:

```text
first character
length
character trigrams
phonetic hash
```

and fuzzy-match only plausible candidates.

---

## 32. If you eventually have labels: TF-IDF + Linear SVM

Once you have manually confirmed categories such as:

```text
FACTORY
FOREST
CHARACTER
WEAPON
VEHICLE
ARCHITECTURE
```

you can stop clustering every new file.

Now it becomes supervised classification.

For sparse title/text data, a very strong classical baseline remains:

```text
word TF-IDF
+
character TF-IDF
+
linear SVM
```

No LLM.

No generative inference.

```python
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC


word = TfidfVectorizer(
    ngram_range=(1, 2),
    min_df=2,
    max_df=0.95,
    sublinear_tf=True,
)

chars = TfidfVectorizer(
    analyzer="char_wb",
    ngram_range=(3, 5),
    min_df=2,
    sublinear_tf=True,
)

model = Pipeline([
    (
        "features",
        FeatureUnion([
            ("word", word),
            ("char", chars),
        ]),
    ),
    (
        "classifier",
        LinearSVC(
            C=1.0,
            class_weight="balanced",
        ),
    ),
])

model.fit(
    training_filenames,
    training_categories,
)
```

The vectorization is sparse and practical even with very large vocabularies. Scikit-learn directly supports these word/character analyzers. ([Scikit-learn][2])

This would probably become your production classifier **after** initial unsupervised category discovery.

---

## 33. If by “names” you literally mean people, places, products, etc

That is a different subproblem: **Named Entity Recognition**.

For example:

```text
John_Smith_Vancouver_Canon_EOS_R5.png
```

might produce:

```text
John Smith       PERSON
Vancouver        LOCATION
Canon EOS R5     PRODUCT
```

Without an LLM, the appropriate classical architecture is:

```text
gazetteers
+
regex/shape features
+
CRF sequence model
```

A linear-chain Conditional Random Field models:

$$
P(\mathbf y|\mathbf x)
=
\frac{1}{Z(\mathbf x)}
\exp
\left[
\sum_t
\sum_k
\lambda_k
f_k(y_{t-1},y_t,\mathbf x,t)
\right]
$$

CRFs are classical structured-prediction models designed to combine many local features while modeling neighboring labels. ([arXiv][14])

Features might include:

```text
capitalized?
all uppercase?
contains digit?
contains hyphen?
known first name?
known city?
known camera model?
previous word?
next word?
```

This remains a legitimate non-LLM route.

Later non-LLM neural upgrades include character-CNN/BiLSTM-CRF models; classical NER research demonstrated those architectures well before contemporary LLMs. ([ACL Anthology][15])

But **I would not put this in version 1 of your sorter unless you actually need entity types**.

---

## 34. The end-to-end algorithm I would build for you

Here is the actual hierarchy I recommend:

1. **Inventory every filename but move nothing.** Generate stable file IDs and preserve original paths.
2. **Normalize filenames** into raw, parsed, and semantic representations.
3. **Extract unigrams, bigrams, and trigrams.**
4. **Compute local document frequency.**
5. Discard obvious metadata/noise and extremely rare terms.
6. **Calculate NPMI for co-occurring terms.**
7. Build the **term association graph**.
8. Use deterministic graph community detection.
9. Name communities from weighted central/category-specific terms.
10. Represent each category as a weighted vector.
11. Score each filename against those categories.
12. Allow multiple labels and an explicit `UNKNOWN`.
13. Run optional NMF/K-means/HDBSCAN as an independent discovery audit.
14. After category review, train TF-IDF + LinearSVC for faster/stabler future classification.
15. Produce a dry-run move plan.
16. Apply filesystem changes through a separately journaled transaction.

That is the architecture I would choose over LLMs for your use case.

---

## 35. Working Python prototype: corpus-driven category discovery

This is deliberately not an LLM and does not require training labels.

Dependencies:

```text
pip install networkx
```

Code:

```python
from __future__ import annotations

import csv
import math
import os
import re
import unicodedata

from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path

import networkx as nx


# ============================================================
# CONFIG
# ============================================================

IMAGE_EXTENSIONS = {
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".bmp",
    ".gif",
    ".tif",
    ".tiff",
    ".heic",
}

NOISE = {
    "img",
    "image",
    "photo",
    "picture",
    "copy",
    "edited",
    "edit",
    "final",
    "export",
    "temp",
    "tmp",
}

CAMEL_1 = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
CAMEL_2 = re.compile(r"(?<=[A-Z])(?=[A-Z][a-z])")

DATE = re.compile(
    r"(?<!\d)(?:19|20)\d{2}[-_.]?"
    r"(?:0?[1-9]|1[0-2])[-_.]?"
    r"(?:0?[1-9]|[12]\d|3[01])(?!\d)"
)

RESOLUTION = re.compile(
    r"(?i)(?<!\d)\d{3,5}x\d{3,5}(?!\d)"
)

VERSION = re.compile(
    r"(?i)\bv\d{1,4}\b"
)

NUMBER = re.compile(
    r"^\d+$"
)


# ============================================================
# DATA
# ============================================================

@dataclass(frozen=True)
class FileRecord:
    path: Path
    filename: str
    raw_stem: str
    tokens: tuple[str, ...]
    terms: frozenset[str]


@dataclass(frozen=True)
class Category:
    category_id: int
    name: str
    aliases: tuple[str, ...]
    terms: frozenset[str]


# ============================================================
# FILESYSTEM
# ============================================================

def iter_files(root: Path):
    """
    Recursive streaming traversal.

    Symbolic-link/reparse recursion is deliberately avoided.
    """

    stack = [root]

    while stack:
        directory = stack.pop()

        try:
            with os.scandir(directory) as it:
                entries = sorted(
                    it,
                    key=lambda e: e.name.casefold(),
                )

                for entry in entries:
                    try:
                        if entry.is_dir(
                            follow_symlinks=False
                        ):
                            stack.append(
                                Path(entry.path)
                            )

                        elif entry.is_file(
                            follow_symlinks=False
                        ):
                            path = Path(entry.path)

                            if (
                                path.suffix.casefold()
                                in IMAGE_EXTENSIONS
                            ):
                                yield path

                    except OSError:
                        continue

        except OSError:
            continue


# ============================================================
# TOKENIZATION
# ============================================================

def tokenize(stem: str) -> list[str]:
    raw = unicodedata.normalize(
        "NFKC",
        stem,
    )

    raw = CAMEL_2.sub(" ", raw)
    raw = CAMEL_1.sub(" ", raw)

    raw = DATE.sub(" ", raw)
    raw = RESOLUTION.sub(" ", raw)
    raw = VERSION.sub(" ", raw)

    raw = re.sub(
        r"[_\-.+@()\[\]{}]+",
        " ",
        raw,
    )

    tokens = []

    for token in raw.split():
        token = token.casefold().strip()

        if len(token) < 2:
            continue

        if token in NOISE:
            continue

        if NUMBER.match(token):
            continue

        tokens.append(token)

    return tokens


def make_terms(
    tokens: list[str],
    max_ngram: int = 2,
) -> set[str]:

    terms = set(tokens)

    for n in range(2, max_ngram + 1):
        for i in range(
            len(tokens) - n + 1
        ):
            terms.add(
                " ".join(
                    tokens[i:i+n]
                )
            )

    return terms


def build_record(path: Path) -> FileRecord:
    stem = path.stem

    tokens = tokenize(stem)

    return FileRecord(
        path=path,
        filename=path.name,
        raw_stem=stem,
        tokens=tuple(tokens),
        terms=frozenset(
            make_terms(tokens)
        ),
    )


# ============================================================
# CORPUS STATISTICS
# ============================================================

def statistics(
    records: list[FileRecord],
):
    df = Counter()
    pair_df = Counter()

    for record in records:
        terms = sorted(record.terms)

        df.update(terms)

        for a, b in combinations(
            terms,
            2,
        ):
            pair_df[(a, b)] += 1

    return df, pair_df


def idf(
    term: str,
    n_docs: int,
    df: Counter,
):
    return (
        math.log(
            (1 + n_docs)
            /
            (1 + df[term])
        )
        + 1
    )


def npmi(
    a: str,
    b: str,
    n_docs: int,
    df: Counter,
    pair_df: Counter,
):
    a, b = sorted((a, b))

    joint = pair_df.get(
        (a, b),
        0,
    )

    if joint == 0:
        return -1.0

    px = df[a] / n_docs
    py = df[b] / n_docs
    pxy = joint / n_docs

    pmi = math.log(
        pxy / (px * py)
    )

    return (
        pmi
        /
        -math.log(pxy)
    )


# ============================================================
# GRAPH DISCOVERY
# ============================================================

def build_term_graph(
    records,
    df,
    pair_df,
    *,
    min_df=3,
    max_df_ratio=0.80,
    min_pair_df=2,
    min_npmi=0.20,
):
    n_docs = len(records)

    max_df = max(
        1,
        int(
            n_docs
            * max_df_ratio
        ),
    )

    valid = sorted(
        term
        for term, count
        in df.items()
        if (
            count >= min_df
            and
            count <= max_df
        )
    )

    valid_set = set(valid)

    G = nx.Graph()

    for term in valid:
        G.add_node(
            term,
            df=df[term],
        )

    for (a, b), pair_count in sorted(
        pair_df.items()
    ):
        if (
            a not in valid_set
            or
            b not in valid_set
        ):
            continue

        if pair_count < min_pair_df:
            continue

        association = npmi(
            a,
            b,
            n_docs,
            df,
            pair_df,
        )

        if association < min_npmi:
            continue

        G.add_edge(
            a,
            b,
            weight=association,
            count=pair_count,
        )

    return G


# ============================================================
# CATEGORY NAMING
# ============================================================

def category_from_community(
    category_id,
    community,
    G,
    records,
    df,
):
    n_docs = len(records)

    terms = set(community)

    subgraph = G.subgraph(
        terms
    )

    centrality = (
        nx.degree_centrality(
            subgraph
        )
    )

    scores = {}

    for term in terms:
        scores[term] = (
            idf(
                term,
                n_docs,
                df,
            )
            *
            math.log1p(
                df[term]
            )
            *
            (
                0.25
                +
                centrality.get(
                    term,
                    0.0,
                )
            )
        )

    ordered = sorted(
        scores,
        key=lambda t: (
            -scores[t],
            t,
        ),
    )

    if not ordered:
        name = (
            f"category_"
            f"{category_id:03d}"
        )

        aliases = ()

    else:
        name = ordered[0]
        aliases = tuple(
            ordered[1:6]
        )

    return Category(
        category_id=category_id,
        name=name,
        aliases=aliases,
        terms=frozenset(terms),
    )


def discover_categories(
    G,
    records,
    df,
):
    communities = list(
        nx.community
        .greedy_modularity_communities(
            G,
            weight="weight",
            resolution=1.0,
        )
    )

    communities.sort(
        key=lambda c: (
            -len(c),
            sorted(c)[0],
        )
    )

    categories = []

    for i, community in enumerate(
        communities
    ):
        categories.append(
            category_from_community(
                i,
                community,
                G,
                records,
                df,
            )
        )

    return categories


# ============================================================
# FILE → CATEGORY
# ============================================================

def category_score(
    record,
    category,
    n_docs,
    df,
):
    overlap = (
        record.terms
        &
        category.terms
    )

    if not overlap:
        return 0.0

    numerator = sum(
        idf(
            term,
            n_docs,
            df,
        )
        for term in overlap
    )

    file_weight = sum(
        idf(
            term,
            n_docs,
            df,
        )
        for term in record.terms
        if term in df
    )

    if file_weight == 0:
        return 0.0

    return numerator / file_weight


def classify_record(
    record,
    categories,
    n_docs,
    df,
):
    scored = [
        (
            category,
            category_score(
                record,
                category,
                n_docs,
                df,
            ),
        )
        for category in categories
    ]

    scored.sort(
        key=lambda item: (
            -item[1],
            item[0].name,
        )
    )

    return scored


# ============================================================
# DRY-RUN
# ============================================================

def safe_folder_name(name):
    name = re.sub(
        r'[<>:"/\\|?*]',
        "_",
        name,
    )

    name = name.rstrip(
        " ."
    )

    reserved = {
        "con",
        "prn",
        "aux",
        "nul",
        *{
            f"com{i}"
            for i in range(1, 10)
        },
        *{
            f"lpt{i}"
            for i in range(1, 10)
        },
    }

    if name.casefold() in reserved:
        name = "_" + name

    return name or "_category"


def write_plan(
    records,
    categories,
    df,
    output_csv,
):
    n_docs = len(records)

    with open(
        output_csv,
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as f:

        writer = csv.writer(f)

        writer.writerow([
            "source",
            "category",
            "score",
            "second_score",
            "margin",
            "status",
            "suggested_folder",
        ])

        for record in records:
            ranked = classify_record(
                record,
                categories,
                n_docs,
                df,
            )

            top_category, top = (
                ranked[0]
                if ranked
                else (None, 0.0)
            )

            second = (
                ranked[1][1]
                if len(ranked) > 1
                else 0.0
            )

            margin = top - second

            if top_category is None:
                status = "UNKNOWN"
                folder = "_UNKNOWN"

            elif top < 0.25:
                status = "UNKNOWN"
                folder = "_UNKNOWN"

            elif margin < 0.05:
                status = "REVIEW"
                folder = "_REVIEW"

            else:
                status = "READY"

                folder = (
                    safe_folder_name(
                        top_category.name
                    )
                )

            writer.writerow([
                str(record.path),
                (
                    top_category.name
                    if top_category
                    else ""
                ),
                f"{top:.6f}",
                f"{second:.6f}",
                f"{margin:.6f}",
                status,
                folder,
            ])


# ============================================================
# MAIN
# ============================================================

def main(root_string):
    root = Path(root_string)

    records = [
        build_record(path)
        for path
        in iter_files(root)
    ]

    print(
        f"Files: {len(records):,}"
    )

    df, pair_df = statistics(
        records
    )

    G = build_term_graph(
        records,
        df,
        pair_df,
        min_df=3,
        max_df_ratio=0.80,
        min_pair_df=2,
        min_npmi=0.20,
    )

    categories = discover_categories(
        G,
        records,
        df,
    )

    print(
        f"Terms: {G.number_of_nodes():,}"
    )

    print(
        f"Associations: "
        f"{G.number_of_edges():,}"
    )

    print(
        f"Categories: "
        f"{len(categories):,}"
    )

    for category in categories:
        print()
        print(
            f"[{category.category_id:03d}] "
            f"{category.name}"
        )

        print(
            "    "
            +
            ", ".join(
                category.aliases
            )
        )

    write_plan(
        records,
        categories,
        df,
        root / "_sort_plan.csv",
    )

    print()
    print(
        "Dry-run written to "
        "_sort_plan.csv"
    )


if __name__ == "__main__":
    main(
        r"D:\YOUR\IMAGE\DIRECTORY"
    )
```

That is a genuine deterministic category-discovery prototype.

It does not move anything.

---

## 36. Windows filesystem engineering

For hundreds of thousands or millions of files, enumeration itself matters.

Python's `os.scandir()` exposes filesystem entries with cached metadata and, on Windows, is implemented using the Win32 directory-enumeration APIs. Python notes that calls such as `entry.is_file()` can often avoid an additional system call. ([Python documentation][16])

So prefer:

```python
os.scandir()
```

over repeatedly constructing large `Path` lists and then separately calling `stat()` everywhere.

For .NET/C#, Microsoft's `Directory.EnumerateFiles()` is also preferable to eager enumeration when streaming huge directories.

---

## 37. Reparse points, symlinks and junctions

Do not blindly recurse through everything.

On Windows, a directory tree can contain:

```text
symbolic links
junctions
mount points
other reparse points
```

Following them can create:

```text
duplicate indexing
loops
cross-volume traversal
unexpected enormous scans
```

The prototype deliberately uses:

```python
entry.is_dir(
    follow_symlinks=False
)
```

For a serious Windows-native implementation, I would additionally store:

```text
volume identity
file ID
reparse attributes
```

where required.

---

## 38. Windows filename constraints when creating category directories

Generated category names must be sanitized.

Windows disallows:

```text
< > : " / \ | ? *
```

in normal filenames and reserves device names including:

```text
CON
PRN
AUX
NUL
COM1 ... COM9
LPT1 ... LPT9
```

Names also should not end in spaces or periods. ([Microsoft Learn][1])

Do not assume case distinguishes folders:

```text
Factory
factory
FACTORY
```

should normally be treated as equivalent on Windows. ([Microsoft Learn][1])

---

## 39. Long paths

Traditional Win32 behavior uses the historical:

$$
MAX\_PATH=260
$$

limit, although modern Windows can support longer paths when the application and system configuration allow them. Microsoft documents long-path opt-in behavior for Windows 10 version 1607 and later. ([Microsoft Learn][17])

Your sorter should therefore calculate:

```text
source path length
destination path length
```

before any move.

Do not discover a path-length problem after 40,000 files have already moved.

---

## 40. Collision handling

Never do this:

```python
shutil.move(
    source,
    destination,
)
```

without a collision policy.

Suppose:

```text
A\factory_wall.png
B\factory_wall.png
```

both become:

```text
FACTORY\factory_wall.png
```

You need a deterministic policy such as:

```text
factory_wall.png
factory_wall__0002.png
```

or content hashes:

```text
factory_wall__8f2a7c.png
```

Prefer preserving original names and solving only actual collisions.

---

## 41. Detect exact duplicates separately

Filename similarity does not detect binary duplicates.

For exact duplicate files, use content hashes.

For example:

```python
import hashlib


def sha256_file(path):
    h = hashlib.sha256()

    with open(path, "rb") as f:
        for chunk in iter(
            lambda: f.read(
                1024 * 1024
            ),
            b"",
        ):
            h.update(chunk)

    return h.hexdigest()
```

Do this selectively if disk I/O is significant.

A staged approach is faster:

```text
file size
→ partial hash
→ full hash only for candidates
```

---

## 42. Safe filesystem transaction design

The classifier should never directly mutate the corpus.

Use:

```text
ANALYZE
   ↓
PLAN
   ↓
REVIEW
   ↓
PREPARED JOURNAL
   ↓
MOVE
   ↓
VERIFY
   ↓
COMMITTED
```

A move table should contain:

```text
operation_id
source
destination
source_size
source_mtime
classification
classification_score
status
timestamp
error
```

Then rollback can simply execute:

```text
destination → source
```

in reverse order.

---

## 43. Incremental updates

Suppose you classify 500,000 files today and add 1,000 next week.

Do not blindly rediscover everything every run.

Persist corpus statistics:

```text
N
df(term)
pair_df(a,b)
category membership
category anchors
model version
```

For a new file:

```text
increment N
increment df
increment co-occurrence
score against existing categories
```

Then periodically perform a **rebuild** when the corpus has materially changed.

For example:

```text
incremental classification every import

full category rediscovery when:
    +10% corpus size
    OR
    vocabulary drift exceeds threshold
    OR
    manual request
```

This keeps category names stable.

---

## 44. Category identity must be independent of display name

This matters.

Suppose your category initially becomes:

```text
factory
```

Later the term weights change and `industrial` narrowly overtakes it.

Do not suddenly change the identity of the category.

Store:

```text
category_id:
    7f43a2...

display_name:
    factory

aliases:
    industrial
    machinery
    pipe
```

The stable ID can be derived from persistent anchor terms:

$$
ID
=
Hash(
sorted(top\_stable\_anchors)
)
$$

This prevents incremental runs from destroying folder stability.

---

## 45. Stability scoring

You can even measure how stable a category is between two runs.

If old category term set is \(A\) and new category term set is \(B\):

$$
J(A,B)
=
\frac{|A\cap B|}
{|A\cup B|}
$$

Then:

```text
0.95    nearly identical
0.80    stable
0.55    drifting
0.20    likely new/different category
```

Use maximum Jaccard matching to map newly discovered categories onto existing category IDs.

This solves a major weakness of unsupervised clustering systems.

---

## 46. Very large corpus architecture

For:

```text
< 100,000 files
```

Python + SQLite + scikit-learn + NetworkX is sufficient.

For roughly:

```text
100,000 – 2,000,000
```

I would use:

```text
Python
SQLite or DuckDB
SciPy sparse matrices
scikit-learn
batch processing
possibly igraph instead of NetworkX for huge graphs
```

For genuinely enormous collections, stop storing vocabulary dictionaries in conventional vectorizers.

Scikit-learn provides `HashingVectorizer`, which is stateless and therefore does not need to learn/store a vocabulary. ([Scikit-learn][18])

That enables streaming:

```text
filename batch
→ hashed sparse representation
→ incremental classifier/clustering
```

---

## 47. Useful complexity estimates

| Technique                 |                          Approximate cost | Role                   |
| ------------------------- | ----------------------------------------: | ---------------------- |
| Tokenization              |                                 \(O(NL)\) | Mandatory              |
| Document frequency        |                                  \(O(T)\) | Mandatory              |
| TF-IDF                    |                           \(O(T)\) sparse | Mandatory/useful       |
| All-pairs file similarity |                                \(O(N^2)\) | Avoid                  |
| Pair co-occurrence        | Depends on terms/file; usually manageable | Category discovery     |
| Greedy modularity         |                  Depends on graph density | Vocabulary communities |
| Linear SVM                |   Roughly scales with sparse observations | Supervised production  |
| MiniBatchKMeans           |            Approx. \(O(NKI)\) but batched | Large clustering       |
| HDBSCAN                   |                     Data/metric dependent | Unknown cluster count  |
| Agglomerative             |                  Expensive at large \(N\) | Small/sample hierarchy |
| MinHash LSH               |                Sublinear candidate search | Near duplicates        |
| Fuzzy matching            |                       Expensive if global | Alias correction       |

The most dangerous computational mistake is building a huge dense:

$$
N\times N
$$

similarity matrix.

Never do that for a million-file corpus.

---

## 48. What I would *not* use first

| Method                       | My use for your problem           |
| ---------------------------- | --------------------------------- |
| LLM categorization           | Avoid                             |
| Sentence transformers        | Avoid initially                   |
| BERT embeddings              | Avoid initially                   |
| Generic semantic search      | Unnecessary initially             |
| Word2Vec                     | Optional experiment               |
| LDA                          | Secondary experiment              |
| Random Forest over raw words | Poor first choice                 |
| Naive Bayes                  | Useful baseline                   |
| CRF                          | Only if actual entities matter    |
| TF-IDF + SVM                 | Excellent after labels exist      |
| NMF                          | Very useful                       |
| NPMI graph                   | **Excellent**                     |
| Community detection          | **Excellent**                     |
| char n-grams                 | **Excellent**                     |
| MinHash LSH                  | Excellent for duplicates/variants |

---

## 49. My preferred production system

If I were implementing this specifically around the behavior you described, the primary classifier would actually be:

$$
\boxed{
\text{Local Corpus}
\rightarrow
\text{N-grams}
\rightarrow
\text{DF/IDF}
\rightarrow
\text{NPMI}
\rightarrow
\text{Term Graph}
\rightarrow
\text{Community Detection}
}
$$

Then:

$$
\boxed{
\text{Category Anchors}
+
\text{TF-IDF}
\rightarrow
\text{File Assignment}
}
$$

Once you approve the discovered category structure:

$$
\boxed{
\text{Word TF-IDF}
+
\text{Character TF-IDF}
+
\text{LinearSVC}
}
$$

becomes the production classifier for future imports.

That gives you an interesting property:

**the system teaches itself the vocabulary structure of the directory once, but future classification becomes cheap and rigid.**

No LLM inconsistency.

No prompt drift.

No semantic hallucination.

No cloud dependency.

---

## 50. The strongest conceptual insight from the research

Your files already contain a weakly structured language.

Something like:

```text
female_sniper_forest_winter_concept
female_sniper_factory_uniform
male_soldier_factory_heavy_armor
factory_wall_rust
factory_pipe_rust
forest_tree_winter
forest_moss_rock
```

is not random text.

Repeated tokens implicitly define a **latent ontology**.

Mathematically:

```text
filename
    =
set of observations

repeated word
    =
latent feature

word co-occurrence
    =
relationship

dense relationship group
    =
candidate category

rare category-specific term
    =
discriminator

high-frequency cross-category term
    =
background vocabulary

filename/category overlap
    =
classification evidence
```

So the most natural modern solution is not really “AI naming files.”

It is:

> **infer the latent taxonomy encoded in the corpus's filename vocabulary.**

And classical information retrieval + information theory + graph clustering is exceptionally well suited to doing exactly that.

### Primary technical sources

Scikit-learn's current documentation provides the relevant sparse TF-IDF, character n-gram, NMF, HDBSCAN, MiniBatchKMeans, LDA, and hashing implementations. ([Scikit-learn][2]) NetworkX provides the modularity/community-detection machinery used by the vocabulary-graph design. ([NetworkX][3]) Microsoft documents the Windows naming, reserved-name, case and path constraints that the filesystem layer has to respect. ([Microsoft Learn][1]) MinHash/LSH is well supported for approximate Jaccard retrieval when the corpus is too large for pairwise near-duplicate comparisons. ([Ekzhu][12])

**For your exact stated use case, the NPMI vocabulary graph + deterministic community/category layer is the part I would prioritize first.** It uses precisely the repeated-word structure you already know exists instead of trying to replace that signal with a more opaque model.

[1]: https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-file "Naming Files, Paths, and Namespaces - Win32 apps | Microsoft Learn"
[2]: https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html "TfidfVectorizer — scikit-learn 1.9.1 documentation"
[3]: https://networkx.org/documentation/stable/reference/algorithms/community.html?utm_source=chatgpt.com "Communities — NetworkX 3.6.1 documentation"
[4]: https://networkx.org/documentation/networkx-3.4.1/reference/algorithms/generated/networkx.algorithms.community.quality.modularity.html?utm_source=chatgpt.com "modularity — NetworkX 3.4.1 documentation"
[5]: https://networkx.org/documentation/networkx-2.7/reference/algorithms/generated/networkx.algorithms.community.modularity_max.greedy_modularity_communities.html?utm_source=chatgpt.com "greedy_modularity_communities — NetworkX 2.7 documentation"
[6]: https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.chi2.html "chi2 — scikit-learn 1.9.1 documentation"
[7]: https://scikit-learn.org/stable/modules/generated/sklearn.feature_selection.mutual_info_classif.html "mutual_info_classif — scikit-learn 1.9.1 documentation"
[8]: https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.NMF.html "NMF — scikit-learn 1.9.1 documentation"
[9]: https://scikit-learn.org/stable/modules/generated/sklearn.decomposition.LatentDirichletAllocation.html "LatentDirichletAllocation — scikit-learn 1.9.1 documentation"
[10]: https://scikit-learn.org/stable/modules/generated/sklearn.cluster.MiniBatchKMeans.html "MiniBatchKMeans — scikit-learn 1.9.1 documentation"
[11]: https://scikit-learn.org/stable/modules/generated/sklearn.cluster.HDBSCAN.html "HDBSCAN — scikit-learn 1.9.1 documentation"
[12]: https://ekzhu.com/datasketch/lsh.html?utm_source=chatgpt.com "MinHash LSH — datasketch 2.0.0 documentation"
[13]: https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html?utm_source=chatgpt.com "rapidfuzz.fuzz - RapidFuzz 3.14.6 documentation"
[14]: https://arxiv.org/abs/1011.4088 "[1011.4088] An Introduction to Conditional Random Fields"
[15]: https://aclanthology.org/N16-1030/ "Neural Architectures for Named Entity Recognition - ACL Anthology"
[16]: https://docs.python.org/3/library/os.html "os — Miscellaneous operating system interfaces — Python 3.14.7 documentation"
[17]: https://learn.microsoft.com/windows/win32/fileio/maximum-file-path-limitation?utm_source=chatgpt.com "Maximum Path Length Limitation - Win32 apps | Microsoft Learn"
[18]: https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.HashingVectorizer.html "HashingVectorizer — scikit-learn 1.9.1 documentation"
