"""Independent, read-only duplicate inventory and evidence-bound relationships."""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
from typing import cast

from .duplicate_features import Visual, compare_views
from .duplicate_index import HashIndex
from .duplicate_media import equal_pixels, image_signature, video_signature
from .errors import RiposteError
from .locking import LEASE_NAME
from .policy import IMAGE_SUFFIXES, FLOAT_DIRECTORIES, is_link
from .records import Progress
from .store import application_directory
from .video import VIDEO_SUFFIXES

VERSION = 'duplicates-1'
LABELS = ('DUPLICATE', 'MAYBE DUPLICATE', 'CLOSELY RELATED')
PRIVATE_DIRECTORIES = frozenset({'.riposte', '.shroud', '.git', '__pycache__'})


@dataclass(frozen=True)
class ScanOptions:
    visual: bool = True
    videos: bool = True
    include_float: bool = True
    max_files: int = 100_000
    max_visual: int = 10_000
    max_pairs: int = 100_000
    max_findings: int = 20_000
    max_file_bytes: int = 4 * 1024**3
    max_pixels: int = 60_000_000

    def __post_init__(self) -> None:
        if any(type(value) is not bool for value in (self.visual, self.videos, self.include_float)):
            raise RiposteError('DUPLICATE_OPTIONS_INVALID')
        for value, maximum in ((self.max_files, 200_000), (self.max_visual, 20_000),
                               (self.max_pairs, 500_000), (self.max_findings, 50_000),
                               (self.max_file_bytes, 64 * 1024**3), (self.max_pixels, 60_000_000)):
            if type(value) is not int or not 1 <= value <= maximum:
                raise RiposteError('DUPLICATE_OPTIONS_INVALID')


@dataclass
class Source:
    id: str
    relative: str
    bytes: int
    state: tuple[int, int, int, int, int]
    media: str
    sha256: str = ''
    pixel_sha256: str | None = None
    width: int | None = None
    height: int | None = None
    duration: float | None = None
    visual_status: str = 'NOT_REQUESTED'
    hardlinks: int = 1


@dataclass
class Entity:
    members: list[Source]
    frames: tuple[Visual, ...] = ()
    basis: str = 'BYTE_EQUAL'

    @property
    def id(self) -> str:
        return hashlib.sha256(('group:' + ':'.join(sorted(s.id for s in self.members))).encode()).hexdigest()[:24]

    @property
    def representative(self) -> Source:
        return self.members[0]


@dataclass
class Issues:
    counts: Counter[str] = field(default_factory=Counter)
    examples: list[dict[str, str]] = field(default_factory=list)

    def add(self, code: str, relative: str = '') -> None:
        self.counts[code] += 1
        if len(self.examples) < 1000:
            self.examples.append({'code': code, 'path': relative})


def source_state(path: Path) -> tuple[int, int, int, int, int]:
    stat = path.stat()
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns


def scan_root(root: Path) -> Path:
    """Validate a read-only folder without opening sorting/publishing state."""
    root = root.expanduser().absolute()
    if not root.is_dir() or is_link(root): raise RiposteError('ROOT_INVALID')
    if any(is_link(parent) for parent in root.parents): raise RiposteError('ROOT_LINKED')
    resolved, app = root.resolve(), application_directory()
    if resolved == app or resolved.is_relative_to(app) or app.is_relative_to(resolved):
        raise RiposteError('IMAGE_FOLDER_OVERLAPS_APPLICATION')
    return root


def scan_path(root: Path, relative: str) -> Path:
    root = scan_root(root)
    path = Path(relative)
    if path.is_absolute() or path.drive or any(part == '..' for part in path.parts) or '\\' in relative:
        raise RiposteError('PATH_REJECTED')
    current = root
    for part in path.parts:
        current /= part
        if is_link(current): raise RiposteError('DUPLICATE_SOURCE_CHANGED')
    return current


def verify_source(root: Path, source: Source) -> Path:
    path = scan_path(root, source.relative)
    if not path.is_file() or is_link(path) or source_state(path) != source.state:
        raise RiposteError('DUPLICATE_SOURCE_CHANGED')
    return path


def content_hash(root: Path, source: Source, progress: Progress | None = None) -> str:
    path = verify_source(root, source)
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        stat = os.fstat(stream.fileno())
        if (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns) != source.state[:4]:
            raise RiposteError('DUPLICATE_SOURCE_CHANGED')
        count = 0
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            count += len(chunk)
            if progress:
                progress({'phase': 'Hashing file contents', 'file_bytes_read': count, 'file_bytes_total': source.bytes})
        after = os.fstat(stream.fileno())
        if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != source.state[:4]:
            raise RiposteError('DUPLICATE_SOURCE_CHANGED')
    verify_source(root, source)
    return digest.hexdigest()


def equal_bytes(root: Path, left: Source, right: Source, progress: Progress | None = None) -> bool:
    a, b = verify_source(root, left), verify_source(root, right)
    if left.bytes != right.bytes:
        return False
    equal = True
    with a.open('rb') as first, b.open('rb') as second:
        while True:
            x, y = first.read(1024 * 1024), second.read(1024 * 1024)
            if progress:
                progress({'phase': 'Verifying exact duplicate bytes'})
            if x != y:
                equal = False
                break
            if not x:
                break
    verify_source(root, left)
    verify_source(root, right)
    return equal


def inventory(root: Path, options: ScanOptions, issues: Issues, counts: Counter[str],
              progress: Progress | None = None) -> tuple[list[Source], dict[str, tuple[int, int, int, int, int]]]:
    files: list[Source] = []
    directories: dict[str, tuple[int, int, int, int, int]] = {}
    pending = [root]
    while pending:
        directory = pending.pop()
        relative = directory.relative_to(root).as_posix()
        if progress:
            progress({'phase': 'Discovering files', 'processed': len(files)})
        try:
            if is_link(directory):
                issues.add('LINK_SKIPPED', relative)
                continue
            directories[relative] = source_state(directory)
            with os.scandir(directory) as stream:
                entries = sorted(stream, key=lambda entry: (entry.name.casefold(), entry.name))
            children = []
            for entry_number, entry in enumerate(entries):
                if progress and entry_number % 128 == 0:
                    progress({'phase': 'Discovering files', 'processed': len(files)})
                path = directory / entry.name
                name = path.relative_to(root).as_posix()
                if entry.name.casefold() in PRIVATE_DIRECTORIES and entry.is_dir(follow_symlinks=False):
                    counts['private_directories_excluded'] += 1
                    continue
                if is_link(path):
                    issues.add('LINK_SKIPPED', name)
                elif entry.is_dir(follow_symlinks=False):
                    if entry.name.casefold() in PRIVATE_DIRECTORIES:
                        counts['private_directories_excluded'] += 1
                    elif not options.include_float and entry.name.casefold() in FLOAT_DIRECTORIES:
                        counts['float_directories_excluded'] += 1
                    else:
                        children.append(path)
                elif entry.is_file(follow_symlinks=False):
                    if entry.name == LEASE_NAME:
                        counts['private_files_excluded'] += 1
                        continue
                    if len(files) >= options.max_files:
                        issues.add('FILE_LIMIT_REACHED', name)
                        return files, directories
                    stat = path.stat()
                    if stat.st_size > options.max_file_bytes:
                        issues.add('FILE_BYTES_LIMIT', name)
                        continue
                    suffix = path.suffix.casefold()
                    media = 'image' if suffix in IMAGE_SUFFIXES else 'video' if suffix in VIDEO_SUFFIXES else 'file'
                    files.append(Source(hashlib.sha256(name.encode()).hexdigest()[:24], name, stat.st_size,
                                        source_state(path), media, hardlinks=stat.st_nlink))
                else:
                    issues.add('SPECIAL_FILE_SKIPPED', name)
            pending.extend(reversed(children))
        except OSError:
            issues.add('DIRECTORY_UNREADABLE', relative)
    return sorted(files, key=lambda source: source.relative), directories


def temporal_evidence(left: Entity, right: Entity, candidate: dict[str, object]) -> dict[str, object] | None:
    lm, rm = left.representative.media, right.representative.media
    if lm == rm == 'image':
        return candidate
    if lm != rm:
        return {**candidate, 'label': 'CLOSELY RELATED', 'basis': 'IMAGE_IN_SAMPLED_VIDEO_FRAME'}
    matches = []
    aligned = 0
    for i, a in enumerate(left.frames):
        for j, b in enumerate(right.frames):
            if not a.views or not b.views:
                continue
            # Corresponding normalized times, plus overlap for a related excerpt.
            value = compare_views(a, a.views[0], b, b.views[0])
            if value:
                matches.append((i, j, value))
                aligned += int(i == j and value['label'] == 'MAYBE DUPLICATE')
    represented_left = {i for i, _, _ in matches}
    represented_right = {j for _, j, _ in matches}
    if min(len(represented_left), len(represented_right)) < 3:
        return None
    duration_a, duration_b = left.representative.duration or 0, right.representative.duration or 0
    ratio = min(duration_a, duration_b) / max(duration_a, duration_b) if duration_a and duration_b else 0
    distinctive = len({frame.views[0].phash for frame in left.frames if frame.views}) >= 3
    strong = aligned >= 4 and ratio >= .98 and distinctive
    scores = [float(cast(float, value['confidence'])) for i, j, value in matches if i == j] if strong else [float(cast(float, value['confidence'])) for _, _, value in matches]
    return {**candidate, 'label': 'MAYBE DUPLICATE' if strong else 'CLOSELY RELATED',
            'basis': 'SAMPLED_VIDEO_SEQUENCE' if strong else 'SAMPLED_VIDEO_OVERLAP',
            'confidence': min(99., round(sum(scores) / len(scores), 1)),
            'temporal': {'aligned_strong_frames': aligned, 'sampled_frames_per_video': 5,
                         'matched_left_frames': len(represented_left), 'matched_right_frames': len(represented_right),
                         'duration_ratio': round(ratio, 4), 'audio_compared': False,
                         'distinctive_sequence': distinctive}}


def relationships(entities: list[Entity], options: ScanOptions, issues: Issues,
                  counts: Counter[str], progress: Progress | None = None) -> list[dict[str, object]]:
    index = HashIndex()
    findings: list[dict[str, object]] = []
    for right_id, right in enumerate(entities):
        if progress:
            progress({'phase': 'Comparing visual candidates', 'processed': right_id + 1, 'total': len(entities)})
        # Best retrieved view pairs per entity pair; never materialize N*N pairs.
        candidates: dict[int, list[tuple[int, int, int, int, int]]] = {}
        for rf, frame in enumerate(right.frames):
            for rv, view in enumerate(frame.views):
                found, complete, visited = index.query(view.phash)
                counts['index_nodes_visited'] += visited
                if not complete:
                    issues.add('CANDIDATE_QUERY_LIMIT', right.representative.relative)
                for distance, (left_id, lf, lv) in found:
                    if view.coverage < 1 and entities[left_id].frames[lf].views[lv].coverage < 1:
                        continue
                    if left_id not in candidates and len(candidates) + counts['candidate_pairs'] >= options.max_pairs:
                        issues.add('COMPARISON_LIMIT_REACHED')
                        return findings
                    values = candidates.setdefault(left_id, [])
                    item = (distance, lf, lv, rf, rv)
                    if item not in values:
                        values.append(item)
                        values.sort()
                        del values[8:]
        for left_id, choices in sorted(candidates.items()):
            if progress:
                progress({'phase': 'Confirming visual relationships', 'processed': counts['candidate_pairs']})
            counts['candidate_pairs'] += 1
            left = entities[left_id]
            best: dict[str, object] | None = None
            for _, lf, lv, rf, rv in choices:
                a, b = left.frames[lf], right.frames[rf]
                value = compare_views(a, a.views[lv], b, b.views[rv])
                counts['view_comparisons'] += 1
                if value and (best is None or (value['label'] == 'MAYBE DUPLICATE', cast(float, value['confidence']))
                              > (best['label'] == 'MAYBE DUPLICATE', cast(float, best['confidence']))):
                    best = value
            if best:
                best = temporal_evidence(left, right, best)
            if best:
                findings.append({'id': hashlib.sha256((left.id + ':' + right.id).encode()).hexdigest()[:24],
                                 'left': left.id, 'right': right.id, **best})
                if len(findings) >= options.max_findings:
                    issues.add('FINDING_LIMIT_REACHED')
                    return findings
        for frame_id, frame in enumerate(right.frames):
            for view_id, view in enumerate(frame.views):
                index.add(view.phash, (right_id, frame_id, view_id))
    counts['index_nodes'] = len(index.nodes)
    return findings


def scan_duplicates(root: Path, options: ScanOptions = ScanOptions(), *,
                    progress: Progress | None = None) -> dict[str, object]:
    root = scan_root(root)
    issues, counts = Issues(), Counter[str]()
    sources, directories = inventory(root, options, issues, counts, progress)
    counts['files_discovered'] = len(sources)
    hashed: dict[tuple[int, str], list[Entity]] = defaultdict(list)
    entities: list[Entity] = []
    for number, source in enumerate(sources, 1):
        if progress:
            progress({'phase': 'Reading duplicate evidence', 'processed': number, 'total': len(sources)})
        try:
            source.sha256 = content_hash(root, source, progress)
            counts['files_hashed'] += 1
            counts['bytes_hashed'] += source.bytes
            bucket = hashed[source.bytes, source.sha256]
            previous = next((entity for entity in bucket if equal_bytes(root, entity.representative, source, progress)), None)
            if previous:
                previous.members.append(source)
            else:
                entity = Entity([source])
                bucket.append(entity)
                entities.append(entity)
        except (OSError, RiposteError) as exc:
            if isinstance(exc, RiposteError) and exc.code == 'JOB_CANCELLED':
                raise
            issues.add(exc.code if isinstance(exc, RiposteError) else 'FILE_UNREADABLE', source.relative)
    counts['byte_groups'] = sum(len(entity.members) > 1 for entity in entities)
    for entity in entities:
        entity.members.sort(key=lambda member: (member.media == 'file', member.relative))
    # Collapse byte-identical files before any image decode or video subprocess.
    pixels: dict[str, list[Entity]] = defaultdict(list)
    final: list[Entity] = []
    visual_count = 0
    for number, entity in enumerate(entities, 1):
        source = entity.representative
        if progress:
            progress({'phase': 'Fingerprinting distinct media', 'processed': number, 'total': len(entities)})
        if options.visual and source.media in {'image', 'video'} and (source.media != 'video' or options.videos):
            if visual_count >= options.max_visual:
                issues.add('VISUAL_FILE_LIMIT_REACHED', source.relative)
                source.visual_status = 'LIMIT_REACHED'
            else:
                visual_count += 1
                try:
                    path = verify_source(root, source)
                    signature = image_signature(path, max_pixels=options.max_pixels) if source.media == 'image' else video_signature(path, progress=progress)
                    verify_source(root, source)
                    source.width, source.height = signature.width, signature.height
                    source.duration, source.pixel_sha256 = signature.duration, signature.pixel_sha256
                    source.visual_status = 'READY' if any(frame.views for frame in signature.frames) else 'LOW_INFORMATION'
                    for member in entity.members:
                        member.media, member.width, member.height = source.media, source.width, source.height
                        member.duration, member.pixel_sha256 = source.duration, source.pixel_sha256
                        member.visual_status = source.visual_status
                    entity.frames = signature.frames
                    counts['media_fingerprinted'] += 1
                    if source.visual_status == 'LOW_INFORMATION':
                        counts['low_information_media'] += 1
                    if signature.pixel_sha256:
                        prior = next((other for other in pixels[signature.pixel_sha256]
                                      if equal_pixels(verify_source(root, other.representative), path, max_pixels=options.max_pixels)), None)
                        if prior:
                            prior.members.extend(entity.members)
                            prior.basis = 'NORMALIZED_PIXELS_EQUAL'
                            continue
                        pixels[signature.pixel_sha256].append(entity)
                except (OSError, RiposteError) as exc:
                    if isinstance(exc, RiposteError) and exc.code == 'JOB_CANCELLED':
                        raise
                    source.visual_status = exc.code if isinstance(exc, RiposteError) else 'MEDIA_UNREADABLE'
                    issues.add(source.visual_status, source.relative)
        final.append(entity)
    matches = relationships(final, options, issues, counts, progress) if options.visual else []
    invalid: set[str] = set()
    for source in sources:
        if progress:
            progress({'phase': 'Rechecking source identities'})
        try:
            verify_source(root, source)
        except (OSError, RiposteError):
            invalid.add(source.id)
            issues.add('DUPLICATE_SOURCE_CHANGED', source.relative)
    changed_tree = False
    for relative, before in directories.items():
        try:
            path = root if relative == '.' else scan_path(root, relative)
            if source_state(path) != before:
                changed_tree = True
        except (OSError, RiposteError):
            changed_tree = True
    if changed_tree:
        issues.add('DIRECTORY_CHANGED_RESCAN')
    valid_entities = [entity for entity in final if not any(source.id in invalid for source in entity.members)]
    valid_ids = {entity.id for entity in valid_entities}
    matches = [match for match in matches if match['left'] in valid_ids and match['right'] in valid_ids]
    groups = []
    for entity in valid_entities:
        members = sorted(entity.members, key=lambda source: source.relative)
        groups.append({'id': entity.id, 'members': [source.id for source in members],
                       'representative': entity.representative.id, 'basis': entity.basis,
                       'media': entity.representative.media, 'count': len(members)})
        if len(members) > 1:
            matches.append({'id': 'exact-' + entity.id, 'left': entity.id, 'right': None,
                            'label': 'DUPLICATE', 'confidence': 100., 'confidence_kind': 'VERIFIED_EQUALITY',
                            'basis': entity.basis, 'member_count': len(members)})
    if changed_tree:
        # The source set changed while scanning; avoid presenting a stale snapshot.
        matches = []
    matches.sort(key=lambda match: (LABELS.index(cast(str, match['label'])), -cast(float, match['confidence']), cast(str, match['id'])))
    if len(matches) > options.max_findings:
        issues.add('FINDING_LIMIT_REACHED')
        matches = matches[:options.max_findings]
    for label in LABELS:
        counts[label] = sum(match['label'] == label for match in matches)
    counts['distinct_content_groups'] = len(groups)
    counts['findings'] = len(matches)
    records = [asdict(source) for source in sources]
    # Tuple state becomes a JSON-native list at the shared operation boundary.
    for record in records:
        record['state'] = list(record['state'])
    basis = {'version': VERSION, 'root': str(root), 'options': asdict(options), 'sources': records,
             'groups': groups, 'matches': matches, 'issues': dict(issues.counts)}
    identifier = hashlib.sha256(json.dumps(basis, sort_keys=True).encode()).hexdigest()
    return {'mode': 'DUPLICATE_SCAN', 'version': VERSION, 'scan_id': identifier, 'root': str(root),
            'checkpoint': 'INCOMPLETE' if issues.counts else 'COMPLETE', 'writes': False,
            'options': asdict(options), 'counts': dict(counts), 'sources': records, 'groups': groups,
            'findings': matches, 'issues': {'counts': dict(issues.counts), 'examples': issues.examples,
                                         'omitted_examples': sum(issues.counts.values()) - len(issues.examples)},
            'confidence_policy': '100 means verified equality for the stated basis. Other scores are heuristic evidence, not probabilities.',
            'coverage': {'exact': 'All successfully hashed files, with byte verification; image equality uses complete normalized still-image pixels.',
                         'visual': 'DCT radius 12; eight whole-image orientations; center/corner crops at 75% and 50% edges; at most eight candidate views per pair.',
                         'video': 'Five timestamps per video; sampled visual sequence only. Audio and unsampled frames are not compared.',
                         'relations': 'Similarities are direct pair relationships, never transitive duplicate groups.',
                         'snapshot': 'Sources rechecked at scan completion; review revalidates selected content. Concurrent filesystem activity is not an atomic snapshot.'}}
