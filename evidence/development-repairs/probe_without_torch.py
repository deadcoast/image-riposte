"""Simulate an unavailable Torch import without changing either uv environment."""
import importlib.abc
import sys


class MissingTorch(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == 'torch' or fullname.startswith('torch.'):
            raise ModuleNotFoundError("Torch intentionally unavailable in this coverage probe", name='torch')
        return None


if __name__ == '__main__':
    assert 'torch' not in sys.modules
    sys.meta_path.insert(0, MissingTorch())
    import pytest
    raise SystemExit(pytest.main([
        'tests/test_v03_publication.py', 'tests/test_v03_api_cli.py',
        'tests/test_development_repairs.py', '-q', '-ra',
        '--basetemp=typing/.cache/development-repairs/no-torch',
        '-o', 'cache_dir=typing/.cache/development-repairs/pytest-cache',
        '--junitxml=evidence/development-repairs/no-torch.xml',
    ]))
