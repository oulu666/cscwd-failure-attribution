"""Gold-free prompt builders for the official and all-at-once protocols."""
from __future__ import annotations

import hashlib

try:
    from .guard import assert_prompt_clean
except ImportError:
    from guard import assert_prompt_clean

STEP_SYSTEM = ("You are an AI assistant tasked with evaluating the correctness of each step "
               "in an ongoing multi-agent conversation aimed at solving a real-world problem.")


def prefix_upto(trace_input, upto, per_step_chars=None, max_chars=None):
    """Chronological prefix; when budget is tight, keep the current step first."""
    if not max_chars:
        return "".join(
            f"Step {i} - {e['agent']}: "
            f"{str(e['content'])[:per_step_chars] if per_step_chars else e['content']}\n"
            for i, e in enumerate(trace_input.history[:upto]))
    entries = []
    used = 0
    for i in range(upto - 1, -1, -1):
        e = trace_input.history[i]
        content = str(e["content"])
        if per_step_chars:
            content = content[:per_step_chars]
        remaining = max_chars - used
        if remaining <= 0:
            break
        content = content[:remaining]
        entries.append((i, e["agent"], content))
        used += len(content)
        if used >= max_chars:
            break
    entries.reverse()
    return "".join(f"Step {i} - {agent}: {content}\n"
                   for i, agent, content in entries)


def step_prompt(trace_input, idx, variant="official", per_step_chars=None,
                max_chars=None):
    prefix = prefix_upto(trace_input, idx + 1, per_step_chars=per_step_chars,
                        max_chars=max_chars)
    agent = trace_input.history[idx]["agent"]
    if variant == "decisive":
        task = (
            "Your task is to determine whether this most recent agent's action "
            f"(Step {idx}) is the earliest decisive error that caused the multi-agent system to fail. "
            "A step is decisive only if correcting it would change the final outcome. "
            "Do not flag a step merely because it is imperfect, incomplete, or could be improved. "
            "If the current step is an early plan or intermediate result and the actual faulty "
            "execution or verification happens later, answer 'No'. "
            "Please respond with 'Yes' or 'No' and provide a clear explanation for your judgment. ")
    else:
        task = (
            "Your task is to determine whether this most recent agent's action "
            f"(Step {idx}) contains an error that could hinder the problem-solving process or lead to an incorrect solution. "
            "Please respond with 'Yes' or 'No' and provide a clear explanation for your judgment. "
            "Note: Please avoid being overly critical in your evaluation. Focus on errors that clearly derail the process.")
    prompt = (
        f"{STEP_SYSTEM} The problem being addressed is: {trace_input.question}. "
        f"Here is the conversation history up to the current step:\n{prefix}\n"
        f"The most recent step ({idx}) was by '{agent}'.\n"
        f"{task}"
        "Respond ONLY in the format: 1. Yes/No.\n2. Reason: [Your explanation here]")
    assert_prompt_clean(prompt, trace_input=trace_input)
    return prompt


def render_trajectory(trace_input, max_chars=24000, start_ratio=0.0,
                      per_step_chars=1200):
    history = trace_input.history
    start = max(0, min(len(history) - 1, int(len(history) * start_ratio)))
    note = (f"\nOnly the late window (global steps {start}-{len(history)-1}) is shown; "
            f"earlier steps are omitted. Return the GLOBAL step index.\n"
            if start > 0 else "")
    lines = []
    used = 0
    for i, e in enumerate(history[start:], start=start):
        content = str(e["content"])
        if per_step_chars:
            content = content[:per_step_chars]
        if max_chars:
            remaining = max_chars - used
            if remaining <= 0:
                break
            content = content[:remaining]
        lines.append(f"Step {i} - {e['agent']}: {content}")
        used += len(content)
        if max_chars and used >= max_chars:
            break
    return note + "\n".join(lines)


def render_slice(trace_input, start, end, max_chars=8000, per_step_chars=1200):
    lines = []
    used = 0
    for i, e in enumerate(trace_input.history[start:end], start=start):
        content = str(e["content"])
        if per_step_chars:
            content = content[:per_step_chars]
        if max_chars:
            remaining = max_chars - used
            if remaining <= 0:
                break
            content = content[:remaining]
        lines.append(f"Step {i} - {e['agent']}: {content}")
        used += len(content)
        if max_chars and used >= max_chars:
            break
    return "\n".join(lines)


def all_prompt(trace_input, max_chars=24000, start_ratio=0.0,
               per_step_chars=1200):
    traj = render_trajectory(trace_input, max_chars=max_chars,
                             start_ratio=start_ratio,
                             per_step_chars=per_step_chars)
    prompt = f"""You are auditing a failed multi-agent trajectory.

Task:
{trace_input.question[:4000]}

Trajectory:
{traj}

The system produced a wrong final answer. Identify the single earliest step whose error is decisive: correcting that step would change the final outcome. Do not choose a step merely because it is imperfect or appears early. If an early plan is reasonable but a later execution or verification is faulty, choose the later step.

Return ONLY JSON:
{{"step": <int>, "agent": "<agent name>", "reason": "<one sentence>"}}"""
    assert_prompt_clean(prompt, trace_input=trace_input)
    return prompt


def late_prompt(trace_input, max_chars=24000, start_ratio=0.5,
                per_step_chars=1200):
    return all_prompt(trace_input, max_chars=max_chars, start_ratio=start_ratio,
                      per_step_chars=per_step_chars)


def chunk_prompt(trace_input, start, end, max_chars=8000, per_step_chars=1200):
    """Ask for the decisive step inside a global-index window [start, end)."""
    traj = render_slice(trace_input, start, end, max_chars=max_chars,
                        per_step_chars=per_step_chars)
    prompt = f"""You are auditing a failed multi-agent trajectory.

Task:
{trace_input.question[:4000]}

Trajectory window (global steps {start}-{end - 1}):
{traj}

The system produced a wrong final answer. Identify the single earliest step
within this window whose error is decisive: correcting that step would change
the final outcome. If no step in this window is decisive, return null for step.

Return ONLY JSON:
{{"step": <global int or null>, "agent": "<agent name>", "reason": "<one sentence>"}}"""
    assert_prompt_clean(prompt, trace_input=trace_input)
    return prompt


def prompt_hash(prompt):
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()
