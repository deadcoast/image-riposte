"""Enumerate extremal completions independently of the production bound formula."""
from fractions import Fraction
import hashlib
import itertools
import json
from pathlib import Path

from riposte.cohort import bounded_mean

ROOT = Path(__file__).resolve().parents[2]
grid = (Fraction(-1), Fraction(-1, 3), Fraction(0), Fraction(2, 3), Fraction(1), None)
states = completions = 0
for values in itertools.product(grid, repeat=3):
    summary = bounded_mean(values)
    possible = []
    for replacements in itertools.product((Fraction(-1), Fraction(1)), repeat=values.count(None)):
        replacement = iter(replacements)
        outcome = [next(replacement) if value is None else value for value in values]
        possible.append(sum(outcome, Fraction(0)) / 3)
        completions += 1
    bounds = summary['bounds']
    lower = Fraction(bounds['lower']['numerator'], bounds['lower']['denominator'])
    upper = Fraction(bounds['upper']['numerator'], bounds['upper']['denominator'])
    assert (lower, upper) == (min(possible), max(possible))
    assert upper - lower == Fraction(2 * values.count(None), 3)
    assert (summary['mean'] is None) == (None in values)
    states += 1
assert (states, completions) == (216, 343)
print(json.dumps({'result':'PASS','states':states,'extreme_completions':completions,
    'mathematics':'Sharp under boundedness only; finite selected sample; no independence assumption or confidence coverage claim.',
    'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
               for p in (ROOT/'src/riposte').rglob('*') if p.is_file() and '__pycache__' not in p.parts}},indent=2))
