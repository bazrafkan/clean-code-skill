"""Objective grading of every run: hidden tests, the agent's own tests, static metrics, diff size.

Usage: python grade.py <runs_dir> <hidden_dir> <out_json>
"""

import ast
import json
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from config import CONDITIONS, IGNORED_NAMES, REPETITIONS, TASKS_DIR

RUFF_RULES = "E,W,F,B,SIM,C901,N,RET,PLR"


def is_ignored(path, root):
    return any(part in IGNORED_NAMES for part in path.relative_to(root).parts)


def python_files(root):
    return [p for p in sorted(root.rglob("*.py")) if not is_ignored(p, root)]


def is_test_file(path, root):
    rel = path.relative_to(root)
    return rel.parts[0] == "tests" or path.name.startswith("test_") or path.name == "conftest.py"


def run_pytest(workdir, target, timeout=120):
    """Run pytest on target inside workdir and return (passed, failed, errors, collected)."""
    with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as report:
        report_path = report.name
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "-o", "addopts=", f"--junitxml={report_path}", target]
    try:
        subprocess.run(cmd, cwd=workdir, capture_output=True, timeout=timeout)
        suite = ET.parse(report_path).getroot()
        suite = suite if suite.tag == "testsuite" else suite.find("testsuite")
        total, failures, errors, skipped = (int(suite.get(k, 0)) for k in ("tests", "failures", "errors", "skipped"))
        return {"passed": total - failures - errors - skipped, "failed": failures, "errors": errors, "collected": total}
    except (subprocess.TimeoutExpired, ET.ParseError, FileNotFoundError):
        return {"passed": 0, "failed": 0, "errors": 1, "collected": 0}


def hidden_test_results(workdir, hidden_tests):
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "ws"
        shutil.copytree(workdir, copy, ignore=shutil.ignore_patterns(*IGNORED_NAMES))
        shutil.copytree(hidden_tests, copy / "_hidden_tests")
        return run_pytest(copy, "_hidden_tests")


def own_test_results(workdir):
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "ws"
        shutil.copytree(workdir, copy, ignore=shutil.ignore_patterns(*IGNORED_NAMES))
        return run_pytest(copy, ".")


def sloc_and_comments(source):
    code = comments = 0
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            comments += 1
        else:
            code += 1
            if "#" in stripped:
                comments += 1
    return code, comments


def function_stats(tree):
    functions = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    lengths = [n.end_lineno - n.lineno + 1 for n in functions]
    params = [len(n.args.args) + len(n.args.kwonlyargs) - (1 if n.args.args and n.args.args[0].arg in ("self", "cls") else 0) for n in functions]
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    return functions, lengths, params, classes


def cyclomatic(paths):
    if not paths:
        return []
    out = subprocess.run([sys.executable, "-m", "radon", "cc", "-j", *map(str, paths)], capture_output=True, text=True)
    blocks = json.loads(out.stdout or "{}")
    return [b["complexity"] for items in blocks.values() if isinstance(items, list) for b in items]


def ruff_findings(paths):
    if not paths:
        return {}
    out = subprocess.run(
        ["ruff", "check", "--isolated", "--line-length", "120", "--select", RUFF_RULES, "--output-format", "json", *map(str, paths)],
        capture_output=True,
        text=True,
    )
    counts = {}
    for finding in json.loads(out.stdout or "[]"):
        counts[finding["code"]] = counts.get(finding["code"], 0) + 1
    return counts


def diff_stats(starter, workdir):
    out = subprocess.run(
        ["diff", "-ruN", *sum((["-x", name] for name in IGNORED_NAMES), []), str(starter), str(workdir)],
        capture_output=True,
        text=True,
    )
    added = removed = 0
    files = set()
    for line in out.stdout.splitlines():
        if line.startswith("+++ "):
            files.add(line[4:].split("\t")[0])
        elif line.startswith("+") and not line.startswith("+++"):
            added += 1
        elif line.startswith("-") and not line.startswith("---"):
            removed += 1
    return {"lines_added": added, "lines_removed": removed, "files_changed": len(files)}


def static_metrics(workdir):
    prod = [p for p in python_files(workdir) if not is_test_file(p, workdir)]
    tests = [p for p in python_files(workdir) if is_test_file(p, workdir) and p.name != "conftest.py"]
    prod_sloc = prod_comments = test_sloc = 0
    lengths, params, n_functions, n_classes = [], [], 0, 0
    for path in prod:
        source = path.read_text()
        code, comments = sloc_and_comments(source)
        prod_sloc += code
        prod_comments += comments
        functions, f_lengths, f_params, classes = function_stats(ast.parse(source))
        lengths += f_lengths
        params += f_params
        n_functions += len(functions)
        n_classes += len(classes)
    for path in tests:
        test_sloc += sloc_and_comments(path.read_text())[0]
    complexity = cyclomatic(prod)
    ruff = ruff_findings(prod)
    return {
        "prod_sloc": prod_sloc,
        "prod_comment_lines": prod_comments,
        "test_sloc": test_sloc,
        "functions": n_functions,
        "classes": n_classes,
        "max_function_lines": max(lengths, default=0),
        "mean_function_lines": round(sum(lengths) / len(lengths), 2) if lengths else 0,
        "max_params": max(params, default=0),
        "max_complexity": max(complexity, default=0),
        "mean_complexity": round(sum(complexity) / len(complexity), 2) if complexity else 0,
        "ruff_findings": sum(ruff.values()),
        "ruff_by_rule": ruff,
    }


def expected_hidden_count(task_dir, hidden_dir):
    """Number of hidden tests, measured on the reference solution (the pass-rate denominator)."""
    with tempfile.TemporaryDirectory() as tmp:
        reference = Path(tmp) / "ref"
        shutil.copytree(task_dir / "starter", reference)
        shutil.copytree(hidden_dir / task_dir.name / "reference", reference, dirs_exist_ok=True)
        result = hidden_test_results(reference, hidden_dir / task_dir.name / "hidden_tests")
    if result["passed"] != result["collected"]:
        sys.exit(f"reference solution fails hidden tests for {task_dir.name}: {result}")
    return result["collected"]


def main():
    runs_dir, hidden_dir, out_json = (Path(a).resolve() for a in sys.argv[1:4])
    results = {}
    for task_dir in sorted(TASKS_DIR.iterdir()):
        task = task_dir.name
        expected = expected_hidden_count(task_dir, hidden_dir)
        for condition in CONDITIONS:
            for rep in range(1, REPETITIONS + 1):
                run_id = f"{task}/{condition}/r{rep}"
                workdir = runs_dir / run_id
                hidden = hidden_test_results(workdir, hidden_dir / task / "hidden_tests")
                own = own_test_results(workdir)
                results[run_id] = {
                    "task": task,
                    "condition": condition,
                    "rep": rep,
                    "hidden": hidden,
                    "hidden_expected": expected,
                    "hidden_pass_rate": round(hidden["passed"] / expected, 4),
                    "own_tests": own,
                    "summary_written": (workdir / "SUMMARY.md").exists(),
                    **static_metrics(workdir),
                    **diff_stats(task_dir / "starter", workdir),
                }
                print(run_id, results[run_id]["hidden_pass_rate"], results[run_id]["prod_sloc"])
    Path(out_json).write_text(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
