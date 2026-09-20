"""Review only the duplicate-finder owners against the retained sorter snapshot."""
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('typing_check',ROOT/'typing/check.py')
check=importlib.util.module_from_spec(spec);spec.loader.exec_module(check)
before=json.loads((ROOT/'evidence/duplicates/source-before.json').read_text())
after=check.source_hashes()
changed={path for path in before.keys()|after.keys() if before.get(path)!=after.get(path)}
expected={f'src/riposte/{name}.py' for name in ('cli','duplicate_features','duplicate_index','duplicate_media','duplicate_review','duplicates','records','server')}
expected|={f'src/riposte/terminal/{name}.py' for name in ('actions','controller','interaction','output','render','reports','service','state')}
expected|={f'src/riposte/static/{name}' for name in ('app.js','duplicates.js','index.html','style.css')}
assert changed==expected,changed^expected
issues,signatures,modules=check.check_parity()
assert not issues,issues
check.REVIEWED_SOURCE.write_text(json.dumps(after,indent=2)+'\n')
print(json.dumps({'reviewed_owners':sorted(changed),'signatures':signatures,'leaf_modules':len(modules),'application_files':len(after)},indent=2))
