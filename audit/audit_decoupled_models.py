"""Recompute the ten decoupled methods from the frozen test80 artifacts.

Offline only: reads split/test80_score_rows.csv, decoupled/test80_ld_predictions.jsonl
and the two cost ledgers. Prints the recomputed table and checks it against
decoupled/decoupled_models.json. No network access and no model calls.
"""

import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SPLIT = ROOT / "split"
DEC = ROOT / "decoupled"


def load_jsonl(path):
    return [json.loads(line) for line in
            Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def vote(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    counts = {v: values.count(v) for v in set(values)}
    top = max(counts.values())
    return min(v for v in values if counts[v] == top)


def mcnemar(broken, fixed):
    total = broken + fixed
    if total == 0:
        return 1.0
    tail = sum(
        math.factorial(total) // (math.factorial(i) * math.factorial(total - i))
        for i in range(min(broken, fixed) + 1)
    ) / (2 ** total)
    return min(1.0, 2 * tail)


def exact(rows, field):
    return sum(1 for row in rows if row[field] == row["gold"])


def cost_of(ledger_rows, actions):
    out = {"requests": 0, "prompt_tokens": 0,
           "completion_tokens": 0, "latency_s": 0.0}
    for row in ledger_rows:
        if row.get("action") not in actions:
            continue
        out["requests"] += int(row.get("requests") or 0)
        out["prompt_tokens"] += int(row.get("prompt_tokens") or 0)
        out["completion_tokens"] += int(row.get("completion_tokens") or 0)
        out["latency_s"] += float(row.get("latency_s") or 0.0)
    out["latency_s"] = round(out["latency_s"], 3)
    return out


def add_cost(*costs):
    return {key: sum(cost[key] for cost in costs) for key in costs[0]}


def main():
    ld_rows = load_jsonl(DEC / "test80_ld_predictions.jsonl")
    ld = {row["id"]: row["step"] for row in ld_rows}
    assert len(ld) == len(ld_rows) == 80

    rows = []
    for source in csv.DictReader((SPLIT / "test80_score_rows.csv").open(encoding="utf-8")):
        def as_int(value):
            return int(value) if value not in ("", None) else None
        record = {
            "id": source["id"],
            "domain": source["domain"],
            "gold": int(source["gold"]),
            "QwenLQ": as_int(source["LQ"]),
            "GQ": as_int(source["GQ"]),
            "GD": as_int(source["GD"]),
            "late": as_int(source["late_q"]),
            "V3": as_int(source["V3"]),
            "LD": ld.get(source["id"]),
        }
        record["V2"] = vote([record["GQ"], record["GD"]])
        record["W3"] = vote([record["GQ"], record["GD"], record["late"]])
        record["DS2"] = vote([record["LD"], record["GD"]])
        record["DS3"] = vote([record["LD"], record["GQ"], record["GD"]])
        record["DS4"] = vote([record["LD"], record["GQ"], record["GD"], record["late"]])
        rows.append(record)
    assert len(rows) == 80

    methods = ("QwenLQ", "GQ", "GD", "V2", "W3", "V3", "LD", "DS2", "DS3", "DS4")
    base_ledger = load_jsonl(SPLIT / "test80_cost_ledger.jsonl")
    ld_ledger = load_jsonl(DEC / "test80_ld_cost_ledger.jsonl")
    costs = {
        "QwenLQ": cost_of(base_ledger, {"LQ"}),
        "GQ": cost_of(base_ledger, {"GQ"}),
        "GD": cost_of(base_ledger, {"GD"}),
        "LD": cost_of(ld_ledger, {"LD"}),
        "late": cost_of(base_ledger, {"late_q"}),
    }
    costs["V2"] = add_cost(costs["GQ"], costs["GD"])
    costs["W3"] = add_cost(costs["GQ"], costs["GD"], costs["late"])
    costs["V3"] = add_cost(costs["QwenLQ"], costs["GQ"], costs["GD"])
    costs["DS2"] = add_cost(costs["LD"], costs["GD"])
    costs["DS3"] = add_cost(costs["LD"], costs["GQ"], costs["GD"])
    costs["DS4"] = add_cost(costs["LD"], costs["GQ"], costs["GD"], costs["late"])

    summary = {
        "n": len(rows),
        "coverage5": sum(
            1 for row in rows
            if row["gold"] in {row[key] for key in ("QwenLQ", "LD", "GQ", "GD", "late")}
        ),
        "methods": {},
        "paired_vs_GD": {},
        "paired_vs_V3": {},
        "by_domain": {},
    }
    for method in methods:
        hits = exact(rows, method)
        summary["methods"][method] = {
            "exact": hits,
            "pct": round(100.0 * hits / len(rows), 2),
            "cost": costs[method],
            "calls_per_exact": round(costs[method]["requests"] / hits, 2) if hits else None,
        }
    for base, key in (("GD", "paired_vs_GD"), ("V3", "paired_vs_V3")):
        for method in methods:
            if method == base:
                continue
            fixed = sum(1 for row in rows
                        if row[method] == row["gold"] and row[base] != row["gold"])
            broken = sum(1 for row in rows
                         if row[method] != row["gold"] and row[base] == row["gold"])
            summary[key][method] = {
                "fixed": fixed, "broken": broken, "net": fixed - broken,
                "mcnemar_p": round(mcnemar(broken, fixed), 4),
            }
    for domain in sorted({row["domain"] for row in rows}):
        subset = [row for row in rows if row["domain"] == domain]
        summary["by_domain"][domain] = {method: exact(subset, method)
                                        for method in methods}
        summary["by_domain"][domain]["n"] = len(subset)

    print("method      exact   pct   requests  prompt_tokens  calls/exact")
    for method in methods:
        item = summary["methods"][method]
        print("%-10s %2d/80  %5.1f  %8d  %13d  %11s" % (
            method, item["exact"], item["pct"], item["cost"]["requests"],
            item["cost"]["prompt_tokens"], item["calls_per_exact"]))
    print("coverage5: %d/80" % summary["coverage5"])

    committed_path = DEC / "decoupled_models.json"
    if committed_path.exists():
        committed = json.loads(committed_path.read_text(encoding="utf-8"))
        assert committed["n"] == summary["n"]
        assert committed["coverage5"] == summary["coverage5"]
        for method in methods:
            assert committed["methods"][method]["exact"] == summary["methods"][method]["exact"]
            assert committed["methods"][method]["cost"]["requests"] == \
                summary["methods"][method]["cost"]["requests"]
            assert committed["methods"][method]["cost"]["prompt_tokens"] == \
                summary["methods"][method]["cost"]["prompt_tokens"]
        for base in ("paired_vs_GD", "paired_vs_V3"):
            for method, values in summary[base].items():
                for field in ("fixed", "broken", "net", "mcnemar_p"):
                    assert committed[base][method][field] == values[field], \
                        (base, method, field)
        print("checks against decoupled_models.json: OK")
    else:
        print("decoupled_models.json not found; printed recomputation only")


if __name__ == "__main__":
    main()
