"""Content-based acceptance cases, counterexamples, bounded coverage and no writes."""
from __future__ import annotations

from dataclasses import replace
import hashlib
from pathlib import Path
import random

from PIL import Image, ImageDraw, ImageEnhance, ImageOps, PngImagePlugin
import pytest

from riposte.duplicate_features import describe
from riposte.duplicate_index import HashIndex
from riposte.duplicates import ScanOptions, scan_duplicates
from riposte.errors import RiposteError


def artwork(seed=7):
    rng = random.Random(seed)
    im = Image.new('RGB', (320, 240), (28, 48, 65))
    draw = ImageDraw.Draw(im)
    for _ in range(70):
        x, y = rng.randrange(290), rng.randrange(210)
        draw.ellipse((x, y, x + rng.randrange(10, 40), y + rng.randrange(10, 40)),
                     fill=tuple(rng.randrange(30, 255) for _ in range(3)))
    draw.rectangle((15, 180, 95, 220), fill=(230, 60, 40))
    return im


@pytest.mark.parametrize('phase',['Discovering files','Hashing file contents','Fingerprinting distinct media',
                                  'Confirming visual relationships','Rechecking source identities'])
def test_cancel_at_each_content_stage_keeps_sources_unchanged(root,phase):
    im=artwork();im.save(root/'source.png');im.save(root/'copy.jpg',quality=85)
    before={p.name:p.read_bytes() for p in root.iterdir()}
    def cancel(event):
        if event.get('phase')==phase: raise RiposteError('JOB_CANCELLED')
    with pytest.raises(RiposteError,match='JOB_CANCELLED'): scan_duplicates(root,progress=cancel)
    assert before=={p.name:p.read_bytes() for p in root.iterdir()}


def pair(report, left, right):
    paths = {s['id']: s['relative'] for s in report['sources']}
    groups = {g['id']: {paths[i] for i in g['members']} for g in report['groups']}
    return [r for r in report['findings'] if (left in groups[r['left']] and
            right in groups[r['right']] if r['right'] else {left, right} <= groups[r['left']])
            or (r['right'] and right in groups[r['left']] and left in groups[r['right']])]


def test_exact_arbitrary_files_pixels_metadata_and_no_writes(root):
    im = artwork()
    im.save(root / 'original.png')
    (root / 'byte-copy.png').write_bytes((root / 'original.png').read_bytes())
    info = PngImagePlugin.PngInfo(); info.add_text('Comment', 'different metadata')
    im.save(root / 'metadata.png', pnginfo=info)
    (root / 'document.txt').write_text('same document')
    (root / 'document.bin').write_bytes((root / 'document.txt').read_bytes())
    before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.iterdir()}
    report = scan_duplicates(root)
    assert report['checkpoint'] == 'COMPLETE' and report['writes'] is False
    assert len(report['findings']) == 2
    assert pair(report, 'original.png', 'metadata.png')[0]['basis'] == 'NORMALIZED_PIXELS_EQUAL'
    assert pair(report, 'document.txt', 'document.bin')[0]['confidence'] == 100
    assert all(r['label'] == 'DUPLICATE' for r in report['findings'])
    assert before == {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in root.iterdir()}


@pytest.mark.parametrize('variant', ['jpeg', 'resize', 'rotate', 'mirror', 'brightness', 'crop'])
def test_real_image_variants_are_not_claimed_byte_duplicates(root, variant):
    im = artwork()
    im.save(root / 'original.png')
    if variant == 'jpeg':
        im.save(root / 'variant.jpg', quality=85)
        filename = 'variant.jpg'
    else:
        other = {'resize': lambda: im.resize((160, 120)), 'rotate': lambda: im.transpose(Image.Transpose.ROTATE_90),
                 'mirror': lambda: ImageOps.mirror(im), 'brightness': lambda: ImageEnhance.Brightness(im).enhance(1.1),
                 'crop': lambda: im.crop((80, 60, 240, 180))}[variant]()
        filename = 'variant.png'; other.save(root / filename)
    report = scan_duplicates(root)
    result = pair(report, 'original.png', filename)
    assert result, (variant, report['counts'])
    assert result[0]['label'] == ('CLOSELY RELATED' if variant == 'crop' else 'MAYBE DUPLICATE')
    assert 0 < result[0]['confidence'] < 100
    assert result[0]['confidence_kind'] == 'HEURISTIC_NOT_PROBABILITY'
    assert result[0]['metrics']['structural_32px'] > .7


def test_names_and_plain_colours_do_not_establish_relatedness(root):
    artwork(1).save(root / 'same-name-original.png')
    artwork(51).save(root / 'same-name-copy.png')
    Image.new('RGB', (320, 240), 'red').save(root / 'red.png')
    Image.new('RGB', (320, 240), 'blue').save(root / 'blue.png')
    report = scan_duplicates(root)
    assert not report['findings']
    assert report['counts']['low_information_media'] == 2


def test_alpha_and_hidden_colour_are_handled_explicitly(root):
    image = artwork().convert('RGBA')
    a = image.copy(); b = image.copy()
    a.putpixel((0, 0), (10, 20, 30, 0)); b.putpixel((0, 0), (90, 80, 70, 0))
    a.save(root / 'a.png'); b.save(root / 'b.png')
    result = scan_duplicates(root)
    assert pair(result, 'a.png', 'b.png')[0]['basis'] == 'NORMALIZED_PIXELS_EQUAL'
    image.putalpha(20); image.save(root / 'transparent.png')
    result = scan_duplicates(root)
    assert not pair(result, 'a.png', 'transparent.png')


def test_animated_and_high_bit_images_do_not_match_from_first_frame(root):
    first = artwork()
    first.save(root / 'a.gif', save_all=True, append_images=[artwork(9)], duration=50, loop=0)
    first.save(root / 'b.gif', save_all=True, append_images=[artwork(10)], duration=50, loop=0)
    Image.new('I', (50, 50), 3000).save(root / 'high.tiff')
    report = scan_duplicates(root)
    assert report['checkpoint'] == 'INCOMPLETE' and not report['findings']
    assert report['issues']['counts']['MULTIFRAME_REQUIRES_REVIEW'] == 2
    assert report['issues']['counts']['HIGH_BIT_DEPTH_REQUIRES_REVIEW'] == 1


def test_float_folders_are_an_explicit_independent_scan_scope(root):
    (root / '_float_').mkdir(); (root / '__FLOAT__').mkdir()
    for path in (root / 'a.txt', root / '_float_/b.txt', root / '__FLOAT__/c.txt'):
        path.write_text('personal synthetic storage')
    report = scan_duplicates(root)
    assert report['counts']['files_hashed'] == 3 and report['findings'][0]['member_count'] == 3
    excluded = scan_duplicates(root, ScanOptions(include_float=False))
    assert excluded['counts']['files_hashed'] == 1 and not excluded['findings']
    assert excluded['counts']['float_directories_excluded'] == 2


@pytest.mark.parametrize('change', ['modify', 'remove', 'add'])
def test_changes_during_scan_cannot_leave_authoritative_findings(root, change):
    (root / 'a.txt').write_text('duplicate'); (root / 'b.txt').write_text('duplicate')
    changed = False
    def progress(event):
        nonlocal changed
        if event['phase'] == 'Rechecking source identities' and not changed:
            changed = True
            if change == 'modify': (root / 'b.txt').write_text('different')
            elif change == 'remove': (root / 'b.txt').unlink()
            else: (root / 'new.txt').write_text('new')
    report = scan_duplicates(root, progress=progress)
    assert report['checkpoint'] == 'INCOMPLETE' and not report['findings']


def test_corrupt_files_do_not_hide_valid_exact_duplicates(root):
    (root / 'bad.png').write_bytes(b'not an image')
    (root / 'a.txt').write_text('same'); (root / 'b.txt').write_text('same')
    report = scan_duplicates(root)
    assert report['checkpoint'] == 'INCOMPLETE'
    assert pair(report, 'a.txt', 'b.txt')[0]['label'] == 'DUPLICATE'
    assert report['issues']['examples'][0]['path'] == 'bad.png'


@pytest.mark.parametrize('field', ['max_files', 'max_visual', 'max_file_bytes', 'max_pairs', 'max_findings'])
def test_resource_limits_report_partial_results(root, field):
    image = artwork()
    image.save(root / 'a.png'); image.save(root / 'b.jpg', quality=90)
    image.resize((160, 120)).save(root / 'c.png')
    report = scan_duplicates(root, replace(ScanOptions(), **{field: 1}))
    assert report['checkpoint'] == 'INCOMPLETE', (field, report)
    assert report['issues']['counts']


def test_cancel_propagates_without_creating_workspace(root):
    (root / 'a.txt').write_text('hello')
    def stop(event):
        raise RiposteError('JOB_CANCELLED')
    with pytest.raises(RiposteError, match='JOB_CANCELLED'):
        scan_duplicates(root, progress=stop)
    assert sorted(p.name for p in root.iterdir()) == ['a.txt']


def test_hamming_index_matches_exhaustive_radius_and_signals_incomplete():
    rng = random.Random(71)
    values = [rng.getrandbits(63) for _ in range(200)]
    values.extend(value ^ 7 for value in values[:10])
    index = HashIndex()
    for i, value in enumerate(values): index.add(value, (i, 0, 0))
    for value in values[:10]:
        actual, complete, _ = index.query(value)
        assert complete
        assert {ref[0] for _, ref in actual} == {i for i, other in enumerate(values) if (value ^ other).bit_count() <= 12}
    assert index.query(values[0], budget=1)[1] is False
    assert index.query(values[0], limit=1)[1] is False


def test_exact_mode_is_independent_of_image_decoding(root):
    (root / 'bad.png').write_bytes(b'invalid pixels')
    (root / 'copy.png').write_bytes((root / 'bad.png').read_bytes())
    report = scan_duplicates(root, ScanOptions(visual=False))
    assert report['checkpoint'] == 'COMPLETE'
    assert report['findings'][0]['basis'] == 'BYTE_EQUAL'


def test_order_independent_report_and_no_transitive_similarity_claim(root):
    image = artwork(); image.save(root / 'a.png')
    image.resize((160, 120)).save(root / 'b.png')
    ImageOps.mirror(image).save(root / 'c.png')
    one, two = scan_duplicates(root), scan_duplicates(root)
    assert one == two
    assert all(len(group['members']) == 1 for group in one['groups'])
    assert len(one['findings']) == 3
