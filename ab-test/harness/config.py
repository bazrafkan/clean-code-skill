"""Shared configuration for the A/B test harness."""

from pathlib import Path

AB_ROOT = Path(__file__).resolve().parent.parent
TASKS_DIR = AB_ROOT / "tasks"
RESULTS_DIR = AB_ROOT / "results"
SKILL_DIR = AB_ROOT.parent / "clean-code"

CONDITIONS = ("with_skill", "without_skill")
REPETITIONS = 3

COMPLEXITY = {
    "s1-pagination-bugfix": "small",
    "s2-temperature-trap": "small",
    "m1-pricing-gold-tier": "medium",
    "m2-rate-limiter": "medium",
    "l1-notifications": "large",
    "l2-report-refactor": "large",
    "h1-scheduler-monthly": "medium",
    "h2-ttl-cache": "large",
}

# Holdout tasks: written after round 1, never seen while revising the skill.
HOLDOUT_PREFIX = "h"

# Files that are never part of the judged or measured code.
IGNORED_NAMES = {"SUMMARY.md", "__pycache__", ".pytest_cache", ".ruff_cache", ".mypy_cache", ".git"}

RUN_PROMPT = """You are working on a small Python project in the directory {workdir}.
Work only inside that directory: do not read, list or modify anything outside it{skill_exception}.
{skill_line}
Task:

{task}

When you are done:
- Write the summary you would normally give the user to {workdir}/SUMMARY.md.
- Do not use the Skill tool.
- Reply with exactly one line: DONE
"""

SKILL_LINE = (
    "\nBefore you start, read {skill_dir}/SKILL.md and follow it. Its reference files are in "
    "{skill_dir}/references/; read them when SKILL.md says to.\n"
)
SKILL_EXCEPTION = " (exception: you may read the skill files in {skill_dir})"


def build_prompt(task_text, workdir, condition, skill_dir):
    """Return the exact prompt for one run. The two conditions differ only in the skill lines."""
    with_skill = condition == "with_skill"
    return RUN_PROMPT.format(
        workdir=workdir,
        task=task_text.strip(),
        skill_line=SKILL_LINE.format(skill_dir=skill_dir) if with_skill else "",
        skill_exception=SKILL_EXCEPTION.format(skill_dir=skill_dir) if with_skill else "",
    )
