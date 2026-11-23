# Anonymous human review

`ratings.csv` is the 40-trace AFTraj label audit. Reviewers are identified only as
A, B, and C. Reviewer A and Reviewer B decided independently. Reviewer C supplied
the six adjudications; rows with `final_label_source=C_adjudication` are exactly
those six cases. No reviewer name, affiliation, email address, or signature is
included.

`ratings_with_decoupled.csv` appends the frozen `LD` and `DS2` predictions. All
original human fields are copied unchanged. `recalculate.py` verifies this before
scoring.

`decoupled_human_subset.json` records the LD/DS2 scores and paired changes on the
21 traces with `final_unknown=0`.

Run from the repository root:

```bash
python evidence/human_review/recalculate.py
```
