# Source-derived private search contracts.
from pathlib import Path
from typing import Literal, TypedDict, cast
from .records import CatalogRow, Progress

class SearchRow(CatalogRow):
    original_filename: str | None
    category: str | None
    provenance: Literal['MATCHED', 'MISSING', 'MISMATCHED', 'INVALID']
    title_state: Literal['KNOWN', 'UNKNOWN']

class SearchReport(TypedDict):
    mode: Literal['PRIVATE_LIBRARY_SEARCH']
    rows: list[SearchRow]
    total: int
    limit: int
    offset: int
    next_offset: int | None
    revision: str
    basis: str

def normalized(value: str) -> str:
    ...

def search_library(root: Path, *, search: str='', category: str='', title_state: str='all', year: str | None=None, month: str | int | None=None, size: str | None=None, limit: int=50, offset: int=0, expected_revision: str | None=None, progress: Progress | None=None) -> SearchReport:
    ...
