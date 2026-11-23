"""Offline checks for the AFTraj test. Run with Python 3 after extracting the archive."""
import csv
import json
from pathlib import Path

root = Path(__file__).resolve().parent
split = root / 'split'

def read_csv(name):
    with (split / name).open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))

def read_jsonl(name):
    return [json.loads(line) for line in (split / name).read_text(encoding='utf-8').splitlines()]

rows = read_csv('test80_score_rows.csv')
test = read_csv('test80.csv')
contacted = read_csv('contacted_tasks.csv')
assert len(rows) == len({r['task_sha256'] for r in test}) == 80
assert {r['trace_id'] for r in test} == {r['id'] for r in rows}
assert not ({r['task_sha256'] for r in test} & {r['task_sha256'] for r in contacted})
pred = {r['id']:r['predictions'] for r in read_jsonl('test80_view_predictions.jsonl')}
for r in rows:
    for view in ('GD','GQ','LQ','late_q'):
        assert (int(r[view]) if r[view] else None) == pred[r['id']][view]['step']
hits = {m:sum(r[m] == r['gold'] for r in rows) for m in ('GD','GQ','LQ','V3','Band64','maj4','gd_supported')}
covered = [r for r in rows if r['gold'] in [r[m] for m in ('GD','GQ','LQ','late_q')]]
omissions = [r for r in rows if r not in covered]
assert (hits['GD'],hits['V3'],len(covered),len(omissions)) == (51,46,61,19)
assert sum(int(r['gold']) in pred[r['id']]['LQ']['yes_steps'] for r in omissions) == 8
print('Exact hits:',hits,'Covered:',len(covered),'Omitted:',len(omissions))
ledger = read_jsonl('test80_cost_ledger.jsonl')
stopped = []
for r in ledger:
    positive = pred[r['id']]['LQ']['yes_steps']
    if r['action'] != 'LQ' or not positive or int(r['step']) <= min(positive):
        stopped.append(r)
for name, group, expected in [('full',ledger,(1202,1580200)),('offline early stop',stopped,(510,341725)),('GD',[r for r in ledger if r['action']=='GD'],(80,81953))]:
    totals = (sum(r['requests'] for r in group),sum(r['prompt_tokens'] for r in group))
    assert totals == expected
    print(name,'requests and input tokens:',totals)

