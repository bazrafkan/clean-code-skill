# A/B test of the clean-code skill

This test measures whether the `clean-code` skill improves the code an AI agent writes, and what it costs in tokens and time. The comparison is with versus without the skill, with blind judging. It ran in two rounds.

- `PLAN.md`: the pre-registered design, measures and decision rules for round 1 (skill v1).
- `PLAN-round2.md`: the plan for round 2 (skill v2, two holdout tasks, a fresh baseline).
- `PREREG-MANIFEST.txt`: SHA-256 of every round-2 file, fixed before the round-2 runs. To check it, run `sha256sum -c --ignore-missing ab-test/PREREG-MANIFEST.txt` from the repository root. This README was edited after the runs, so its line is expected to fail.
- `tasks/`: eight Python tasks, each with a starter project, the task text, hidden tests and a reference solution. The six `s*`, `m*` and `l*` tasks are used in both rounds; `h1` and `h2` are the round-2 holdout tasks.
- `harness/`: scripts to create the runs, grade them, build blind judging packets and aggregate the results.
- `results/`: round 1. Raw run outputs, costs, grades, judgments and `REPORT.md`.
- `results-round2/`: round 2, with the same layout.

## Results (2026-10-10)

**Round 1, skill v1: inconclusive on quality, clearly more expensive.**
- **Quality:** in blind review the skill won 6 pairs and lost 8, with 4 ties.
- **Correctness:** identical, 100% on the hidden tests.
- **Better with the skill:** tests, function length and complexity.
- **Worse with the skill:** larger changes (scope 0–11).
- **Cost:** +44% tokens, about 2.7× wall time.

**Round 2, skill v2: helps under the pre-registered rule, at a lower cost.**
- **Quality:** 14 wins, 3 losses, 7 ties. Win share 82%, 95% CI 59–94%.
- **Holdout tasks:** 5–0–1.
- **Correctness:** identical, 100% on the hidden tests.
- **Better with the skill:** readability 14–0, design 10–0, scope 11–3, tests 12–5.
- **Worse with the skill:** robustness 0–8.
- **Cost:** +16% tokens, about 1.5× wall time.
- **Caveat:** in 4 pairs the baseline wrote no tests. Without those pairs the result is 10–3–7, which is not decisive.

Details, deviations and limitations are in `results/REPORT.md` and `results-round2/REPORT.md`.
