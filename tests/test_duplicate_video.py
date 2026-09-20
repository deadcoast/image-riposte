"""Actual local FFmpeg decoding; synthetic clips do not qualify real-world recall."""
import io
from pathlib import Path
import shutil
import subprocess

from PIL import Image
import pytest

from riposte.duplicate_review import DuplicateReview
from riposte.duplicates import scan_duplicates, ScanOptions
from test_duplicates import artwork, pair


def ffmpeg(*args):
    executable=shutil.which('ffmpeg')
    if not executable or not shutil.which('ffprobe'): pytest.skip('Local FFmpeg/ffprobe required')
    run=subprocess.run([executable,'-nostdin','-v','error',*map(str,args)],capture_output=True,timeout=30)
    assert run.returncode==0,run.stderr.decode(errors='replace')


def clip(root, destination, seed=7, static=False):
    root.mkdir()
    for number in range(5): artwork(seed if static else seed+number).save(root/f'frame-{number}.png')
    ffmpeg('-framerate','1','-i',root/'frame-%d.png','-c:v','libx264','-crf','10','-pix_fmt','yuv420p',destination)


def test_actual_video_reencode_exact_copy_still_frame_and_unrelated_sequence(root,tmp_path):
    clip(tmp_path/'frames',root/'original.mp4')
    shutil.copyfile(root/'original.mp4',root/'copy.mp4')
    ffmpeg('-i',root/'original.mp4','-c:v','libx264','-crf','22',root/'reencoded.mkv')
    clip(tmp_path/'different-frames',root/'unrelated.mp4',seed=70)
    shutil.copyfile(tmp_path/'frames'/'frame-2.png',root/'poster.png')
    report=scan_duplicates(root)
    assert report['checkpoint']=='COMPLETE',report['issues']
    assert pair(report,'original.mp4','copy.mp4')[0]['label']=='DUPLICATE'
    assert pair(report,'original.mp4','reencoded.mkv')[0]['label']=='MAYBE DUPLICATE'
    assert pair(report,'original.mp4','poster.png')[0]['label']=='CLOSELY RELATED'
    assert not pair(report,'original.mp4','unrelated.mp4')
    match=pair(report,'original.mp4','reencoded.mkv')[0]
    assert match['temporal']['audio_compared'] is False and match['temporal']['aligned_strong_frames']>=4
    review=DuplicateReview(report)
    source=next(record for record in report['sources'] if record['relative']=='original.mp4')
    with Image.open(io.BytesIO(review.preview(source['id'],timestamp=2.5))) as image:
        assert image.size==(384,288) and not image.info


def test_static_videos_are_related_not_maybe_duplicates(root,tmp_path):
    clip(tmp_path/'static',root/'one.mp4',static=True)
    ffmpeg('-i',root/'one.mp4','-c:v','libx264','-crf','25',root/'two.mkv')
    report=scan_duplicates(root)
    assert pair(report,'one.mp4','two.mkv')[0]['label']=='CLOSELY RELATED'


def test_unavailable_video_tools_keep_exact_results_and_disclose_missingness(root,monkeypatch):
    (root/'one.mp4').write_bytes(b'fixture')
    (root/'two.mp4').write_bytes(b'fixture')
    monkeypatch.setattr('riposte.duplicate_media.shutil.which',lambda _: None)
    report=scan_duplicates(root)
    assert report['counts']['DUPLICATE']==1
    assert report['issues']['counts']['DUPLICATE_VIDEO_TOOLS_UNAVAILABLE']==1
    assert report['checkpoint']=='INCOMPLETE'
    assert scan_duplicates(root,ScanOptions(videos=False))['checkpoint']=='COMPLETE'
