"""Synthetic in-memory lexical scaling, not whole-folder or semantic accuracy."""
import json
from pathlib import Path
import time
import tracemalloc
from riposte.category_corpus import build_corpus


def word(number):
    result = ""
    while True:
        result = chr(97 + number % 26) + result
        number //= 26
        if not number: return "asset" + result


results = []
for size in (1_000, 10_000, 50_001):
    names = [f'{("forest_tree", "factory_pipe", "soldier_armor", "ocean_water")[i % 4]}_{word(i)}.png' for i in range(size)]
    tracemalloc.start()
    start = time.perf_counter()
    model = build_corpus(names)
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory(); tracemalloc.stop()
    assert model.status in {"READY", "LIMIT_REACHED"}
    results.append({"titles": size, "seconds": round(elapsed, 4), "peak_traced_bytes": peak,
                    "status": model.status, "families": model.families, "pairs": model.pairs,
                    "categories": len(model.categories)})
result = {"scope": "Synthetic in-memory titles; traced Python allocations; excludes image/video I/O and source verification.", "runs": results}
(Path(__file__).parent / "scaling.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
