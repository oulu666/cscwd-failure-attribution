# Failure Attribution in Collaborative Multi-Agent Workflows

Companion artifact for the CSCWD 2027 submission *Diagnosing Failure Attribution in Collaborative Multi-Agent Workflows: Coverage, Selection, and Resource Cost*.

The artifact contains the frozen test80 evidence, the anonymous human label audit, and the decoupled model–view control reported in supplement S9. It does **not** contain raw upstream trajectories, credentials, or reviewer identities.

## Manuscript and workflow figure

Read the [revised six-page manuscript](cscwd2027_paper.pdf) alongside the [supplement](supplement_cscwd.pdf). The manuscript cites commit `418f94f` for the frozen experimental evidence. Figure 1 is available as an [editable SVG](figures/fig1.svg) and a [vector PDF](figures/fig1.pdf).

## Scope and claim boundaries

- AFTraj `mistake_step` labels are multi-LLM-judge labels, not human labels. The human review is a 40-trace label audit; 21 traces were localized and form the sensitivity subset.
- Test80 was used for the reported model and view comparisons. The decoupled control in `decoupled/` reuses test80 and is a robustness analysis, not a new untouched test.
- The supported result is a negative one: within the tested Qwen and DeepSeek aliases, whole-trace views exceed step-by-step views, and multi-view voting does not reliably improve on the best whole-trace single view.
- No raw `Who&When`, `TraceElephant`, or `AFTraj-2K` trajectories are redistributed. Only trace IDs, task hashes, frozen predictions, labels, and per-request ledgers are included.

## Quick start: three offline reproduction commands

Requires Python 3.7 or newer. These commands use only the standard library and the files in this repository; they make no network calls.

```bash
python verify_test.py
```

```bash
python evidence/human_review/recalculate.py
```

```bash
python audit/audit_decoupled_models.py
```

The first command verifies the test80/dev20 blacklist split, coverage, early-stop replay, and ledger totals. The second recomputes the 40-trace human audit, the 21-trace subset, and the LD/DS2 scores. The third recomputes all ten decoupled methods from the frozen ledgers and checks them against `decoupled/decoupled_models.json`.

## Repository layout

```
.
├── README.md
├── LICENSE
├── .gitignore
├── supplement_cscwd.pdf
├── verify_test.py
├── prompts/
│   ├── prompts.py
│   └── guard.py
├── split/
│   ├── test80.csv
│   ├── dev20.csv
│   ├── contacted_tasks.csv
│   ├── frozen_configs.json
│   ├── test80_view_predictions.jsonl
│   ├── test80_score_rows.csv
│   ├── test80_cost_ledger.jsonl
│   ├── early_stop_rows.csv
│   ├── early_stop_check.json
│   ├── gold_visibility.csv
│   └── gold_visibility_summary.json
├── evidence/human_review/
│   ├── README.md
│   ├── recalculate.py
│   ├── ratings.csv
│   ├── ratings_with_decoupled.csv
│   ├── decoupled_human_subset.json
│   └── sampling_protocol.md
├── decoupled/
│   ├── DECOUPLED_MODELS_PROTOCOL.md
│   ├── decoupled_models.md
│   ├── decoupled_models.json
│   ├── test80_ld_predictions.jsonl
│   └── test80_ld_cost_ledger.jsonl
├── audit/
│   └── audit_decoupled_models.py
└── src/
    └── run_aftraj_ld.py
```

`evidence/human_review/ratings.csv` contains human fields only and uses anonymous reviewer identifiers A, B, and C. `ratings_with_decoupled.csv` appends the frozen LD and DS2 predictions; `recalculate.py` verifies that every original field is unchanged before scoring.

## Upstream data

Obtain the original trajectories from the official releases; this repository intentionally does not redistribute them.

- **AFTraj-2K / AgentForesight**: Zhang et al., *AgentForesight*, arXiv:2605.08715. Use the official AFTraj-2K release to reconstruct inputs from the trace IDs and task hashes in `split/`.
- **Who&When**: Cemri et al., *Why Do Multi-Agent LLM Systems Fail?*, NeurIPS 2024. Use the official Who&When release.
- **TraceElephant**: use the official release cited in the manuscript.

`split/test80.csv` and `split/dev20.csv` contain trace IDs and task hashes, not trajectory text. `split/contacted_tasks.csv` is the 53-task blacklist used to show that test80 is disjoint from previously contacted tasks.

## Key numbers

- Test80: GD 51/80, V3 46/80, maj4 47/80, gd_supported 48/80; four-view coverage 61/80.
- Decoupled control: Qwen step 30 vs Qwen whole 42; DeepSeek step (LD) 18 vs DeepSeek whole (GD) 51. LD returned no proposal on 33/80 traces; with a proposal it is 18/47. DS2 ties GD at 51/80 (6 fixed, 6 broken, p = 1.0) at 548 requests versus 80.
- Human audit: 40 sampled traces, 21 localized. LD scores 3/21 against released labels and 5/21 against the combined human step; DS2 scores 8/21 and 9/21; GD scores 9/21 and 8/21. The DS2-versus-GD paired changes are 1 fixed / 2 broken on released labels and 2 fixed / 1 broken on human steps.

These are the numbers implemented by the three commands above. They should not be read as prevalence estimates or as evidence of a positive intervention.

## Optional online LD regeneration

`src/run_aftraj_ld.py` is optional and is not needed for the three offline commands. It uses only the standard library and regenerates the DeepSeek step-by-step control from user-supplied AFTraj inputs:

```bash
python src/run_aftraj_ld.py --inputs /path/to/test80_inputs.jsonl --execute
```

Provide the credential through the environment variable named by `--key-env` (default `MODEL_KEY`). The repository stores no key and no `.env` file. Defaults write `*.reproduced.jsonl` files under `decoupled/`, so the frozen artifacts are not overwritten.

## License

Code is released under the MIT License; see `LICENSE`. The manuscript and supplement are provided for review and reuse with attribution. Upstream datasets remain under their original licenses.
