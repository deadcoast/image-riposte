"""Retain PAC-042 intake and pre-change search reproduction."""
from pathlib import Path
import json
import shutil
import tempfile
from PIL import Image
from riposte.organizer import organize, plan
from riposte.policy import Policy
from riposte.terminal.service import select_rows
from riposte.sort_titles import title_records

HERE = Path(__file__).parent
shutil.copyfile('typing/evidence/source-reviewed-workspace-health.json', HERE/'source-before.json')
with tempfile.TemporaryDirectory(prefix='riposte-search-baseline-') as temp:
    root = Path(temp)
    Image.new('RGB', (32, 32)).save(root/'private-moonlight-sketch.png')
    policy = Policy(date_mode='modified')
    organize(root, policy, plan_id=plan(root, policy)['plan_id'])
    result = {'baseline': 'Ordinary list search omits private original titles',
              'query': 'moonlight', 'canonical_matches': len(select_rows(root, search='moonlight')),
              'private_title_saved': title_records(root)[0]['original_filename'],
              'canonical_record_keys': list(select_rows(root)[0])}
    assert result['canonical_matches'] == 0 and result['private_title_saved'] == 'private-moonlight-sketch.png'
    (HERE/'baseline.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
