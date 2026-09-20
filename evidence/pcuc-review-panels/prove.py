"""Independent enumeration checks the production arithmetic on all small panels."""
from fractions import Fraction
from itertools import combinations, product
from pathlib import Path
import hashlib, json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'src'))
from riposte.agreement import binary_agreement

def fraction(value):
    return Fraction(value['numerator'], value['denominator'])

states = completions = kappa_cases = 0
for count in range(2, 9):
    for row in product((False, True, None), repeat=count):
        result = binary_agreement([row])
        missing = [i for i,v in enumerate(row) if v is None]
        values = []
        for completion in product((False, True), repeat=len(missing)):
            filled = list(row)
            for i,v in zip(missing,completion):
                filled[i] = v
            pairs = list(combinations(filled,2))
            values.append(Fraction(sum(a == b for a,b in pairs),len(pairs)))
            completions += 1
        assert fraction(result['bounds']['lower']) == min(values)
        assert fraction(result['bounds']['upper']) == max(values)
        states += 1
multi_states = multi_completions = 0
for values in product((False, True, None), repeat=6):
    result = binary_agreement([values[:3],values[3:]])
    missing = [i for i,v in enumerate(values) if v is None]
    scores = []
    for completion in product((False, True), repeat=len(missing)):
        filled=list(values)
        for i,v in zip(missing,completion):
            filled[i]=v
        scores.append(Fraction(sum(a == b for row in (filled[:3],filled[3:]) for a,b in combinations(row,2)),6))
        multi_completions += 1
    assert fraction(result['bounds']['lower']) == min(scores)
    assert fraction(result['bounds']['upper']) == max(scores)
    multi_states += 1
for values in product((False,True), repeat=10):
    rows = list(zip(values[:5],values[5:]))
    pair = binary_agreement(rows)['pairs'][0]
    po = Fraction(sum(a == b for a,b in rows),5)
    # Independent enumeration of all cross-item coder decisions gives Pe.
    pe = Fraction(sum(a == b for a in values[:5] for b in values[5:]),25)
    assert fraction(pair['observed_agreement']) == po
    assert fraction(pair['chance_agreement']) == pe
    assert (pair['kappa'] is None) == (pe == 1)
    if pe != 1:
        assert fraction(pair['kappa']) == (po-pe)/(1-pe)
    kappa_cases += 1
sources = {p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
           for p in (ROOT/'src/riposte').rglob('*') if p.is_file() and '__pycache__' not in p.parts}
result = dict(result='PASS', states=states, completions=completions, multi_states=multi_states,
              multi_completions=multi_completions, kappa_cases=kappa_cases, sources=sources,
              scope='Exact small finite panels; no real-rater, population or efficacy qualification')
Path(__file__).with_name('proof.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k != 'sources'},indent=2))
