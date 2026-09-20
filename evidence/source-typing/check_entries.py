"""Exercise the Windows wrappers with a read-only version/menu invocation."""
from pathlib import Path
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent


def main():
    version = subprocess.run(["cmd.exe", "/d", "/c", str(ROOT / "riposte.cmd"), "--version"],
                             cwd=ROOT, capture_output=True, text=True, timeout=45)
    assert version.returncode == 0 and not version.stderr, version
    start = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File",
                            str(ROOT / "START.ps1"), "-NoAnimation", "-Linear"], cwd=ROOT,
                           input="q\n", capture_output=True, text=True, timeout=45)
    (HERE / "start-transcript.txt").write_text(start.stdout + start.stderr, encoding="utf-8")
    result = {"wrapper_version": version.stdout.strip(), "start_linear": {
        "exit_code": start.returncode, "main_menu": "RIPOSTE" in start.stdout and "Sort" in start.stdout,
        "explicit_q_exit": start.returncode == 0, "stderr_empty": not start.stderr}}
    assert result["wrapper_version"] == "RIPOSTE 0.5.0", result
    assert result["start_linear"] == dict(exit_code=0, main_menu=True, explicit_q_exit=True, stderr_empty=True), result
    (HERE / "entries.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
