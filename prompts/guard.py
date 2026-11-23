"""Leakage guards for prompts, features, and prediction records."""
from __future__ import annotations

import re

GT_MARKER = "The Answer for the problem is:"
FORBIDDEN_FEATURE = re.compile(
    r"(^|_)(gold|ok|default_correct|mistake|ground_truth|label|y)(_|$)", re.I)
YES_RE = re.compile(r"(?:^|\n)\s*(?:1\.\s*)?(Yes|No)\b", re.I)


def parse_yes(raw):
    """Return True/False for a parsed Yes/No, or None when no answer is found."""
    match = YES_RE.search(raw or "")
    if not match:
        match = re.search(r"\b(Yes|No)\b", raw or "", re.I)
    return match.group(1).lower() == "yes" if match else None


def source_text(trace_input):
    return (trace_input.question + "\n" +
            "\n".join(e["content"] for e in trace_input.history)).lower()


def assert_prompt_clean(prompt, label=None, trace_input=None):
    if GT_MARKER in prompt:
        raise AssertionError("GT marker found in prompt")
    if label is not None and label.gold_reason and len(label.gold_reason) >= 30:
        if label.gold_reason.lower() in prompt.lower():
            raise AssertionError(f"mistake_reason leaked for {label.id}")
    if label is not None and label.ground_truth and len(label.ground_truth) >= 6:
        src = source_text(trace_input).lower() if trace_input is not None else ""
        gt = label.ground_truth.lower()
        if gt in prompt.lower() and gt not in src:
            raise AssertionError(f"ground_truth leaked for {label.id}")
    return True


def assert_features_clean(feature_names):
    bad = [f for f in feature_names if FORBIDDEN_FEATURE.search(f)]
    if bad:
        raise AssertionError(f"forbidden feature names: {bad}")
    return True


def assert_prediction_clean(record):
    bad = [k for k in ("gold", "gold_step", "gold_agent", "mistake_step",
                       "mistake_reason", "ground_truth", "default_correct", "ok")
           if k in record]
    if bad:
        raise AssertionError(f"label fields in prediction: {bad}")
    return True
