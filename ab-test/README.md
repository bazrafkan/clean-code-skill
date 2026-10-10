# A/B test of the clean-code skill

This test measures whether the `clean-code` skill improves the code an AI agent writes, and what it costs in tokens and time. The comparison is with versus without the skill, with blind judging.

- `PLAN.md`: the pre-registered design, measures and decision rules.
- `tasks/`: six Python tasks (small, medium, large). Each has a starter project, the task text, hidden tests and a reference solution.
- `harness/`: scripts to create the runs, grade them, build blind judging packets and aggregate the results.
- `results/`: raw run outputs, costs, grades, judgments and `REPORT.md`. Added after the runs.

## Result (2026-10-10)

The quality result is inconclusive, and the skill costs clearly more:
- **Quality:** in blind review the skill won 6 pairs and lost 8, with 4 ties.
- **Correctness:** identical, 100% on the hidden tests in both conditions.
- **Better with the skill:** tests, function length and complexity.
- **Worse with the skill:** larger changes (scope 0–11).
- **Cost:** +44% tokens and about 2.7× wall time.

Details, deviations and limitations are in `results/REPORT.md`.
