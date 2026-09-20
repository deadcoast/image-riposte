"""Compare fresh build contents to reviewed application bytes; no install claim."""
import hashlib
import json
from pathlib import Path
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
sources = json.loads((ROOT / "typing/evidence/source-reviewed-sorter-menu.json").read_text())
dist = ROOT / ".tmp/sorter-menu/dist"
with zipfile.ZipFile(next(dist.glob("*.whl"))) as wheel, tarfile.open(next(dist.glob("*.tar.gz"))) as sdist:
    prefix = sdist.getnames()[0].split("/")[0]
    for name, digest in sources.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
        assert hashlib.sha256(wheel.read(name.removeprefix("src/"))).hexdigest() == digest, name
        assert hashlib.sha256(sdist.extractfile(prefix + "/" + name).read()).hexdigest() == digest, name
result = {"result": "PASS", "application_files": len(sources),
          "scope": "Source, fresh wheel and sdist have identical reviewed application bytes. Native launchers use the existing editable installation; no clean-install qualification."}
(Path(__file__).parent / "packages.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(result, indent=2))
