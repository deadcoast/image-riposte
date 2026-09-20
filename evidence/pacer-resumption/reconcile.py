"""Submit reviewed inventory batches through PACER's guarded Service, never CSV writes.

Pass the installed plugin source directory and a reviewed operation file. New
assets are registered before their dependency edges so each <=200-row transaction
is structurally complete. Receipts and command outcomes are retained in .tmp.
"""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pacer-source', type=Path, required=True)
    parser.add_argument('--operations', type=Path, required=True)
    parser.add_argument('--task', default='PAC-044')
    parser.add_argument('--inventory', action='store_true')
    args = parser.parse_args()
    sys.path.insert(0, str(args.pacer_source))
    from pacer_mcp.service import Service
    service = Service(ROOT)
    operations = json.loads(args.operations.read_text(encoding='utf-8-sig'))
    if args.inventory:
        additions, changes = [], []
        for operation in operations:
            if operation['op'] == 'add':
                row = dict(operation['row'])
                edges = row.pop('Requires', '')
                additions.append({**operation, 'row': row})
                if edges:
                    changes.append({'op': 'set', 'id': row['ID'], 'fields': {'Requires': edges}})
            else:
                assert operation['op'] == 'set', operation
                changes.append(operation)
        batches = [additions[i:i+200] for i in range(0, len(additions), 200)]
        batches += [changes[i:i+200] for i in range(0, len(changes), 200)]
    else:
        assert len(operations) <= 200
        batches = [operations]
    receipt_folder = ROOT / '.tmp/pacer-resumption'
    receipt_folder.mkdir(parents=True, exist_ok=True)
    for number, batch in enumerate(batches):
        if not batch: continue
        onboard = service.onboard()
        context = service.context(args.task, max_bytes=1_000_000)
        assert context['complete']
        (receipt_folder / 'context.json').write_text(json.dumps(context, indent=2) + '\n')
        result = service.apply(batch, actor='codex', revision=onboard['revision'],
                               onboarding=onboard['onboarding'], context=context['receipt'])
        record = {'operations': batch, 'result': result}
        (receipt_folder / f'{args.operations.stem}-{number:03}.json').write_text(json.dumps(record, indent=2) + '\n')
        print(json.dumps({'batch': number, 'operations': len(batch), 'revision': result['revision'],
                          'validation': result['validation']}), flush=True)


if __name__ == '__main__':
    main()
