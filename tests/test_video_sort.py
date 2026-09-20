"""Real local ffmpeg/ffprobe fixtures; no protection model or video generation."""
from riposte.organizer import plan as _sort_preview
import datetime as dt
import os
import shutil
import subprocess

import pytest

from riposte.organizer import audit_workspace, organize, plan, undo_sort
from riposte.policy import Policy
from riposte.store import catalog
from riposte.video import video_catalog

POLICY = Policy(date_mode="modified")


@pytest.fixture
def make_video():
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("Real video fixture needs local ffmpeg and ffprobe")
    def create(path):
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=64x48:r=2",
                        "-t", "1", "-metadata", "comment=PRIVATE_VIDEO_METADATA", str(path)], check=True,
                       capture_output=True, timeout=30, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        stamp = dt.datetime(2025, 3, 12, 12).timestamp()
        os.utime(path, (stamp, stamp))
        return path
    return create


def test_numbered_video_sorts_with_optional_categories_and_no_rules(root, make_video):
    video = make_video(root / 'SML01.mp4'); original = video.read_bytes()
    preview = plan(root, POLICY, categories=True)
    assert preview['ready'] and preview['files'][0]['category'] is None
    assert preview['files'][0]['original_filename'] is None
    assert organize(root, POLICY, categories=True, plan_id=preview['plan_id'])['checkpoint'] == 'COMPLETE'
    row = video_catalog(root)[0]
    assert row['relative'] == '2025/March/vid/SML/SML01.mp4'
    assert (root / row['relative']).read_bytes() == original
    assert audit_workspace(root)['checkpoint'] == 'COMPLETE'
    assert undo_sort(root, apply=True)['checkpoint'] == 'COMPLETE'
    assert video.read_bytes() == original


@pytest.mark.parametrize("extension", ["mp4", "mov", "mkv", "webm", "avi"])
def test_real_mixed_video_sort_preview_idempotence_and_undo(root, make_image, make_video, extension):
    image = make_image(root / "photo.png")
    video = make_video(root / ("clip." + extension))
    original_image, original_video = image.read_bytes(), video.read_bytes()
    preview = plan(root, POLICY)
    assert preview["ready"]
    assert preview["destinations"] == {"2025/March/img/SML": 1, "2025/March/vid/SML": 1}
    assert image.read_bytes() == original_image and video.read_bytes() == original_video
    assert not (root / ".riposte").exists()
    result = organize(root, POLICY, plan_id=_sort_preview(root, POLICY)["plan_id"])
    assert result["checkpoint"] == "COMPLETE"
    assert result["counts"]["videos_sorted"] == 1
    assert len(catalog(root)) == len(video_catalog(root)) == 1
    row = video_catalog(root)[0]
    assert row["relative"] == "2025/March/vid/SML/SML01." + extension
    assert (root / row["relative"]).read_bytes() == original_video
    assert audit_workspace(root)["checkpoint"] == "COMPLETE"
    assert audit_workspace(root)["verified_videos"] == 1
    assert organize(root, POLICY, plan_id=_sort_preview(root, POLICY)["plan_id"])["counts"]["already_sorted_videos"] == 1
    assert undo_sort(root, apply=True)["checkpoint"] == "COMPLETE"
    assert image.read_bytes() == original_image and video.read_bytes() == original_video
    assert catalog(root) == video_catalog(root) == []


def test_probe_missing_does_not_break_image_sorting(root, make_image, monkeypatch):
    monkeypatch.setattr("riposte.video.shutil.which", lambda _: None)
    make_image(root / "photo.png")
    assert plan(root, POLICY)["ready"]
    video = root / "clip.mp4"
    video.write_bytes(b"not probed")
    assert plan(root, POLICY)["blockers"] == {"VIDEO_PROBE_UNAVAILABLE": 1}
    assert organize(root, POLICY, plan_id=_sort_preview(root, POLICY)["plan_id"])["checkpoint"] == "INCOMPLETE"
    assert video.read_bytes() == b"not probed"
    assert len(catalog(root)) == 1


def test_corrupt_video_is_never_moved_or_registered(root):
    if not shutil.which("ffprobe"):
        pytest.skip("Needs ffprobe")
    video = root / "broken.mp4"
    video.write_bytes(b"not a video")
    assert plan(root, POLICY)["blockers"] == {"VIDEO_PROBE_FAILED": 1}
    assert organize(root, POLICY, plan_id=_sort_preview(root, POLICY)["plan_id"])["checkpoint"] == "INCOMPLETE"
    assert video.read_bytes() == b"not a video" and not video_catalog(root)


def test_video_only_sort_never_populates_protection_selection(root, make_video):
    from riposte.terminal.service import image_selection
    make_video(root / "video.mp4")
    assert organize(root, POLICY, plan_id=_sort_preview(root, POLICY)["plan_id"])["checkpoint"] == "COMPLETE"
    assert image_selection(root, {"all_images": True}) == []
