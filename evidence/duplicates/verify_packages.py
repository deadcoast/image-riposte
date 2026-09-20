"""Compare reviewed application bytes with fresh wheel and sdist artifacts."""
import hashlib
import json
from pathlib import Path
import tarfile
import zipfile

ROOT=Path(__file__).resolve().parents[2]
sources=json.loads((ROOT/'typing/evidence/source-reviewed-duplicates.json').read_text())
dist=ROOT/'.tmp/duplicates/dist'
with zipfile.ZipFile(next(dist.glob('*.whl'))) as wheel,tarfile.open(next(dist.glob('*.tar.gz'))) as sdist:
    prefix=sdist.getnames()[0].split('/')[0]
    for name,digest in sources.items():
        assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,name
        assert hashlib.sha256(wheel.read(name.removeprefix('src/'))).hexdigest()==digest,name
        assert hashlib.sha256(sdist.extractfile(prefix+'/'+name).read()).hexdigest()==digest,name
    assert sdist.extractfile(prefix+'/README.md').read()==(ROOT/'README.md').read_bytes()
    assert sdist.extractfile(prefix+'/docs/DUPLICATES.md').read()==(ROOT/'docs/DUPLICATES.md').read_bytes()
result={'result':'PASS','application_files':len(sources),'readme_current':True,'duplicate_guide_current':True,
        'scope':'Current source and fresh wheel/sdist bytes; native execution uses the existing editable installation. Clean installation remains shelved.'}
(Path(__file__).parent/'packages.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
