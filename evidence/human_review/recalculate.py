"""Recompute the paper's human-review denominators and same-case method scores.

Reads the human-only ratings.csv and the derived ratings_with_decoupled.csv.
The script verifies that every original field is byte-identical between them
before scoring; LD/DS2 are frozen model predictions, not human labels.
"""
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
with (HERE / 'ratings.csv').open(encoding='utf-8-sig', newline='') as handle:
    base_rows = list(csv.DictReader(handle))
with (HERE / 'ratings_with_decoupled.csv').open(encoding='utf-8-sig', newline='') as handle:
    rows = list(csv.DictReader(handle))
assert len(base_rows) == len(rows) == 40
assert len({r['case_id'] for r in rows}) == len(rows) == 40
for before, after in zip(base_rows, rows):
    for field, value in before.items():
        assert after[field] == value, (before['case_id'], field)
for row in rows:
    has_disagreement = (row['A_step'], row['A_unknown']) != (row['B_step'], row['B_unknown'])
    assert bool(row['C_unknown']) == has_disagreement
    source = 'C' if has_disagreement else 'A'
    for field in ['unknown', 'step']:
        assert row[f'final_{field}'] == row[f'{source}_{field}']
both = [r for r in rows if r['A_unknown'] == r['B_unknown'] == '0']
assert len(both) == 20 and sum(r['A_step'] == r['B_step'] for r in both) == 16
assert sum(r['A_unknown'] == r['B_unknown'] for r in rows) == 38
known = [r for r in rows if r['final_unknown'] == '0']
print('localized:', len(known), '/ 40; blank LD proposals in this subset:',
      sum(not r['LD'] for r in known))
for name, group in [('all', rows), ('no worked example', [r for r in rows if r['known_assisted']=='0']), ('no earlier discussion', [r for r in rows if r['previous_chat_discussion']=='0'])]:
    assigned = [r for r in group if r['final_step']]
    print(name, 'assigned / total:', len(assigned), '/', len(group), 'released-label matches:', sum(r['final_step']==r['released_step'] for r in assigned))
for method in ['LQ','GQ','GD','V3','Band64','maj4','gd_supported','LD','DS2']:
    print(method, 'released / human hits on same subset:', *(sum(r[method]==r[target] for r in known) for target in ['released_step','final_step']))
for target in ['released_step','final_step']:
    fixed = sum(r['DS2']==r[target] and r['GD']!=r[target] for r in known)
    broken = sum(r['GD']==r[target] and r['DS2']!=r[target] for r in known)
    print('DS2 vs GD on', target, 'fixed / broken / net:', fixed, broken, fixed-broken)
