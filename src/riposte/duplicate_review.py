"""Shared filtering, evidence details, verified previews and explicit report export."""
from __future__ import annotations

import csv
import io
import json
import math
from pathlib import Path
from typing import cast

from .duplicate_media import thumbnail
from .duplicates import LABELS, Source, content_hash, verify_source, scan_root
from .errors import RiposteError
from .policy import is_link


class DuplicateReview:
    def __init__(self, report: dict[str, object]) -> None:
        self.report = report
        self.sources = {cast(str, source['id']): source for source in cast(list[dict[str, object]], report['sources'])}
        self.groups = {cast(str, group['id']): group for group in cast(list[dict[str, object]], report['groups'])}
        self.findings = {cast(str, finding['id']): finding for finding in cast(list[dict[str, object]], report['findings'])}
        self.rows = []
        for finding in self.findings.values():
            left = self.groups[cast(str, finding['left'])]
            right = self.groups[cast(str, finding['right'])] if finding['right'] else left
            left_ids = cast(list[str], left['members'])
            right_ids = cast(list[str], right['members'])
            a = cast(str, left['representative'])
            b = cast(str, right['representative']) if finding['right'] else next(identifier for identifier in left_ids if identifier != a)
            paths = [cast(str, self.sources[i]['relative']) for i in dict.fromkeys([*left_ids, *right_ids])]
            self.rows.append({'id': finding['id'], 'label': finding['label'], 'confidence': finding['confidence'],
                              'basis': finding['basis'], 'left_source': a, 'right_source': b,
                              'left_path': self.sources[a]['relative'], 'right_path': self.sources[b]['relative'],
                              'left_count': left['count'], 'right_count': right['count'] if finding['right'] else 0,
                              'member_count': len(paths), 'media': left['media'] if left['media'] == right['media'] else 'mixed',
                              'search_text': '\n'.join(paths).casefold()})

    def summary(self) -> dict[str, object]:
        return {key: value for key, value in self.report.items() if key not in {'sources', 'groups', 'findings'}}

    def page(self, *, label: str = 'ALL', search: str = '', media: str = 'ALL', min_confidence: float = 0,
             order: str = 'confidence', offset: int = 0, limit: int = 50) -> dict[str, object]:
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 200:
            raise RiposteError('DUPLICATE_FILTER_INVALID')
        rows = self.select(label=label, search=search, media=media, min_confidence=min_confidence, order=order)
        offset = min(offset, ((len(rows) - 1) // limit) * limit) if rows else 0
        return {'scan_id': self.report['scan_id'], 'total': len(rows), 'offset': offset, 'limit': limit,
                'rows': [{key: value for key, value in row.items() if key != 'search_text'} for row in rows[offset:offset + limit]]}

    def select(self, *, label: str = 'ALL', search: str = '', media: str = 'ALL', min_confidence: float = 0,
               order: str = 'confidence') -> list[dict[str, object]]:
        if (label not in ('ALL', *LABELS) or media not in {'ALL', 'image', 'video', 'file', 'mixed'}
                or order not in {'confidence', 'path', 'members'} or not isinstance(search, str) or len(search) > 500
                or isinstance(min_confidence, bool) or not isinstance(min_confidence, (int, float))
                or not math.isfinite(min_confidence) or not 0 <= min_confidence <= 100):
            raise RiposteError('DUPLICATE_FILTER_INVALID')
        query = search.casefold().strip()
        rows = [row for row in self.rows if (label == 'ALL' or row['label'] == label)
                and (media == 'ALL' or row['media'] == media)
                and cast(float, row['confidence']) >= min_confidence
                and (not query or query in cast(str, row['search_text']))]
        if order == 'path':
            rows.sort(key=lambda row: (cast(str, row['left_path']).casefold(), cast(str, row['id'])))
        elif order == 'members':
            rows.sort(key=lambda row: (-cast(int, row['member_count']), cast(str, row['id'])))
        else:
            rows.sort(key=lambda row: (LABELS.index(cast(str, row['label'])), -cast(float, row['confidence']), cast(str, row['id'])))
        return rows

    def group(self, identifier: str, *, offset: int = 0, limit: int = 50) -> dict[str, object]:
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 200:
            raise RiposteError('DUPLICATE_FILTER_INVALID')
        group = self.groups.get(identifier)
        if group is None:
            raise RiposteError('DUPLICATE_FINDING_NOT_FOUND')
        members = cast(list[str], group['members'])
        offset = min(offset, ((len(members) - 1) // limit) * limit) if members else 0
        return {**group, 'members': [self.sources[i] for i in members[offset:offset + limit]],
                'representative_record': self.sources[cast(str, group['representative'])], 'offset': offset, 'limit': limit}

    def detail(self, identifier: str) -> dict[str, object]:
        finding = self.findings.get(identifier)
        if finding is None:
            raise RiposteError('DUPLICATE_FINDING_NOT_FOUND')
        return {'mode': 'DUPLICATE_FINDING', 'scan_id': self.report['scan_id'], 'finding': finding,
                'left': self.group(cast(str, finding['left'])),
                'right': self.group(cast(str, finding['right'])) if finding['right'] else None,
                'confidence_policy': self.report['confidence_policy']}

    def preview(self, identifier: str, *, timestamp: float | None = None) -> bytes:
        record = self.sources.get(identifier)
        if record is None or (timestamp is not None and (not math.isfinite(timestamp) or timestamp < 0)):
            raise RiposteError('DUPLICATE_PREVIEW_UNAVAILABLE')
        source = Source(cast(str, record['id']), cast(str, record['relative']), cast(int, record['bytes']),
                        cast(tuple[int, int, int, int, int], tuple(cast(list[int], record['state']))), cast(str, record['media']),
                        sha256=cast(str, record['sha256']))
        root = scan_root(Path(cast(str, self.report['root'])))
        try:
            if not source.sha256 or content_hash(root, source) != source.sha256:
                raise RiposteError('DUPLICATE_SOURCE_CHANGED')
            data = thumbnail(verify_source(root, source), media=source.media, timestamp=timestamp)
            verify_source(root, source)
            return data
        except OSError:
            raise RiposteError('DUPLICATE_SOURCE_CHANGED') from None

    def export_bytes(self, kind: str = 'json') -> bytes:
        if kind == 'json':
            return (json.dumps(self.report, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
        if kind != 'csv':
            raise RiposteError('DUPLICATE_EXPORT_FORMAT_INVALID')
        output = io.StringIO(newline='')
        fields = ['label', 'confidence', 'basis', 'member_count', 'left_path', 'right_path', 'left_count', 'right_count', 'id']
        writer = csv.writer(output, quoting=csv.QUOTE_ALL)
        writer.writerow(fields)
        for row in self.rows:
            values = []
            for key in fields:
                text = str(row[key])
                values.append("'" + text if text.lstrip().startswith(('=', '+', '-', '@', '\t', '\r', '\n')) else text)
            writer.writerow(values)
        return output.getvalue().encode('utf-8-sig')

    def export(self, target: Path) -> dict[str, object]:
        target = target.expanduser().absolute()
        if not target.parent.is_dir() or (target.exists() and is_link(target)) or any(is_link(parent) for parent in target.parents):
            raise RiposteError('DUPLICATE_REPORT_PATH_INVALID')
        data = self.export_bytes(target.suffix.lower().removeprefix('.'))
        try:
            with target.open('xb') as stream:
                stream.write(data)
        except FileExistsError:
            raise RiposteError('DUPLICATE_REPORT_EXISTS') from None
        except OSError:
            raise RiposteError('DUPLICATE_REPORT_WRITE_FAILED') from None
        return {'path': str(target), 'bytes': len(data), 'format': target.suffix[1:].lower(), 'scan_id': self.report['scan_id']}
