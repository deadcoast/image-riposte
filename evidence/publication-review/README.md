# Bounded publication review and exact report snapshots

Publication review now retains only item IDs, candidate hashes and report hashes
between selected outputs. Each verified item's decoded image pair and raw PNG
buffers are released before the next item. All selected items are still checked
before the first acceptance receipt is written.

The publication record reader now reads at most 8 MiB plus one byte, checks the
consumed byte count, and parses that snapshot. `_verified_item` hashes those same
bytes. It no longer reopens the report after validation to obtain its hash.

## Reproductions

[The original regression run](red.txt) recorded **5 failures and 8 passing
controls**:

- A six-item review retained all 12 decoded output images during every receipt
  write. After the repair, none remain at receipt writes and the test observes
  at most one returned clean/candidate pair during verification. This measures
  object retention, not process RSS or all temporary image-processing buffers.
- Replacing a report during quality verification produced a digest for different
  bytes than the parsed report. Review could then display the replacement as
  accepted. The repaired review binds the earlier verified bytes and reports
  the changed item as stale; later export refuses it.
- Export could reject a valid already-read approved snapshot because its second
  report read encountered a replacement. Export now uses its verified snapshot;
  the next operation observes the replacement and rejects the stale review.
- A file that grew after its initial size check bypassed the 8 MiB record limit.
  The repaired reader consumes at most 8,388,609 bytes and rejects an oversized
  record before parsing it.

The [13 regression cases](../../tests/test_publication_review_snapshots.py) use
actual date-only PNGs, storage, quality validation and ZIP export. They also
verify unchanged masters/candidates, exact exported bytes, revocation,
full-selection validation before writes, boundary lengths and invalid records.
These tests do not require Torch.

## Executed validation

| Check | Result |
|---|---|
| [Focused publication, repair and API suites](focused.txt) | 97 passed |
| [Full application suite](full-suite.txt) | 799 passed, 7 skipped |
| [External contracts](contracts.txt) | PASS; 320 signatures, stubtest, consumer and fixture checks |
| [Static inventory](inventory.txt) | PASS; 442 source symbols and 1,735 symbol dependencies |

The seven suite skips are three Windows symlink privilege cases and four POSIX
terminal host cases. Commands from the repository root:

```powershell
uv run --frozen --no-sync --cache-dir typing/.cache/uv python -m pytest tests/test_publication_review_snapshots.py tests/test_v03_publication.py tests/test_development_repairs.py tests/test_v03_api_cli.py -q --basetemp typing/.cache/publication-review/focused-final -o cache_dir=typing/.cache/publication-review/pytest-cache
uv run --frozen --no-sync --cache-dir typing/.cache/uv python -m pytest -q --basetemp typing/.cache/publication-review/full -o cache_dir=typing/.cache/publication-review/pytest-cache
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/check.py
uv run --project typing --frozen --cache-dir typing/.cache/uv python typing/pacer_inventory.py
```

The existing public signatures and receipt format remain compatible. The new
private `_read_record` helper is declared as returning a report and its bytes;
`_read` retains its mapping result. Only publication.py advances in the reviewed
source manifest after that contract review. The previous manifest is preserved
in [source-before.json](source-before.json).

Snapshot consistency applies to each verified item. The workspace lock prevents
conflicting application writes; this change does not introduce an atomic
filesystem snapshot or a transaction covering all receipt files.
