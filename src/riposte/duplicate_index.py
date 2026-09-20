"""Bounded Hamming BK-tree. Exact groups are collapsed before visual retrieval."""
from __future__ import annotations

from dataclasses import dataclass, field

Reference = tuple[int, int, int]  # entity, frame, view


@dataclass
class Node:
    value: int
    references: list[Reference] = field(default_factory=list)
    children: dict[int, int] = field(default_factory=dict)


class HashIndex:
    def __init__(self) -> None:
        self.nodes: list[Node] = []

    def add(self, value: int, reference: Reference) -> None:
        if not self.nodes:
            self.nodes.append(Node(value, [reference]))
            return
        cursor = 0
        while True:
            node = self.nodes[cursor]
            distance = (value ^ node.value).bit_count()
            if distance == 0:
                node.references.append(reference)
                return
            child = node.children.get(distance)
            if child is None:
                node.children[distance] = len(self.nodes)
                self.nodes.append(Node(value, [reference]))
                return
            cursor = child

    def query(self, value: int, radius: int = 12, *, budget: int = 20_000,
              limit: int = 10_000) -> tuple[list[tuple[int, Reference]], bool, int]:
        pending = [0] if self.nodes else []
        results: list[tuple[int, Reference]] = []
        visited = 0
        while pending:
            if visited >= budget:
                return results, False, visited
            node = self.nodes[pending.pop()]
            visited += 1
            distance = (value ^ node.value).bit_count()
            if distance <= radius:
                for reference in node.references:
                    if len(results) >= limit:
                        return results, False, visited
                    results.append((distance, reference))
            pending.extend(node.children[d] for d in sorted(node.children, reverse=True)
                           if distance - radius <= d <= distance + radius)
        return results, True, visited
