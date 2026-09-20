"""Source-derived duplicate analysis contract; scores are evidence, not probabilities."""
from __future__ import annotations
from dataclasses import dataclass, field
Reference = tuple[int, int, int]

@dataclass
class Node:
    value: int
    references: list[Reference] = ...
    children: dict[int, int] = ...

class HashIndex:
    nodes: list[Node]

    def __init__(self) -> None:
        ...

    def add(self, value: int, reference: Reference) -> None:
        ...

    def query(self, value: int, radius: int=..., *, budget: int=..., limit: int=...) -> tuple[list[tuple[int, Reference]], bool, int]:
        ...
