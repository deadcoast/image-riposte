"""Exact descriptive agreement for a fixed, fully crossed binary review panel.

Missing decisions stay in the planned denominator. Completion bounds are not
confidence intervals; pairwise kappa is not averaged into a panel verdict.
"""
from __future__ import annotations

from collections.abc import Sequence
from fractions import Fraction
from itertools import combinations
from math import comb


def _fraction(value: Fraction) -> dict[str, object]:
    return {"numerator": value.numerator, "denominator": value.denominator, "value": float(value)}


def _pair(rows: Sequence[Sequence[bool | None]], left: int, right: int) -> dict[str, object]:
    counts = dict.fromkeys(("yes_yes", "yes_no", "no_yes", "no_no", "missing"), 0)
    for row in rows:
        decision_left, decision_right = row[left], row[right]
        key = "missing" if decision_left is None or decision_right is None else f"{'yes' if decision_left else 'no'}_{'yes' if decision_right else 'no'}"
        counts[key] += 1
    result: dict[str, object] = {"reviewers": [left, right], "counts": counts,
        "status": "INCOMPLETE", "observed_agreement": None, "chance_agreement": None, "kappa": None}
    if counts["missing"]:
        return result
    a, b, c, d = (counts[key] for key in ("yes_yes", "yes_no", "no_yes", "no_no"))
    size = len(rows)
    observed = Fraction(a + d, size)
    chance = Fraction((a + b)*(a + c) + (c + d)*(b + d), size*size)
    result.update(observed_agreement=_fraction(observed), chance_agreement=_fraction(chance),
                  status="UNDEFINED_CONSTANT_MARGINALS" if chance == 1 else "DESCRIPTIVE",
                  kappa=_fraction((observed - chance)/(1 - chance)) if chance != 1 else None)
    return result


def binary_agreement(rows: Sequence[Sequence[bool | None]]) -> dict[str, object]:
    """Rows are fixed items; columns are fixed reviewers. No item deletion/imputation."""
    if not rows or len(rows[0]) < 2:
        raise ValueError("At least one item and two reviewers are required")
    reviewers = len(rows[0])
    if any(len(row) != reviewers or any(v is not None and type(v) is not bool for v in row) for row in rows):
        raise ValueError("A rectangular bool-or-null decision matrix is required")
    minimum = maximum = missing = known_pairs = known_agreements = 0
    disagreement_items: list[int] = []
    for index, row in enumerate(rows):
        yes = sum(v is True for v in row)
        no = sum(v is False for v in row)
        unknown = reviewers - yes - no
        missing += unknown
        known_pairs += comb(yes + no, 2)
        known_agreements += comb(yes, 2) + comb(no, 2)
        if yes and no:
            disagreement_items.append(index)
        # f(t)=C(t,2)+C(R-t,2); t is the final number of yes decisions.
        balanced = min(max(reviewers // 2, yes), yes + unknown)
        minimum += comb(balanced, 2) + comb(reviewers - balanced, 2)
        maximum += max(comb(yes, 2) + comb(reviewers - yes, 2),
                       comb(yes + unknown, 2) + comb(no, 2))
    denominator = len(rows)*comb(reviewers, 2)
    return {"items": len(rows), "reviewers": reviewers, "planned_pairs": denominator,
            "observed_pairs": known_pairs, "observed_agreements": known_agreements,
            "missing_decisions": missing, "disagreement_items": disagreement_items,
            "agreement": _fraction(Fraction(minimum, denominator)) if missing == 0 else None,
            "bounds": {"lower": _fraction(Fraction(minimum, denominator)),
                       "upper": _fraction(Fraction(maximum, denominator)),
                       "kind": "EXACT_FINITE_PANEL_COMPLETIONS_NOT_CONFIDENCE_INTERVAL"},
            "pairs": [_pair(rows, a, b) for a, b in combinations(range(reviewers), 2)]}
