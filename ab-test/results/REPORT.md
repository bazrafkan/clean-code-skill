# A/B test report: clean-code skill

Run on 2026-10-10, with skill snapshot `7def5b27731d6954` (the compact `SKILL.md` plus two reference files). The design, the tasks, the hidden tests and the decision rules were committed before any run, in commit `0a8510d` of the repository (see `../PLAN.md`). That commit comes before the results commit in the history. Its timestamp is local to the author's machine, so it cannot be verified independently.

## Bottom line

**Inconclusive on quality, clearly more expensive.**
- **Overall quality:** in blind pairwise review the skill won 6 pairs and lost 8, with 4 ties. That is a 43% win share, 95% CI 21–67%. Under the pre-registered rule, this is *inconclusive*: there is no evidence the skill improves overall code quality on these tasks.
- **Correctness:** identical. All 36 runs passed 100% of the hidden tests.
- **Where the skill helps:**
  - More tests. Judges leaned towards the skill's tests 7–2, which is not significant.
  - Shorter functions and lower complexity on average.
- **Where it hurts:**
  - Bigger changes. Reviewers preferred the baseline on scope 11–0 (p = 0.001).
  - Leaning worse on design (1–5), mainly through extra abstractions and unrequested robustness.
- **Cost:**
  - +44% tokens, about 38k extra tokens per task.
  - About 2.7× wall time on average (3.7× by median).
  - About 2.3× tool calls.

Whether the cost is worth it is the reader's call (as fixed in the plan). For scale: the skill used 692k extra tokens in total, for 6 decisive wins and 8 decisive losses.

## Setup in one paragraph

There were six Python tasks:
- two small: a bug fix, and a trap task where patterns or classes are unnecessary
- two medium: a feature in messy legacy code, and a module with an injectable clock
- two large: a multi-part service, and a refactor plus a new format with byte-identical output

Each task ran 3 times with the skill and 3 times without, giving 36 fresh agents on the same model. The prompts were identical except for the lines that load the skill. Both conditions were told not to use the Skill tool, because the skill is installed in the account. Each workspace had a neutral random name.

Correctness was measured with hidden tests that the agents never saw. Quality was judged by independent agents. Each judge saw only the task and two anonymized diffs, did not know a skill existed, and judged each pair in both presentation orders. A pair counts as a win only if both orders agree.

## Results

### Correctness (guardrail)

| | With skill | Without skill |
|---|---|---|
| Hidden tests passed | 100% (36/36 runs fully green) | 100% |

The guardrail holds. There is also a ceiling effect: the tasks did not separate the two conditions on correctness.

### Blind pairwise judgments (primary outcome)

| Scope | Criterion | With wins | Without wins | Ties / split | Win share | 95% CI | Sign-test p |
|---|---|---|---|---|---|---|---|
| All 18 pairs | **overall** | 6 | 8 | 4 | 0.43 | 0.21–0.67 | 0.79 |
| | readability | 3 | 4 | 11 | 0.43 | 0.16–0.75 | 1.00 |
| | design | 1 | 5 | 12 | 0.17 | 0.03–0.56 | 0.22 |
| | robustness | 4 | 6 | 8 | 0.40 | 0.17–0.69 | 0.75 |
| | tests | 7 | 2 | 9 | 0.78 | 0.45–0.94 | 0.18 |
| | **scope** | 0 | 11 | 7 | 0.00 | 0.00–0.26 | **0.001** |
| Small (6 pairs) | overall | 2 | 3 | 1 | | | |
| Medium (6 pairs) | overall | 3 | 2 | 1 | | | |
| Large (6 pairs) | overall | 1 | 3 | 2 | | | |

Overall winner for each task (3 pairs each):

| Task | With | Without | Tie / split |
|---|---|---|---|
| s1 pagination bug fix | 0 | 2 | 1 |
| s2 temperature (trap) | 2 | 1 | 0 |
| m1 gold tier in legacy code | **2** | 0 | 1 |
| m2 rate limiter | 1 | 2 | 0 |
| l1 notification service | 0 | **3** | 0 |
| l2 report refactor | 1 | 0 | 2 |

### Objective metrics (mean over 18 runs per condition)

| Metric | With skill | Without skill |
|---|---|---|
| Tests in the project after the change | 23.6 | 19.6 |
| Test lines of code | 113 | 79 |
| Production lines of code | 99 | 83 |
| Classes | 3.4 | 2.3 |
| Longest function (lines) | **16.9** | 20.3 |
| Mean cyclomatic complexity | **2.02** | 2.38 |
| Max cyclomatic complexity | **3.8** | 4.6 |
| Linter findings (ruff) | 0.17 | 0.28 |
| Diff size (lines added + removed) | 313 | 244 |

Per-task tables with standard deviations are in `tables.md`.

### Cost

| Level | Tokens with | Tokens without | Ratio | Extra tokens per task |
|---|---|---|---|---|
| Small | 98.8k | 78.2k | 1.26 | +20.6k |
| Medium | 126.3k | 85.7k | 1.47 | +40.6k |
| Large | 153.9k | 99.8k | 1.54 | +54.1k |
| **All** | **126.3k** | **87.9k** | **1.44** | **+38.5k** |

- **Wall time:** mean 416 s vs 154 s (2.7×), median 451 s vs 122 s (3.7×).
- **Tool calls:** mean 26 vs 11.5 (2.3×).
- **What the token figures include:** both conditions carry the agent's fixed overhead (system prompt and tool definitions). For scale, a judge agent that only read one file of about 7k tokens used about 87k tokens (see `judge_costs.json`). That fixed overhead is why the ratio understates the relative increase in the agent's own work.
- **Wall time is noisy**, because the runs shared one machine in parallel.

## What the skill actually changes (from the diffs and the judges' reasons)

- **Tests.** With the skill, agents wrote more tests: 23.6 vs 19.6 per run on average, and 113 vs 79 test lines. In one baseline run (m2 r2) the agent wrote no tests at all. Judges favored the skill on tests 7–2. This is the skill's clearest benefit, but it is not statistically significant.
- **Smaller functions, lower complexity.** This holds in aggregate but not in every task. Max complexity is worse with the skill in l2 and s1, and the longest function is worse in m2.
- **Restructuring.** In m1 (legacy pricing), both conditions merged the duplicated `if t == 2` logic into one shared calculation. All three skill runs used a tier table, which follows the skill's "restructure before adding a variant" rule. The skill versions won 2–0, and the judges mostly cited their stronger regression tests.
- **Trap task (s2).** With the skill, the production code was larger: 46 vs 37 lines, and 1.0 vs 0.33 classes per run. That is a mild over-engineering signal. Even so, the judges gave the trap task 2–1 to the skill.
- **More scope and more machinery.** The baseline won on scope in every decisive pair. Judges repeatedly named extra things the task did not ask for:
  - logging
  - `_Route` abstractions
  - generic `Protocol` typing
  - exact `Fraction` arithmetic and NaN/inf checks for a temperature conversion
  - a `DEFAULT_PER_PAGE` constant
  - row validation

  This is not one-sided. In m2 the judges credited the baseline with robustness: thread safety and rejecting an infinite rate.

  The skill warns against over-engineering, but its "make it right" and "be precise" pressure seems to push agents past what the task needs.
- **Much longer runs, cause not measured.** Two things contribute, but neither was measured per tool:
  - Reading the skill: `SKILL.md` is about 3.5k tokens, and the references are about 6k and 11k tokens when they are read.
  - Running checks: the skill's verify step. Several with-skill agents reported running tools the projects never configured, such as mypy, pyright, black and flake8. These reports come from the agents' end-of-run summaries, which are not stored here. One leftover `.mypy_cache` confirms at least one such run.

## Decision (pre-registered rule)

- **Win share 43%, CI 21–67%, which includes 50%: inconclusive.**
- **The guardrail holds** (correctness unchanged).
- **The cost is clearly higher.**

The honest summary: on these tasks the skill buys better tests and simpler functions, at about +44% tokens and about 2.7× time. Blind reviewers did not prefer its output overall, mainly because its changes are larger than needed.

## Deviations from the plan

1. **Neutral workspace names.** These were added after the pre-registration commit and before any run, so agents could not infer their condition from the path. This change only strengthens the blinding.
2. **`SUMMARY.md`.** The agent runtime usually blocks subagents from writing report files, so most agents returned their summary as text instead. Three with-skill runs (l2 r3, s2 r1, s2 r2) did write `SUMMARY.md`, and no baseline run did. Summaries were never part of the evaluation: they are excluded from the diffs and the metrics.
3. **Judges answered in text.** They returned their JSON as a reply instead of writing a file, for the same reason. The orchestrator saved each reply verbatim to `judging/*.judgment.json`.
4. **`.mypy_cache` in one diff.** The ignore list missed `.mypy_cache`, so one with-skill run (s1 r1) left mypy cache files in its diff, and both judges mentioned them.
   - Both judges also cited an unneeded constant, so the cache may not have decided the pair.
   - Worst case: counting that pair as a with-skill win instead of a loss gives 7–7 (CI 0.27–0.73). That is still inconclusive, so the conclusion does not change.
   - The cache files are visible in `judging/s1-*` and are excluded from `runs/`.

## Limitations

- **Small sample.** With 18 pairs, only a large effect could reach significance.
- **Correctness ceiling.** Every run passed every hidden test, so correctness could not separate the conditions.
- **Narrow scope.** Python only, one model, synthetic tasks. These are small, well-specified tasks, where a strong model already writes reasonable code without help. The skill may matter more in large, messy, real codebases or with weaker models. This test cannot show that.
- **Judge bias.** The judges are LLMs of the same family. Blinding and order swapping reduce this bias, but do not remove it.
- **Author bias.** The tasks were written by the same assistant that wrote the skill. Pre-registration, hidden tests and blind judging are the mitigations.
- **Triggering not tested.** Automatic triggering of the skill was not tested; it was loaded explicitly.

## Hypotheses for a next round (post-hoc, to be tested, not concluded)

1. **Tighten scope.** Make "the smallest diff that satisfies the task" an explicit top rule. Add robustness the spec does not ask for (thread safety, NaN, type checks, logging) only when asked.
2. **Verify with the project's tools only.** Run the project's configured checks, not every tool available. This should cut time and tool calls.
3. **Keep the testing guidance.** It produced the clearest benefit.
4. **Possible effect by task type.** The skill may help most when changing messy legacy code (m1: 2–0) and least on greenfield designs (l1: 0–3).

## Files

- `runs/<task>/<condition>/r<n>/`: the code each agent left (caches removed).
- `prompts.json`, `workspace_map.json`, `skill_version.txt`: exact prompts and the skill snapshot used.
- `grades.json`: hidden-test results, the agents' own tests, static metrics and diff sizes per run.
- `costs.json`: tokens, wall time and tool calls per run, as reported by the agent runner. `judge_costs.json` has the same figures for the judge agents.
- `judging/*.md`: the blind packets. `judging/*.judgment.json`: the judges' answers. `judging/key.json`: the de-blinding key.
- `summary.json`, `tables.md`: aggregated statistics, produced by `harness/aggregate.py`.
