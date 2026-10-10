# A/B test of the clean-code skill

This test measures whether the `clean-code` skill improves the code an AI agent writes, and what it costs in tokens and time. The comparison is with versus without the skill, with blind judging.

- `PLAN.md`: the pre-registered design, measures and decision rules.
- `tasks/`: six Python tasks (small, medium, large). Each has a starter project, the task text, hidden tests and a reference solution.
- `harness/`: scripts to create the runs, grade them, build blind judging packets and aggregate the results.
- `results/`: raw run outputs, costs, grades, judgments and `REPORT.md`. Added after the runs.
