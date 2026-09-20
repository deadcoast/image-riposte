"""Native POSIX lease probe using only the existing Python standard library.

This does not qualify the full application on Linux or macOS.
"""
from pathlib import Path
import json
import os
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from riposte.locking import file_lease, file_identity
from riposte.errors import RiposteError


def child(path, hold):
    try:
        with file_lease(Path(path)):
            print("OWNED", flush=True)
            if hold:
                sys.stdin.readline()
    except RiposteError as exc:
        print(exc.code, flush=True)


def main():
    assert os.name == "posix"
    with tempfile.TemporaryDirectory(dir=ROOT / ".tmp/workspace-lease") as temporary:
        root = Path(temporary)
        path = root / "lease"
        with file_lease(path):
            try:
                with file_lease(path):
                    raise AssertionError("nested ownership")
            except RiposteError as exc:
                assert exc.code == "WORKSPACE_LOCKED"
            result = subprocess.run([sys.executable, __file__, "--once", str(path)],
                                    capture_output=True, text=True, timeout=10)
            assert result.returncode == 0 and result.stdout.strip() == "WORKSPACE_LOCKED"
        identity = file_identity(path)
        worker = subprocess.Popen([sys.executable, __file__, "--hold", str(path)],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            assert worker.stdout.readline().strip() == "OWNED"
            worker.kill()
            worker.communicate(timeout=10)
            with file_lease(path):
                assert file_identity(path) == identity
        finally:
            if worker.poll() is None:
                worker.kill()
                worker.communicate(timeout=10)
        # Production keeps the lease outside the renamed state directory,
        # including on WSL's Windows-backed mount, which rejects open descendants.
        folder = root / "old"
        folder.mkdir()
        with file_lease(path):
            folder.rename(root / "new")
            result = subprocess.run([sys.executable, __file__, "--once", str(path)],
                                    capture_output=True, text=True, timeout=10)
            assert result.returncode == 0 and result.stdout.strip() == "WORKSPACE_LOCKED"
        return {"result": "PASS", "python": sys.version, "platform": platform.platform(),
                "checks": ["nested owner blocked", "live subprocess blocked", "killed process released lease",
                           "persistent lease identity", "adjacent state rename retains ownership"],
                "scope": "Native POSIX file_lease only, on the existing Ubuntu WSL runtime and mounted checkout; not full Linux/macOS application qualification."}


if __name__ == "__main__":
    if len(sys.argv) == 3:
        child(sys.argv[2], sys.argv[1] == "--hold")
    else:
        print(json.dumps(main(), indent=2))
