# A/B test plan (pre-registered)

This plan, the tasks, the hidden tests and the harness were committed **before any run**. The results in `results/` must be read against this plan, not against decisions made afterwards.

## Question

Does the `clean-code` skill make an AI coding agent produce better code, and at what extra cost?

## Design

**Tasks.** There are six Python tasks at three complexity levels. Each has a starter project, a task text, hidden tests and a reference solution.

| Task | Level | Kind |
|---|---|---|
| `s1-pagination-bugfix` | small | Fix two bugs, add validation |
| `s2-temperature-trap` | small | Tiny new function; a **trap** where patterns or classes are unnecessary |
| `m1-pricing-gold-tier` | medium | Add a feature to messy legacy code without changing existing behavior |
| `m2-rate-limiter` | medium | New module with an injectable clock (testability) |
| `l1-notifications` | large | Multi-part service: channels, retries, fallback, templates |
| `l2-report-refactor` | large | Refactor duplicated legacy code and add a format, keeping output byte-identical |

**Conditions.**
- `with_skill`: the agent reads a frozen snapshot of `clean-code/SKILL.md` first, plus the references when the skill says to.
- `without_skill`: no skill.

**Prompt.** Both conditions get exactly the same prompt, apart from the lines that tell the agent to read the skill (see `harness/config.py`). The prompt contains only the task and housekeeping. It does not tell the agent to write tests or to refactor.

**Isolation.**
- Every run is a fresh agent with a fresh copy of the starter.
- Both conditions are told not to use the Skill tool. The skill is installed in the account, and this prevents the baseline from loading it by itself.
- The model is the same for every run. Runs of both conditions are launched together.

**Repetitions.** There are 3 repetitions per task and condition: 36 runs and 18 with/without pairs. A pair is the with-skill run and the without-skill run with the same repetition number.

## Measures

**Primary outcome: blind pairwise preference (overall).**
- Each pair is judged by independent judge agents that see only the task text and the two code diffs.
- Judges never see the agents' messages or summaries.
- Each pair is judged twice, in both presentation orders, by different judge agents.
- A pair counts as a win for one condition only when both orders agree. Any disagreement counts as a tie.
- Judges are not told that a skill exists. Paths, run names and mentions of the skill or the books are redacted equally on both sides.

**Guardrail: correctness.** This is the share of hidden tests passed. The agents never see the hidden tests. The skill must not lower the mean pass rate by more than 5 percentage points.

**Secondary outcomes.**
- Judgments per criterion: readability, design, robustness, tests, scope.
- Static metrics:
  - production and test lines of code
  - longest function, cyclomatic complexity (radon), maximum parameters
  - linter findings (ruff, rules `E,W,F,B,SIM,C901,N,RET,PLR`)
  - number of classes
  - diff size
- Tests in the project after the change.
- On the trap task: production size and number of classes (over-engineering).

**Cost.**
- Tokens processed by the agent, wall time and tool calls, as reported by the agent runner.
- Reported as absolute values and as the with/without ratio, plus extra tokens per decisive win.

## Decision rules (fixed in advance)

- **The skill helps:**
  - the with-skill win share among decisive pairs is above 50%,
  - the lower bound of its 95% Wilson interval is above 50%,
  - and the guardrail holds.
- **The skill hurts:** the upper bound of that interval is below 50%, or the guardrail fails.
- **Otherwise the result is inconclusive.**
- Results are also reported by complexity level. Those subgroups are too small to be decisive and are only descriptive.
- Whether the cost is worth it is left to the reader. The report shows both numbers side by side.

## Known limitations

- **Small sample.** With 18 pairs, only a large effect can reach significance. For example, 14 wins out of 18 decisive pairs is needed for the Wilson lower bound to exceed 50%.
- **Narrow scope.** Python only, one model, synthetic tasks of limited size. The results may not transfer to other languages or to large real codebases.
- **Judge bias.** The judges are LLMs of the same family as the coding agent. Blinding and order swapping reduce, but do not remove, judge bias.
- **Author bias.** The tasks were written by the same assistant that wrote the skill. Hidden tests, pre-registration and blind judging are the mitigations.
- **Triggering is not tested.** The skill is loaded explicitly. Whether it triggers automatically is a separate question.

## Reproduce

```bash
cd ab-test/harness
python setup_runs.py <runs_dir>                      # creates workspaces + prompts.json
# run one fresh agent per entry in prompts.json; record tokens, duration_ms and tool_uses in costs.json
python grade.py <runs_dir> ../tasks <out>/grades.json
python make_packets.py <runs_dir> <packets_dir> <key.json> <seed>
# run one blind judge agent per packet (each writes <packet>.judgment.json)
python aggregate.py <out>/grades.json <costs.json> <packets_dir> <key.json> <out>
```

`grade.py` expects each `tasks/<task>/` to contain `hidden_tests/` and `reference/`.
