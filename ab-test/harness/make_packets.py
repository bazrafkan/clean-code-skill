"""Build blind judging packets: one per (task, presentation order), three pairs each.

Each pair puts the with-skill and without-skill diff of the same repetition side by side as
"Implementation 1" and "Implementation 2". Order 1 uses a seeded random placement; order 2 swaps it.
Paths, run names and mentions that would reveal the condition are redacted equally on both sides.

Usage: python make_packets.py <runs_dir> <packets_dir> <key_json> <seed>
"""

import json
import random
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from config import IGNORED_NAMES, REPETITIONS, TASKS_DIR

REDACTIONS = [
    re.compile(r"\((?:\s*[CEFGJNT]\d{1,2}(?:\s*[,–-]\s*[CEFGJNT]?\d{1,2})*\s*,?)+\)"),
    re.compile(r"\b(?:clean[ -]code|gang of four|GoF|skill|with_skill|without_skill)\b", re.IGNORECASE),
]

RUBRIC = """You are reviewing two implementations of the same task, written by two different developers.
For each pair below, compare Implementation 1 and Implementation 2 on these criteria:

- readability: names, structure, how easy the code is to read
- design: decomposition and abstraction level; penalize both over-engineering and under-engineering
- robustness: error handling, edge cases, likely bugs you can see by reading
- tests: quality and relevance of tests added or changed (tie if neither adds tests)
- scope: the change is limited to what the task needs; required behavior is preserved
- overall: which one you would rather merge and maintain

Judge only what you can see in the diffs. Longer is not better: extra code, comments or abstractions
that the task does not need count against an implementation. Ties are allowed when there is no real difference.

Reply with only a JSON object (no other text, no code fence), with exactly this shape:
{{"pairs": [{{"pair": <pair number>, "readability": "1"|"2"|"tie", "design": "1"|"2"|"tie",
"robustness": "1"|"2"|"tie", "tests": "1"|"2"|"tie", "scope": "1"|"2"|"tie", "overall": "1"|"2"|"tie",
"confidence": "low"|"medium"|"high", "reason": "<at most two sentences>"}}, ...]}}

Read only this packet file. Do not look at any other file or directory, and do not write any files.
"""


def redact(text, runs_dir):
    count = text.count(str(runs_dir))
    text = text.replace(str(runs_dir), "<workspace>")
    for pattern in REDACTIONS:
        text, n = pattern.subn("[redacted]", text)
        count += n
    return text, count


def neutral_diff(starter, workdir):
    """Unified diff with neutral paths (before/ after/), so the run directory is not revealed."""
    with tempfile.TemporaryDirectory() as tmp:
        ignore = shutil.ignore_patterns(*IGNORED_NAMES)
        shutil.copytree(starter, Path(tmp) / "before", ignore=ignore)
        shutil.copytree(workdir, Path(tmp) / "after", ignore=ignore)
        out = subprocess.run(["diff", "-ruN", "before", "after"], cwd=tmp, capture_output=True, text=True)
    return re.sub(r"^((?:---|\+\+\+) \S+)\t.*$", r"\1", out.stdout, flags=re.MULTILINE)


def build_packet(task_text, pairs, output_path):
    parts = [RUBRIC.format(output_path=output_path), "## Task given to both developers\n\n" + task_text.strip()]
    for number, (first, second) in enumerate(pairs, start=1):
        parts.append(f"## Pair {number}\n\n### Implementation 1\n\n```diff\n{first}```\n\n### Implementation 2\n\n```diff\n{second}```")
    return "\n\n".join(parts) + "\n"


def main():
    runs_dir, packets_dir, key_json = (Path(a).resolve() for a in sys.argv[1:4])
    rng = random.Random(int(sys.argv[4]))
    packets_dir.mkdir(parents=True, exist_ok=True)
    key, redaction_counts = {}, {}
    for task_dir in sorted(TASKS_DIR.iterdir()):
        task = task_dir.name
        diffs = {}
        for condition in ("with_skill", "without_skill"):
            for rep in range(1, REPETITIONS + 1):
                text, count = redact(neutral_diff(task_dir / "starter", runs_dir / task / condition / f"r{rep}"), runs_dir)
                diffs[(condition, rep)] = text
                redaction_counts[f"{task}/{condition}/r{rep}"] = count
        placements = [rng.random() < 0.5 for _ in range(REPETITIONS)]
        for order in (1, 2):
            pairs, mapping = [], {}
            for rep, with_first in enumerate(placements, start=1):
                with_first = with_first if order == 1 else not with_first
                first, second = ("with_skill", "without_skill") if with_first else ("without_skill", "with_skill")
                pairs.append((diffs[(first, rep)], diffs[(second, rep)]))
                mapping[str(rep)] = {"1": first, "2": second}
            name = f"{task}__order{order}"
            output_path = packets_dir / f"{name}.judgment.json"
            (packets_dir / f"{name}.md").write_text(build_packet((task_dir / "task.md").read_text(), pairs, output_path))
            key[name] = mapping
    key_json.write_text(json.dumps({"key": key, "redactions": redaction_counts}, indent=2))
    print(f"{len(key)} packets written to {packets_dir}")


if __name__ == "__main__":
    main()
