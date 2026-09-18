"""Check fresh distributions and saved-rule commands in an isolated install target."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DIST = ROOT / ".tmp/category-rules/dist"
INSTALLED = ROOT / "typing/.cache/category-rules/installed"


def main():
    sources = {p.relative_to(ROOT / "src").as_posix(): p.read_bytes()
               for p in (ROOT / "src/riposte").rglob("*") if p.is_file() and "__pycache__" not in p.parts}
    with ZipFile(DIST / "riposte_studio-0.5.0-py3-none-any.whl") as wheel, tarfile.open(DIST / "riposte_studio-0.5.0.tar.gz") as sdist:
        assert {n for n in wheel.namelist() if n.startswith("riposte/")} == set(sources)
        for name, data in sources.items():
            assert wheel.read(name) == data, name
            assert sdist.extractfile("riposte_studio-0.5.0/src/" + name).read() == data, name
            assert (INSTALLED / name).read_bytes() == data, name
        for name in ("docs/DESIGN.md", "docs/UX-CONTRACT.md", "docs/CLI.md", "riposte.cmd"):
            assert sdist.extractfile("riposte_studio-0.5.0/" + name).read() == (ROOT / name).read_bytes(), name
    env = {**os.environ, "PYTHONPATH": str(INSTALLED)}
    with tempfile.TemporaryDirectory(prefix="installed-rules-", dir=ROOT / ".tmp/category-rules") as directory:
        workspace = Path(directory)
        for name in ("hockey.png", "toy-goalie.mp4", "goaltender.jpg", "other.png"):
            (workspace / name).write_bytes(b"Filename fixture; media decoding is not claimed.")
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in workspace.iterdir()}
        probe = subprocess.run([sys.executable, "-c", "import riposte; print(riposte.__file__)"],
                               cwd=workspace, env=env, capture_output=True, text=True, timeout=30)
        assert probe.returncode == 0 and Path(probe.stdout.strip()).is_relative_to(INSTALLED)
        base = [sys.executable, "-m", "riposte", "--json", "category-rules", str(workspace)]
        selection = ["--category", "Hockey=hockey;goalie;goaltender", "--exclude", "Hockey=toy", "--priority", "Hockey=10"]

        def invoke(args):
            run = subprocess.run([*base, *args], cwd=workspace, env=env, capture_output=True,
                                 text=True, encoding="utf-8", timeout=30)
            assert run.returncode == 0, run.stdout + run.stderr
            return json.loads(run.stdout)

        preview = invoke([*selection, "--review"])
        assert preview["status"] == "DRAFT" and preview["revision"] == "missing"
        assert preview["review"]["assignments"] == {"hockey": 2, "uncategorized": 2}
        assert not (workspace / ".riposte").exists()
        saved = invoke([*selection, "--save", "--expected-revision", "missing"])
        reloaded = invoke(["--review"])
        assert saved["rules"] == reloaded["rules"] and saved["revision"] == reloaded["revision"]
        assert before == {name: ((workspace / name).read_bytes(), (workspace / name).stat().st_mtime_ns) for name in before}
        assert {p.name for p in (workspace / ".riposte").iterdir()} == {"WORKSPACE", "category-rules.json"}
        wrapper = subprocess.run([str(ROOT / "riposte.cmd"), "--json", "category-rules", str(workspace), "--review"],
                                 cwd=workspace, capture_output=True, text=True, encoding="utf-8", timeout=30)
        assert wrapper.returncode == 0, wrapper.stdout + wrapper.stderr
        assert json.loads(wrapper.stdout) == reloaded
        report = {"result": "PASS", "scope": "Fresh distribution bytes, moved design docs, installed CLI preview/save/reload and actual Windows wrapper; synthetic filenames only",
                  "source_files": len(sources), "installed_origin": probe.stdout.strip(),
                  "saved_rules": saved["rules"], "match_counts": reloaded["review"]["assignments"],
                  "media_bytes_and_mtimes_unchanged": True}
        (HERE / "package.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print("PASS package bytes, moved documents, installed rule persistence and Windows wrapper")


if __name__ == "__main__":
    main()
