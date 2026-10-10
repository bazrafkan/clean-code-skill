# A/B test report, round 2: clean-code skill v2

Run on 2026-10-10 with the skill v2 snapshot `9f93e108aba3c2ea` (`SKILL.md` plus the two reference files).

The design and the decision rules are in `../PLAN-round2.md`. The tasks and hidden tests are in `../tasks/`. They were fixed before the first run but not committed to git, by the user's choice. Instead, the SHA-256 of a manifest listing every file's hash (`../PREREG-MANIFEST.txt`, manifest hash `d37ef8d2…1c61548`) was sent to the user in the conversation before any run. After the runs, all 75 substantive files still matched their hashes (see deviation 1).

## Bottom line

**Under the pre-registered rule, v2 helps. It also costs much less extra than v1 did.**

- **Overall quality.** In blind pairwise review, v2 won 14 pairs and lost 3, with 7 ties.
  - Win share 82%, 95% CI 59–94%, sign test p = 0.013.
  - The lower bound is above 50%, so the pre-registered verdict is *helps*.
- **Holdout tasks** (written after v2, never used to tune it): 5 wins, 0 losses, 1 tie.
- **Seen tasks** (the six round-1 tasks v2 was tuned on): 9–3–6. On their own these are not decisive (CI 47–91%).
- **Correctness:** identical. All 48 runs passed 100% of the hidden tests.
- **Where v2 is better:** readability (14–0), design (10–0), scope (11–3), tests (12–5).
- **Where it is worse:** robustness (0–8). The baseline adds more defensive handling, such as locks, float tolerance, and type and empty-value checks. Judges credited that under robustness, but usually counted it against scope.
- **Cost:**

  | | v2 vs its baseline | v1 vs its baseline (round 1) |
  |---|---|---|
  | Tokens | +16% (+14k per task) | +44% |
  | Wall time (mean) | 1.5× | 2.7× |
  | Tool calls | 1.5× | 2.3× |

- **Main caveat: tests.** In 4 of the 24 pairs, the baseline agent wrote no tests at all. Every v2 run wrote tests, and all 4 of those pairs went to v2.
  - Leaving those 4 pairs out (a post-hoc check) gives 10–3–7: win share 77%, CI 49.7–91.8%, p = 0.09. Under the pre-registered rule, that subset alone would be *inconclusive*.
  - So part of v2's advantage is simply that it always writes tests.

## What changed from v1 to v2

v2 keeps v1's structure and rules (about 3.9k tokens instead of 3.5k). It acts on the round-1 hypotheses:

- **Smallest change first.** "The smallest change that fully solves the task" is now:
  - in the opening line
  - second in the precedence list, right after correctness
  - first in the checklist
- **No speculative extras.** v2 says to handle what the task states or its domain clearly implies. Nothing else gets added: no unrequested validation, thread safety, NaN or type checks, logging, options, constants, abstractions, generic typing or new files. Such ideas go in the report instead.
- **Bounded "make it right".** It applies only to the code the agent wrote or touched.
- **The project's own checks only.** Run what the project already configures, and leave no caches behind.
- **Testing guidance.** Before changing untested legacy code, add tests that capture its current behavior. New behavior and fixed bugs ship with a test, and tests stay focused on what the task changed. The rest of the testing rules are unchanged.
- **References are rarely needed.** The skill now says most tasks don't need its reference files.

## Setup

Round 2 used the same design as round 1:
- the same prompt template and Python tasks
- fresh agents on the same model, with neutral workspace names
- both conditions told not to use the Skill tool
- hidden tests the agents never saw
- blind judges who saw only the rubric, the task and the anonymized diffs of three pairs, in both presentation orders. A pair is a win only if both orders agree.

Two things are new:
- **Holdout tasks.** Two tasks were written after v2 and never used to tune it:
  - `h1-scheduler-monthly` (medium): add a schedule kind to legacy code that has a repeated switch, keeping existing behavior.
  - `h2-ttl-cache` (large): a greenfield LRU cache with expiry, statistics and a memoizing decorator.
- **A fresh baseline.** The baseline runs were done in the same session as the v2 runs, not reused from round 1.

In total: 8 tasks × 2 conditions × 3 repetitions = 48 runs and 24 pairs, judged by 16 judge agents. The packet seed was 7342, fixed in the plan.

## Results

### Correctness (guardrail)

| | v2 | Baseline |
|---|---|---|
| Hidden tests passed | 100% (24/24 runs fully green) | 100% (24/24) |

The guardrail holds. As in round 1, correctness hit its ceiling and could not separate the two conditions.

### Blind pairwise judgments (primary outcome)

| Scope | Criterion | v2 wins | Baseline wins | Ties / split | Win share | 95% CI | Sign-test p |
|---|---|---|---|---|---|---|---|
| All 24 pairs | **overall** | **14** | 3 | 7 | **0.82** | **0.59–0.94** | **0.013** |
| | readability | 14 | 0 | 10 | 1.00 | 0.78–1.00 | <0.001 |
| | design | 10 | 0 | 14 | 1.00 | 0.72–1.00 | 0.002 |
| | robustness | 0 | 8 | 16 | 0.00 | 0.00–0.32 | 0.008 |
| | tests | 12 | 5 | 7 | 0.71 | 0.47–0.87 | 0.14 |
| | scope | 11 | 3 | 10 | 0.79 | 0.52–0.92 | 0.057 |
| Seen tasks (18 pairs) | overall | 9 | 3 | 6 | 0.75 | 0.47–0.91 | 0.15 |
| Holdout (6 pairs) | overall | 5 | 0 | 1 | 1.00 | 0.57–1.00 | 0.062 |
| Small (6 pairs) | overall | 2 | 3 | 1 | | | |
| Medium (9 pairs) | overall | 5 | 0 | 4 | | | |
| Large (9 pairs) | overall | 7 | 0 | 2 | | | |

Counting the 48 single judgments instead of pairs, the overall verdict went to v2 35 times, to the baseline 12 times, and 1 was a tie.

Overall winner for each task (3 pairs each), with round 1 for comparison:

| Task | v2 – baseline – tie (round 2) | v1 – baseline – tie (round 1) |
|---|---|---|
| s1 pagination bug fix | 1–2–0 | 0–2–1 |
| s2 temperature (trap) | 1–1–1 | 2–1–0 |
| m1 gold tier in legacy code | 0–0–3 | 2–0–1 |
| m2 rate limiter | 2–0–1 | 1–2–0 |
| l1 notification service | 2–0–1 | 0–3–0 |
| l2 report refactor | 3–0–0 | 1–0–2 |
| h1 monthly schedule (holdout) | 3–0–0 | – |
| h2 TTL cache (holdout) | 2–0–1 | – |

### Objective metrics (mean over 24 runs per condition)

| Metric | v2 | Baseline |
|---|---|---|
| Tests in the project after the change | 20.3 | 16.5 |
| Test lines of code | 95 | 76 |
| Production lines of code | **68** | 84 |
| Classes | 2.1 | 1.9 |
| Longest function (lines) | **16.5** | 23.6 |
| Mean cyclomatic complexity | **2.62** | 3.88 |
| Max cyclomatic complexity | **5.5** | 7.0 |
| Max parameters | 2.83 | 3.38 |
| Linter findings (ruff) | 1.1 | 2.3 |
| Diff size (lines added + removed) | 231 | 220 |

- **Linter findings** are mostly `PLR2004` (magic values), much of it already present in the legacy starters of h1 and m1. v2 runs restructured more of that code.
- **Diff size** is about the same. v2 writes less production code but more test code.
- Per-task tables are in `tables.md`.

### Cost

| Level | Tokens v2 | Tokens baseline | Ratio | Extra tokens per task |
|---|---|---|---|---|
| Small | 89.4k | 78.3k | 1.14 | +11.1k |
| Medium | 98.9k | 84.2k | 1.17 | +14.7k |
| Large | 108.9k | 93.3k | 1.17 | +15.6k |
| **All** | **100.3k** | **86.1k** | **1.16** | **+14.2k** |

- **Wall time:** mean 212 s vs 140 s (1.5×), median 189 s vs 133 s (1.4×). Wall time is noisy, because runs shared one machine in parallel.
- **Tool calls:** mean 16.1 vs 10.5 (1.5×).
- **Total extra tokens:** 340k, for 14 decisive wins and 3 decisive losses, which is about 24k extra tokens per decisive win. In round 1, v1 spent 692k extra tokens for 6 wins and 8 losses.
- **What the figures include:** as in round 1, both conditions carry the agent's fixed overhead (system prompt and tool definitions). The ratios therefore understate the relative increase in the agent's own work.

### Pre-registered secondary hypotheses (seen tasks, each version against its own baseline)

| Hypothesis | v1 (round 1) | v2 (round 2) | Result |
|---|---|---|---|
| Scope win share higher than v1's | 0–11 (0%) | 8–3 (73%) | Supported |
| Tests win share at least 50% | 7–2 (78%) | 8–5 (62%) | Supported, but weaker than v1. Without the 3 seen pairs where the baseline wrote no tests, it is 5–5. |
| Token ratio below 1.44 | 1.44 | 1.17 | Supported |
| Wall-time ratio below 2.7 | 2.69 | 1.50 | Supported |
| Diff-size ratio below 1.28 | 1.28 | 0.99 | Supported |
| No sign of overfitting (holdout not clearly worse than seen) | – | holdout 5–0–1, seen 9–3–6 | No sign of overfitting, but only 6 holdout pairs |

The round-1 and round-2 baselines come from different sessions and behave somewhat differently. For example, the baseline wrote no tests in 4 of 24 runs here, against 1 of 18 in round 1. That is why these comparisons use ratios and win shares against each version's own baseline, and why they are descriptive only.

## What v2 changes in practice (from the diffs and the judges' reasons)

- **Less production code, simpler functions.** On the seen tasks, v2 wrote about 60 production lines per run against the baseline's 79. In round 1, v1 had written more than its baseline (99 vs 83).
  - The gap is largest on l1 (83 vs 148 lines), then l2 (122 vs 147), m2 (53 vs 74) and h2 (113 vs 132).
  - Judges repeatedly called the baseline's extras unneeded: locks, float tolerance, duck-type checks, `TypeVar`s, label constants, extra modules, heavy docstrings, a duplicate-channel filter the spec didn't ask for.
- **Tests every time.** All 24 v2 runs added tests, while 4 baseline runs added none: m2 r1 and r3, h2 r3, s2 r2. Judges weighed missing tests heavily.
- **Legacy code is pinned before it changes.** In h1 and m1, the v2 runs first wrote tests capturing current behavior. h1 judges cited these regression checks in all three v2 wins.
- **The robustness trade-off is real.** The baseline won robustness 8–0, all on seen tasks: l1 ×3, m2 ×3 and s2 ×2. The other 16 pairs, including all 6 holdout pairs, were ties. The judges cited empty addresses, positional placeholders and copying the channel list (l1); locks, float tolerance and a clock going backwards (m2); and checking absolute zero in the source unit and type guards (s2). Some of these points are genuine:
  - **m2 r2:** one of the two judges preferred the baseline because its token bucket tolerates float drift, while v2's version can refuse a token that is due after many small clock steps. The other judge preferred v2, so the pair counts as a tie. The hidden tests don't cover this case.
  - **s2 r1:** the v2 run converted to Celsius before checking absolute zero. Tiny sub-zero inputs can therefore slip through by rounding.
  - "No speculative extras" sometimes removes protection a careful reviewer would want.
- **m1: the two judges disagreed.** In all three m1 pairs, the two judges reached opposite verdicts. The positions of v2 and the baseline varied, so this is a disagreement between two judges, not a position bias:
  - The order-1 judge preferred the baseline's minimal change every time.
  - The order-2 judge preferred v2's restructure every time: one shared price calculation, a tier table in r2 and r3, and in those two runs a dead silver rule removed.

  All three v2 runs restructured, so this task tests the tension between "smallest change" and "restructure when a new variant would repeat the same edit". The judges themselves were divided.
- **Small tasks: no change.** Small tasks went 2–3–1, the same as in round 1. In s1, both baseline wins came from broader tests (parametrized invalid inputs, a check that every item appears on exactly one page).
- **Trap task (s2).** A mild over-structure signal remains:
  - v2 used one small record class per run (0 for the baseline), with the same production size (39 vs 40 lines).
  - Judges split 1–1–1.
- **No reference files, no extra tools.** No v2 run opened the reference files. No v2 run ran a tool the project doesn't configure: three only checked whether such tools were installed. Two baseline runs did run mypy or pyflakes.
- **Still slower than the baseline.** v2 runs ran the tests more often (77 pytest runs vs 36), made more edits, and read more files (29 file reads vs 9, plus the 24 reads of `SKILL.md`). Pinning legacy behavior adds work on h1 and m1. On the greenfield tasks (h2, l1, m2, s2), v2 still used 1.33× the tool calls and 1.37× the wall time. Both conditions wrote scripts comparing old and new code about equally often.

## Decision (pre-registered rule)

- **v2 helps:** win share 82%, CI 59–94%, entirely above 50%.
- **The guardrail holds:** correctness is unchanged.
- **The cost is moderate:** +16% tokens, about 1.5× wall time.

The honest summary: on these tasks, blind reviewers preferred v2's output in 14 of 17 decisive pairs, including all 5 decisive holdout pairs. v2's code is smaller and simpler, always tested, and less defensive. A noticeable part of the margin comes from baseline runs that skipped tests. The robustness loss is the trade-off to watch.

## Deviations from the plan

1. **Pre-registration by hash, not by commit.** This was the user's choice.
   - **What happened:** the manifest by mistake included 74 files of a ruff cache directory copied over from round 1 (`ab-test/harness/.ruff_cache`). That directory was deleted after the runs while caches were being cleaned up.
   - **What still checks out:** all 75 other files (the skill, the plan, the tasks, the hidden tests and the harness) still match their hashes.
  - **To check it yourself:** run `sha256sum -c --ignore-missing ab-test/PREREG-MANIFEST.txt` from the repository root. `ab-test/README.md` was edited after the runs to describe round 2 (documentation only), so its line is expected to fail.
2. **`SUMMARY.md`.** As in round 1, the runtime blocks subagents from writing report files. Three runs wrote `SUMMARY.md` through the shell anyway: v2 h1 r1, and baseline h1 r2 and l1 r3. Summaries are excluded from the diffs and the metrics.
   - **What's new:** this round, each agent's final report and tool calls are saved in `agent_reports.json`.
3. **Judges answered in text.** Their JSON replies were extracted verbatim from the judge transcripts by a script, not copied by hand. Each judge read only its own packet.
4. **Scratch files outside the workspace.** Agents in both conditions wrote temporary comparison scripts to a shared scratch directory outside their workspace, even though the prompt said to work only inside it. From the tool calls, 7 v2 runs and 8 baseline runs did this.
   - One agent reported that another run overwrote its scratch script, and it reran the check in a private folder.
   - Only the code left in the workspaces was graded and judged.

## Limitations

- **Small sample.** 24 pairs, and only 6 holdout pairs. The seen tasks alone are not decisive.
- **The test-writing confound.** Part of the margin comes from 4 baseline runs with no tests. With those pairs removed, the result is borderline.
- **Robustness.** v2 lost robustness in 8 of 24 pairs, in three tasks, and never won it. The hidden tests don't measure the cases involved, such as concurrency, float drift and empty addresses.
- **Judge bias and noise.** The judges are LLMs of the same family. On m1, the two judges disagreed on every pair. Requiring both orders to agree turns such cases into ties, but cannot remove judge bias.
- **Author bias and overfitting.** The same assistant wrote the skill, the tasks and the hidden tests, and tuned v2 after seeing round 1. The holdout tasks and pre-registration are the mitigations.
- **The rest is as in round 1:** Python only, one model, small synthetic tasks, triggering of the skill not tested.

## Files

- `runs/<task>/<condition>/r<n>/`: the code each agent left, with caches removed.
- `prompts.json`, `workspace_map.json`, `skill_version.txt`: the exact prompts and the skill snapshot used.
- `agent_reports.json`: each run's final report and a short form of its tool calls.
- `grades.json`: hidden-test results, the agents' own tests, static metrics and diff sizes.
- `costs.json`, `judge_costs.json`: tokens, wall time and tool calls, as reported by the agent runner.
- `judging/*.md`: the blind packets. `judging/*.judgment.json`: the judges' answers. `judging/key.json`: the de-blinding key.
- `summary.json`, `tables.md`: aggregated statistics, produced by `harness/aggregate.py`.
