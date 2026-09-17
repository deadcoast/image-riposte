# Production optimizer search repair

`src/riposte/release_guard.py` now considers every accepted iterate for output,
independently of trace checkpoint cadence. It checks the exact quantized pixels
before committing an update and retries quality failures with a smaller step,
at most eight reductions down to 0.05/255. A rejected update preserves the
previous iterate. Random starts remain ineligible. Selection still maximizes
the worst context first and the mean context second under the existing quality
limits. Reports record the selected step and reduction count.

## Reproduced improvement

The before/after comparison executes the reviewed previous implementation and
the current implementation with actual CPU Torch gradients, all nine image
codec/mask contexts, and the real numerical quality checks. Encoders are the
deterministic synthetic functions defined in `tests/test_release_search.py`.

| Reproduction | Before | After |
|---|---|---|
| Four steps, checkpoint cadence 4, nonlinear encoder | Selected worst-context score 0.00634881 | 0.01658705; same pixels and scores as cadence 1 |
| One step requested at 8/255, quadratic encoder | No eligible candidate; publishing blocked | One reduction to 4/255; quality passes; publishing ready for review |
| Recovered publication | No candidate | Saved pixels equal direct engine output; reviewed ZIP contains the exact candidate bytes; source master unchanged |

Exact settings, scores, quality reports and hashes are in
[comparison.json](comparison.json). The earlier source manifest is retained in
[source-before.json](source-before.json). Initial failing regressions are in
[red.txt](red.txt); later test corrections read the committed report rather than
the public status projection, use the existing quality-limit field names, and
read the date from the audited PNG.

## Validation

- Seven new regressions cover cadence independence, quality recovery, pixel
  caps, determinism and global RNG isolation, cancellation, bounded exhausted
  retries, and publication through review and ZIP export.
- [Focused engine and publication suite](focused.txt): **77 passed**.
- [Full application suite](full-suite.txt): **768 passed, 7 skipped**. Skips are
  three Windows symlink privilege cases and four POSIX terminal host cases.
- [External contracts](contracts.txt): **PASS**, including 318 signature
  matches, stubtest, consumer checks and contract/tooling fixtures.
- [Static source inventory](inventory.txt): **PASS**.

Commands, from the project root:

```powershell
uv run --frozen --no-sync --cache-dir typing/.cache/uv python -m pytest tests/test_release_search.py tests/test_v03_quality_guard.py tests/test_v03_publication.py -q --basetemp typing/.cache/release-search/focused3 -o cache_dir=typing/.cache/release-search/pytest-cache
uv run --frozen --no-sync --cache-dir typing/.cache/uv python -m pytest -q --basetemp typing/.cache/release-search/full -o cache_dir=typing/.cache/release-search/pytest-cache
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/pacer_inventory.py
```

The affected external declaration, `typing/stubs/riposte/release_guard.pyi`, was
reviewed: configuration fields, function arguments, return tuple and callback
contract remain compatible. Report additions fit the existing dynamic `Report`
contract. Only this reviewed application's source hash was advanced in
`typing/evidence/source-reviewed-repairs.json`; the prior manifest is preserved
here. Earlier acceptance artifacts retain their original source bindings and
are historical when those bindings differ from this authorized development.
