"""Real-process crash recovery and exclusion; synthetic artwork only."""
from riposte.organizer import plan as _sort_preview
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from riposte import organizer
from riposte.errors import RiposteError
from riposte.locking import LEASE_NAME, file_identity
from riposte.policy import Policy
from riposte.store import catalog, state_dir, workspace_lock

POLICY = Policy(date_mode="modified")
CHILD = """
import os,sys,time
from pathlib import Path
from riposte import organizer
from riposte.policy import Policy
from riposte.sort_history import SortHistory
from riposte.store import workspace_lock
root,ready=map(Path,sys.argv[1:3])
stage,ending=sys.argv[3:5]
def interrupt():
    ready.write_text('ready')
    if ending=='exit':os._exit(23)
    time.sleep(60)
if stage=='hold':
    with workspace_lock(root):interrupt()
elif stage=='undo':
    import riposte.sort_history as history
    original=history.copy_exclusive
    def copied(*args,**kwargs):
        original(*args,**kwargs)
        interrupt()
    history.copy_exclusive=copied
    organizer.undo_sort(root,apply=True)
else:
    method='prepare' if stage=='prepare' else 'remove_source'
    original=getattr(SortHistory,method)
    def stopped(self,*args,**kwargs):
        original(self,*args,**kwargs)
        interrupt()
    setattr(SortHistory,method,stopped)
    organizer.organize(root,Policy(date_mode='modified'),plan_id=organizer.plan(root,Policy(date_mode='modified'))['plan_id'])
"""


def start_child(root, tmp_path, stage, ending="hold"):
    ready = tmp_path / f"ready-{stage}"
    child = subprocess.Popen([sys.executable, "-c", CHILD, str(root), str(ready), stage, ending],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.monotonic() + 15
    while not ready.exists() and time.monotonic() < deadline and child.poll() is None:
        time.sleep(.01)
    if not ready.exists():
        child.kill()
        output = child.communicate(timeout=10)
        pytest.fail(f"Child failed to reach {stage}: {output}")
    return child


@pytest.mark.parametrize("stage", ["prepare", "remove", "undo"])
@pytest.mark.parametrize("ending", ["exit", "terminate"])
def test_killed_sort_or_undo_restores_exact_original(root, tmp_path, make_image, stage, ending):
    source = make_image(root / "originals/private-name.png")
    original, modified = source.read_bytes(), source.stat().st_mtime_ns
    if stage == "undo":
        organizer.organize(root, POLICY, plan_id=_sort_preview(root, POLICY)["plan_id"])
    child = start_child(root, tmp_path, stage, ending)
    try:
        if ending == "terminate":
            child.kill()
        child.communicate(timeout=10)
        assert child.returncode != 0
        preview = organizer.undo_sort(root)
        assert preview["ready"]
        result = organizer.undo_sort(root, apply=True, sort_id=preview["sort_id"])
        assert result["checkpoint"] == "COMPLETE"
        assert source.read_bytes() == original and source.stat().st_mtime_ns == modified
        assert not catalog(root)
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=10)


def test_live_owner_cannot_be_displaced_then_death_releases_ownership(root, tmp_path):
    child = start_child(root, tmp_path, "hold")
    marker = state_dir(root) / "operation.lock"
    before = marker.read_bytes()
    try:
        with pytest.raises(RiposteError, match="WORKSPACE_LOCKED"):
            with workspace_lock(root):
                pytest.fail("Live owner displaced")
        assert marker.read_bytes() == before
    finally:
        child.kill()
        child.communicate(timeout=10)
    with workspace_lock(root):
        assert marker.exists()
    assert not marker.exists()


def test_nested_lock_is_not_reentrant_and_exception_releases_it(root):
    with pytest.raises(ValueError, match="fixture"):
        with workspace_lock(root):
            with pytest.raises(RiposteError, match="WORKSPACE_LOCKED"):
                with workspace_lock(root):
                    pytest.fail("Nested owner admitted")
            raise ValueError("fixture")
    with workspace_lock(root):
        pass


@pytest.mark.parametrize("abandoned", [False, True])
def test_concurrent_process_claims_admit_one_owner(root, tmp_path, abandoned):
    state_dir(root)
    if abandoned:
        prior = start_child(root, tmp_path, "hold", "exit")
        prior.communicate(timeout=10)
        assert prior.returncode == 23
    program = """
import sys
from pathlib import Path
from riposte.store import workspace_lock
from riposte.errors import RiposteError
sys.stdin.readline()
try:
    with workspace_lock(Path(sys.argv[1])):
        print('OWNED',flush=True)
        sys.stdin.readline()
except RiposteError as exc:
    print(exc.code,flush=True)
"""
    children = [subprocess.Popen([sys.executable, "-c", program, str(root)],
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, text=True) for _ in range(6)]
    try:
        for child in children:
            child.stdin.write("go\n")
            child.stdin.flush()
        # Each process reports before waiting; bound all pipe reads with a pool.
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=6) as pool:
            futures = [pool.submit(child.stdout.readline) for child in children]
            answers = [future.result(timeout=15).strip() for future in futures]
        assert answers.count("OWNED") == 1, answers
        assert answers.count("WORKSPACE_LOCKED") == 5, answers
    finally:
        for child in children:
            if child.poll() is None:
                child.kill()
            child.communicate(timeout=10)
    with workspace_lock(root):
        pass


@pytest.mark.parametrize("data", [b"", b"legacy", b"RIPOSTE_OS_LEASE_1\ninvalid\n"])
def test_unknown_legacy_markers_are_never_reclaimed(root, data):
    marker = state_dir(root) / "operation.lock"
    marker.write_bytes(data)
    before = marker.stat()
    with pytest.raises(RiposteError, match="WORKSPACE_LOCKED"):
        with workspace_lock(root):
            pytest.fail("Unknown lock reclaimed")
    assert marker.read_bytes() == data and marker.stat().st_ino == before.st_ino


def test_recovery_does_not_consult_pids_or_lock_age(root, tmp_path, monkeypatch):
    child = start_child(root, tmp_path, "hold", "exit")
    child.communicate(timeout=10)
    marker = state_dir(root) / "operation.lock"
    # Neither a reused PID nor arbitrary/future timestamps are ownership proof.
    os.utime(marker, (4_000_000_000, 4_000_000_000))
    def forbidden(*args, **kwargs):
        pytest.fail("Recovery attempted PID probing")
    monkeypatch.setattr(os, "kill", forbidden)
    monkeypatch.setattr(os, "getpid", forbidden)
    with workspace_lock(root):
        pass


def test_replaced_lease_cannot_prove_ownership_of_old_marker(root, tmp_path):
    child = start_child(root, tmp_path, "hold", "exit")
    child.communicate(timeout=10)
    marker = state_dir(root) / "operation.lock"
    before = marker.read_bytes()
    replacement = root / "replacement"
    replacement.touch()
    os.replace(replacement, root / LEASE_NAME)
    with pytest.raises(RiposteError, match="WORKSPACE_LOCKED"):
        with workspace_lock(root):
            pytest.fail("New lease reclaimed unrelated marker")
    assert marker.read_bytes() == before


def test_cleanup_never_removes_replacement_marker(root):
    with workspace_lock(root):
        marker = state_dir(root) / "operation.lock"
        replacement = marker.with_name("replacement")
        replacement.write_bytes(marker.read_bytes())
        os.replace(replacement, marker)
    assert marker.exists()


@pytest.mark.parametrize("kind", ["directory", "content", "hardlink"])
def test_invalid_lease_path_fails_closed(root, kind):
    lease = root / LEASE_NAME
    if kind == "directory":
        lease.mkdir()
    elif kind == "content":
        lease.write_bytes(b"not a lease")
    else:
        original = root / "unrelated"
        original.touch()
        os.link(original, lease)
    with pytest.raises(RiposteError, match="STATE_PATH_INVALID"):
        with workspace_lock(root):
            pytest.fail("Invalid lease path accepted")
    assert not (root / ".riposte").exists()


@pytest.mark.parametrize("after_link", [False, True])
def test_hard_exit_during_marker_publication_leaves_recoverable_claim(root, after_link):
    program = """
import os,sys
from pathlib import Path
from riposte.store import workspace_lock
root=Path(sys.argv[1]);after=sys.argv[2]=='True'
original=os.link
def interrupted(src,dst,*args,**kwargs):
    if Path(dst).name=='operation.lock':
        if after:original(src,dst,*args,**kwargs)
        os._exit(23)
    return original(src,dst,*args,**kwargs)
os.link=interrupted
with workspace_lock(root):raise AssertionError('unreachable')
"""
    child = subprocess.run([sys.executable, "-c", program, str(root), str(after_link)],
                           capture_output=True, text=True, timeout=15)
    assert child.returncode == 23, child.stderr
    marker = state_dir(root) / "operation.lock"
    assert marker.exists() is after_link
    if after_link:
        assert marker.read_bytes().startswith(b"RIPOSTE_OS_LEASE_1\n")
    with workspace_lock(root):
        pass


def test_legacy_claim_winning_marker_publication_is_preserved(root, monkeypatch):
    import riposte.store as store
    real = store._publish_lock_marker
    def legacy_wins(path, data, token):
        path.touch(exist_ok=False)
        return real(path, data, token)
    monkeypatch.setattr(store, "_publish_lock_marker", legacy_wins)
    with pytest.raises(RiposteError, match="WORKSPACE_LOCKED"):
        with workspace_lock(root):
            pytest.fail("Legacy claim overwritten")
    assert (state_dir(root) / "operation.lock").read_bytes() == b""


def test_body_io_failure_is_not_misreported_as_lock_failure(root):
    with pytest.raises(OSError, match="fixture disk full"):
        with workspace_lock(root):
            raise OSError("fixture disk full")
    with workspace_lock(root):
        pass


def test_private_lease_is_stable_and_excluded_from_sort_preview(root, make_image):
    make_image(root / "image.png")
    assert organizer.plan(root, POLICY)["ready"]
    assert not (root / LEASE_NAME).exists()
    organizer.organize(root, POLICY, plan_id=_sort_preview(root, POLICY)["plan_id"])
    identity = file_identity(root / LEASE_NAME)
    assert organizer.plan(root, POLICY)["ready"]
    organizer.undo_sort(root, apply=True)
    assert file_identity(root / LEASE_NAME) == identity
