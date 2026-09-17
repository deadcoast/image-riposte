"""Execute shipping review handlers with controlled network and image decode timing."""
from pathlib import Path
import os
import shutil
import subprocess

import pytest


@pytest.mark.parametrize('scenario', [
    'approval_waits_for_decode',
    'failed_image_blocks_approval',
    'failed_decode_blocks_approval',
    'new_review_clears_old_pixels',
    'superseded_load_cannot_authorize',
    'original_pixels_required',
    'cached_preview_is_revalidated',
    'closed_review_cannot_submit',
    'native_close_cancels_review',
    'duplicate_decisions_blocked',
    'old_decision_keeps_new_review_open',
    'failed_decision_can_retry',
    'rejection_without_images',
    'same_path_load_race',
    'late_decode_keeps_current_image',
    'fresh_urls_are_released',
    'acknowledgements_required',
    'stale_receipt_is_not_success',
    'old_workshop_keeps_new_review_open',
    'workshop_handoff',
    'native_browser',
])
def test_browser_review(scenario):
    node = shutil.which('node')
    if node is None:
        pytest.skip('Node is required to execute the browser JavaScript')
    browser = None
    if scenario == 'native_browser':
        candidates = [
            os.environ.get('RIPOSTE_TEST_BROWSER', ''),
            shutil.which('chromium') or shutil.which('google-chrome') or '',
            'C:/Program Files/Google/Chrome/Application/chrome.exe',
            'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
        ]
        browser = next((name for name in candidates if name and Path(name).is_file()), None)
        if browser is None:
            pytest.skip('A local Chromium browser is required for native DOM verification')
    script = Path(__file__).with_name('browser_review.cjs')
    result = subprocess.run([node, str(script), scenario, *([browser] if browser else [])],
                            capture_output=True, text=True, encoding='utf-8', timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == 'PASS ' + scenario, 'scenario did not finish'
