"""Actual Windows organization and mutation controls; synthetic files only."""
import json
import os
from pathlib import Path
import sys
import tempfile
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from PIL import Image
from riposte.organizer import organize
from riposte.policy import Policy
from riposte.store import catalog, record_image


def probe():
    results = []
    with tempfile.TemporaryDirectory(dir='typing/.cache/development-repairs') as folder:
        for mode in ['immediate', 'dated', 'replace', 'write_restore_mtime']:
            root = Path(folder) / mode
            root.mkdir()
            source = root / 'input.png'
            Image.new('RGB', (64, 48), (30, 90, 150)).save(source)
            if mode == 'dated':
                os.utime(source, (1725984000, 1725984000))

            def commit(*args, **kwargs):
                row = record_image(*args, **kwargs)
                before = source.stat()
                time.sleep(.03)
                if mode == 'replace':
                    replacement = root / 'replacement.png'
                    replacement.write_bytes(source.read_bytes())
                    os.replace(replacement, source)
                elif mode == 'write_restore_mtime':
                    data = bytearray(source.read_bytes())
                    data[-1] ^= 1
                    source.write_bytes(data)
                os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns))
                return row

            if mode in ('immediate', 'dated'):
                checkpoints = [organize(root, Policy(date_mode='modified'))['checkpoint'] for _ in range(3)]
                assert checkpoints == ['COMPLETE'] * 3
                assert not source.exists() and len(catalog(root)) == 1
            else:
                with patch('riposte.organizer.record_image', commit):
                    result = organize(root, Policy(date_mode='modified'))
                assert result['checkpoint'] == 'INCOMPLETE'
                assert result['blockers']['SOURCE_CHANGED_OUTPUT_RETAINED'] == 1
                assert source.exists()
            results.append({'case': mode, 'result': 'PASS'})
    return {'python': sys.version, 'platform': sys.platform, 'cases': results}


if __name__ == '__main__':
    print(json.dumps(probe(), indent=2))
