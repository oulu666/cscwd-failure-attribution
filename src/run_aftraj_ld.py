"""Optional LD runner: DeepSeek-chat step-by-step with first-Yes early stop.

This script is not needed for the three offline reproduction commands. It is
included so the decoupled control can be regenerated from user-supplied AFTraj
inputs. No credentials are stored in this repository. Provide the key through
the environment variable named by --key-env (default: MODEL_KEY).
"""

import argparse
import concurrent.futures as cf
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "prompts"))
import prompts as P  # noqa: E402
from guard import parse_yes  # noqa: E402


class Trace:
    def __init__(self, row):
        self.id = row["id"]
        self.question = row["question"]
        self.history = row["history"]
        self.n_steps = len(self.history)
        self.metadata = {"system": row.get("system"),
                         "task_id": row.get("task_id")}


def usage_dict(payload):
    usage = payload.get("usage") or {}
    return {
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "total_tokens": usage.get("total_tokens"),
    }


def call(base_url, key, model, prompt, max_tokens=256):
    url = base_url.rstrip("/") + "/chat/completions"
    body = json.dumps({
        "model": model,
        "temperature": 0,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": "Return only the requested output."},
            {"role": "user", "content": prompt},
        ],
    }).encode("utf-8")
    started = time.perf_counter()
    last = None
    for attempt in range(2):
        request = urllib.request.Request(
            url, data=body, method="POST",
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + key})
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
            text = payload["choices"][0]["message"].get("content") or ""
            return text, attempt + 1, usage_dict(payload), time.perf_counter() - started
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            last = "HTTP %s: %s" % (exc.code, detail[:500])
            low = last.lower()
            if exc.code == 402 or "quota" in low or "insufficient" in low:
                raise SystemExit("stopping on quota/402: " + last)
        except Exception as exc:
            last = "%s: %s" % (type(exc).__name__, exc)
        time.sleep(1 + attempt)
    raise RuntimeError(last)


def process(row, base_url, key, model):
    trace = Trace(row)
    ledger = []
    step = None
    yes_steps = []
    parse_errors = 0
    for index in range(trace.n_steps):
        prompt = P.step_prompt(trace, index)
        yes = None
        try:
            raw, attempts, usage, latency = call(base_url, key, model, prompt)
            yes = parse_yes(raw)
            if yes:
                yes_steps.append(index)
            if yes is None:
                parse_errors += 1
            ledger.append({"id": trace.id, "action": "LD", "step": index,
                           "requests": attempts, "latency_s": round(latency, 3),
                           "prompt_chars": len(prompt), **usage})
        except Exception as exc:
            parse_errors += 1
            ledger.append({"id": trace.id, "action": "LD", "step": index,
                           "requests": 2, "latency_s": 0.0,
                           "prompt_chars": len(prompt), "error": str(exc),
                           "prompt_tokens": None, "completion_tokens": None,
                           "total_tokens": None})
        if yes:
            step = index
            break
    record = {
        "id": trace.id,
        "system": trace.metadata["system"],
        "task_id": trace.metadata["task_id"],
        "no_gt": True,
        "step": step,
        "agent": trace.history[step]["agent"] if step is not None else None,
        "yes_steps": yes_steps,
        "parse_errors": parse_errors,
        "n_calls": len(ledger),
    }
    return record, ledger


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", default=str(ROOT / "inputs/test80_inputs.jsonl"),
                        help="AFTraj test80 inputs obtained from the upstream release")
    parser.add_argument("--out", default=str(ROOT / "decoupled/test80_ld_predictions.reproduced.jsonl"))
    parser.add_argument("--ledger", default=str(ROOT / "decoupled/test80_ld_cost_ledger.reproduced.jsonl"))
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--base-url", default="https://api.deepseek.com/v1")
    parser.add_argument("--key-env", default="MODEL_KEY",
                        help="name of the environment variable holding the key")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()

    input_path = Path(args.inputs)
    rows = [json.loads(line) for line in
            input_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.limit:
        rows = rows[:args.limit]
    print(json.dumps({"inputs": len(rows), "execute": args.execute,
                      "model": args.model, "mode": "first-Yes early stop"},
                     ensure_ascii=False))
    if not args.execute:
        return

    key = os.environ.get(args.key_env, "").strip()
    if not key:
        raise SystemExit("no key in environment variable " + args.key_env)

    out = Path(args.out)
    done = set()
    if out.exists():
        done = {json.loads(line)["id"] for line in
                out.read_text(encoding="utf-8").splitlines() if line.strip()}
    pending = [row for row in rows if row["id"] not in done]
    with out.open("a", encoding="utf-8") as out_handle, \
            Path(args.ledger).open("a", encoding="utf-8") as ledger_handle:
        with cf.ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures = {pool.submit(process, row, args.base_url, key, args.model): row
                       for row in pending}
            for index, future in enumerate(cf.as_completed(futures), 1):
                row = futures[future]
                record, ledger = future.result()
                for entry in ledger:
                    ledger_handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
                ledger_handle.flush()
                out_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                out_handle.flush()
                print(index, len(pending), row["id"], record["step"],
                      record["n_calls"], flush=True)


if __name__ == "__main__":
    main()
