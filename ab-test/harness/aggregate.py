"""Combine objective grades, costs and blind judgments into summary statistics and tables.

Usage: python aggregate.py <grades_json> <costs_json> <packets_dir> <key_json> <out_dir>
"""

import json
import math
import statistics
import sys
from pathlib import Path

from config import COMPLEXITY, HOLDOUT_PREFIX, REPETITIONS

CRITERIA = ("overall", "readability", "design", "robustness", "tests", "scope")
METRICS = [
    ("hidden_pass_rate", "Hidden tests passed (share)", "higher"),
    ("own_tests_collected", "Tests written/kept by the agent", "info"),
    ("prod_sloc", "Production lines of code", "info"),
    ("test_sloc", "Test lines of code", "info"),
    ("classes", "Classes", "info"),
    ("max_function_lines", "Longest function (lines)", "lower"),
    ("max_complexity", "Max cyclomatic complexity", "lower"),
    ("mean_complexity", "Mean cyclomatic complexity", "lower"),
    ("max_params", "Max parameters", "lower"),
    ("ruff_findings", "Linter findings", "lower"),
    ("diff_lines", "Diff size (lines added + removed)", "info"),
    ("tokens", "Tokens used", "lower"),
    ("duration_s", "Wall time (s)", "lower"),
    ("tool_uses", "Tool calls", "lower"),
]


def mean_sd(values):
    if not values:
        return float("nan"), float("nan")
    return statistics.fmean(values), (statistics.stdev(values) if len(values) > 1 else 0.0)


def wilson(successes, n, z=1.96):
    if n == 0:
        return float("nan"), float("nan")
    p = successes / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / (1 + z * z / n)
    return centre - half, centre + half


def sign_test_p(wins, losses):
    """Two-sided exact binomial test of wins vs losses (ties excluded)."""
    n = wins + losses
    if n == 0:
        return 1.0
    k = min(wins, losses)
    tail = sum(math.comb(n, i) for i in range(k + 1)) / 2**n
    return min(1.0, 2 * tail)


def load_rows(grades, costs):
    rows = {}
    for run_id, grade in grades.items():
        cost = costs[run_id]
        rows[run_id] = {
            **grade,
            "own_tests_collected": grade["own_tests"]["collected"],
            "diff_lines": grade["lines_added"] + grade["lines_removed"],
            "tokens": cost["tokens"],
            "duration_s": cost["duration_ms"] / 1000,
            "tool_uses": cost["tool_uses"],
        }
    return rows


def metric_table(rows, tasks):
    table = {}
    for task in tasks + ["ALL"]:
        table[task] = {}
        for key, _, _ in METRICS:
            per_condition = {}
            for condition in ("with_skill", "without_skill"):
                values = [r[key] for r in rows.values() if r["condition"] == condition and task in ("ALL", r["task"])]
                per_condition[condition] = mean_sd(values)
            table[task][key] = per_condition
    return table


def combine(first, second):
    """Combine the verdicts of the two presentation orders for one pair."""
    if first == second:
        return first
    if "tie" in (first, second):
        return "lean_" + (first if second == "tie" else second)
    return "inconsistent"


def judgments(packets_dir, key):
    verdicts = {}
    raw = {c: {"with_skill": 0, "without_skill": 0, "tie": 0} for c in CRITERIA}
    for name, mapping in key.items():
        task, order = name.rsplit("__order", 1)
        data = json.loads((packets_dir / f"{name}.judgment.json").read_text())
        for pair in data["pairs"]:
            rep = str(pair["pair"])
            for criterion in CRITERIA:
                choice = pair[criterion]
                condition = "tie" if choice == "tie" else mapping[rep][choice]
                raw[criterion][condition] += 1
                verdicts.setdefault((task, rep, criterion), {})[order] = condition
            verdicts.setdefault((task, rep, "reason"), {})[order] = (pair.get("confidence"), pair.get("reason"))
    combined = {}
    for (task, rep, criterion), by_order in verdicts.items():
        if criterion != "reason":
            combined[(task, rep, criterion)] = combine(by_order["1"], by_order["2"])
    return combined, raw, verdicts


def win_summary(combined, criterion, tasks):
    outcomes = [v for (t, _, c), v in combined.items() if c == criterion and t in tasks]
    wins, losses = outcomes.count("with_skill"), outcomes.count("without_skill")
    ties = len(outcomes) - wins - losses
    low, high = wilson(wins, wins + losses)
    return {
        "pairs": len(outcomes),
        "with_skill_wins": wins,
        "without_skill_wins": losses,
        "ties_or_inconsistent": ties,
        "lean_with": outcomes.count("lean_with_skill"),
        "lean_without": outcomes.count("lean_without_skill"),
        "inconsistent": outcomes.count("inconsistent"),
        "win_share_decisive": wins / (wins + losses) if wins + losses else float("nan"),
        "wilson95": [low, high],
        "sign_test_p": sign_test_p(wins, losses),
    }


def fmt(value, digits=2):
    return "n/a" if isinstance(value, float) and math.isnan(value) else f"{value:.{digits}f}"


def render_tables(table, tasks, wins_by_scope, raw):
    lines = ["## Objective metrics (mean ± sd over repetitions)", ""]
    for task in tasks + ["ALL"]:
        label = task if task == "ALL" else f"{task} ({COMPLEXITY[task]})"
        lines += [f"### {label}", "", "| Metric | With skill | Without skill | Better |", "|---|---|---|---|"]
        for key, title, direction in METRICS:
            (w_mean, w_sd), (o_mean, o_sd) = table[task][key]["with_skill"], table[task][key]["without_skill"]
            better = ""
            if direction != "info" and not math.isnan(w_mean) and abs(w_mean - o_mean) > 1e-9:
                with_better = (w_mean > o_mean) == (direction == "higher")
                better = "with" if with_better else "without"
            lines.append(f"| {title} | {fmt(w_mean)} ± {fmt(w_sd)} | {fmt(o_mean)} ± {fmt(o_sd)} | {better} |")
        lines.append("")
    lines += ["## Blind pairwise judgments", "", "A pair counts as a win only when both presentation orders agree.", ""]
    lines += ["| Scope | Criterion | Pairs | With wins | Without wins | Ties/split | Win share (decisive) | 95% CI | Sign test p |", "|---|---|---|---|---|---|---|---|---|"]
    for scope, by_criterion in wins_by_scope.items():
        for criterion, s in by_criterion.items():
            lines.append(
                f"| {scope} | {criterion} | {s['pairs']} | {s['with_skill_wins']} | {s['without_skill_wins']} | "
                f"{s['ties_or_inconsistent']} | {fmt(s['win_share_decisive'])} | {fmt(s['wilson95'][0])}–{fmt(s['wilson95'][1])} | {fmt(s['sign_test_p'], 3)} |"
            )
    lines += ["", "Raw single judgments (each pair judged twice, once per order):", "", "| Criterion | With | Without | Tie |", "|---|---|---|---|"]
    for criterion, counts in raw.items():
        lines.append(f"| {criterion} | {counts['with_skill']} | {counts['without_skill']} | {counts['tie']} |")
    return "\n".join(lines) + "\n"


def main():
    grades_json, costs_json, packets_dir, key_json, out_dir = (Path(a).resolve() for a in sys.argv[1:6])
    rows = load_rows(json.loads(grades_json.read_text()), json.loads(costs_json.read_text()))
    key = json.loads(key_json.read_text())["key"]
    tasks = sorted({r["task"] for r in rows.values()})
    table = metric_table(rows, tasks)
    combined, raw, verdicts = judgments(packets_dir, key)
    scopes = {"ALL": tasks, **{level: [t for t in tasks if COMPLEXITY[t] == level] for level in ("small", "medium", "large")}}
    scopes["seen"] = [t for t in tasks if not t.startswith(HOLDOUT_PREFIX)]
    scopes["holdout"] = [t for t in tasks if t.startswith(HOLDOUT_PREFIX)]
    wins_by_scope = {
        scope: {c: win_summary(combined, c, scope_tasks) for c in (CRITERIA if scope == "ALL" else ("overall",))}
        for scope, scope_tasks in scopes.items()
    }
    wins_by_task = {t: win_summary(combined, "overall", [t]) for t in tasks}
    out_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "metrics": {t: {k: {c: list(v) for c, v in m.items()} for k, m in by.items()} for t, by in table.items()},
        "wins": wins_by_scope,
        "wins_by_task": wins_by_task,
        "raw_judgments": raw,
        "pair_verdicts": {f"{t}/r{r}/{c}": v for (t, r, c), v in combined.items()},
        "judge_reasons": {f"{t}/r{r}": v for (t, r, c), v in verdicts.items() if c == "reason"},
        "repetitions": REPETITIONS,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2))
    (out_dir / "tables.md").write_text(render_tables(table, tasks, wins_by_scope, raw))
    print((out_dir / "tables.md").read_text())


if __name__ == "__main__":
    main()
