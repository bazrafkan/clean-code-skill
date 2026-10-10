"""Create one fresh workspace per (task, condition, repetition) and write the exact prompts.

Usage: python setup_runs.py <runs_dir>
"""

import hashlib
import json
import shutil
import sys
from pathlib import Path

from config import CONDITIONS, REPETITIONS, SKILL_DIR, TASKS_DIR, build_prompt


def snapshot_skill(runs_dir):
    """Freeze the skill under test so every with-skill run reads the same version."""
    target = runs_dir / "_skill" / "clean-code"
    shutil.copytree(SKILL_DIR, target)
    digest = hashlib.sha256()
    for path in sorted(target.rglob("*.md")):
        digest.update(path.read_bytes())
    return target, digest.hexdigest()[:16]


def create_workspaces(runs_dir, skill_dir):
    prompts = {}
    for task_dir in sorted(TASKS_DIR.iterdir()):
        task_text = (task_dir / "task.md").read_text()
        for condition in CONDITIONS:
            for rep in range(1, REPETITIONS + 1):
                run_id = f"{task_dir.name}/{condition}/r{rep}"
                workdir = runs_dir / run_id
                shutil.copytree(task_dir / "starter", workdir)
                prompts[run_id] = build_prompt(task_text, workdir, condition, skill_dir)
    return prompts


def main():
    runs_dir = Path(sys.argv[1]).resolve()
    if runs_dir.exists():
        sys.exit(f"{runs_dir} already exists; refusing to overwrite runs")
    runs_dir.mkdir(parents=True)
    skill_dir, skill_hash = snapshot_skill(runs_dir)
    prompts = create_workspaces(runs_dir, skill_dir)
    (runs_dir / "prompts.json").write_text(json.dumps(prompts, indent=2))
    (runs_dir / "skill_version.txt").write_text(skill_hash + "\n")
    print(f"{len(prompts)} workspaces created; skill snapshot {skill_hash}")


if __name__ == "__main__":
    main()
