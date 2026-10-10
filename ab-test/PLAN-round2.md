# A/B test plan, round 2 (pre-registered)

Round 1 (see `PLAN.md` and `results/REPORT.md`) was inconclusive on quality and showed the skill growing the scope of changes, at about +44% tokens. Round 2 tests a revised skill, **v2**, built from the round-1 hypotheses.

This plan was fixed before any round-2 run. It was not committed to git, by the user's choice. Instead, its SHA-256 and the hashes of every file in the test (see `PREREG-MANIFEST.txt`) were sent to the user in the conversation before the first run.

## What changed in the skill (v1 to v2)

- **Smallest change first.** "The smallest change that fully solves the task" is now in the opening line, in the precedence list and first in the checklist.
- **No speculative extras.** Handle the cases the task states or its domain clearly implies, but add no unrequested validation, thread safety, NaN or type checks, logging, configuration, constants, abstractions, generic typing or new files. Mention them in the report instead.
- **"Make it right" is bounded** to the code the agent wrote or touched. Restructure existing code only when that makes the change simpler.
- **Verify with the project's own tools.** Run the tests and the checks the project already configures. Don't install or run other tools. Leave no caches or scratch files.
- **Testing guidance kept**, plus: pin legacy behavior with tests before changing untested code, and keep tests focused on what the task changed.
- **References are rarely needed.** The skill now says most tasks don't need the reference files.

v2 was written by looking at round-1 results on six tasks. That risks overfitting to those tasks, so round 2 adds two **holdout tasks** written after v2 and never used to tune it.

## Design

**Tasks.** The six round-1 tasks, unchanged, plus two holdout tasks:

| Task | Level | Kind |
|---|---|---|
| `h1-scheduler-monthly` | medium | Add a schedule kind to messy legacy code with a repeated switch, keeping existing behavior and one changed message |
| `h2-ttl-cache` | large | Greenfield: size-limited LRU cache with expiry, statistics and a memoizing decorator, with an injectable clock |

**Conditions.**
- `with_skill`: the agent reads a frozen snapshot of skill v2.
- `without_skill`: no skill. This is a **fresh baseline**, run in the same session as the v2 runs, not reused from round 1.

**Everything else is as in round 1:**
- the same prompt template (`harness/config.py`)
- fresh agents, fresh starters, neutral workspace names
- both conditions told not to use the Skill tool, and launched together
- 3 repetitions per task and condition: 48 runs and 24 pairs
- the same blind judging: 2 presentation orders, 16 judge agents, the same rubric
- the same hidden-test grading and static metrics

Harness changes from round 1: `.mypy_cache` is now ignored in diffs and metrics (a round-1 deviation), and `aggregate.py` reports the "seen" and "holdout" task groups. The packet seed is **7342**.

## Measures and decision rules

**Primary outcome: v2 vs fresh baseline, blind overall win share over all 24 pairs.** The rule is the same as round 1:
- **v2 helps:** the win share among decisive pairs is above 50%, the lower bound of its 95% Wilson interval is above 50%, and the guardrail holds.
- **v2 hurts:** the upper bound is below 50%, or the guardrail fails.
- **Otherwise inconclusive.**

**Guardrail.** The mean hidden-test pass rate with v2 must not be more than 5 percentage points below the baseline's.

**Secondary outcomes (descriptive, not decisive):**
1. **Holdout.** Overall wins on `h1` and `h2` (6 pairs), reported separately from the six seen tasks (18 pairs). If v2 does clearly better on the seen tasks than on the holdout, that points to overfitting.
2. **Round-1 hypotheses**, each checked against round 1 on the six seen tasks:
   - **Scope:** v2's win share on the scope criterion is higher than v1's (0 wins, 11 losses).
   - **Tests:** v2 keeps an advantage on the tests criterion (win share at least 50%).
   - **Cost:** v2's token ratio against its baseline is below v1's 1.44, and its wall-time ratio below v1's 2.7.
   - **Size:** v2's mean diff size relative to its baseline is smaller than v1's (313 vs 244 lines, ratio 1.28).
3. **Per criterion and per complexity level**, as in round 1.
4. **Static metrics and cost per condition**, as in round 1, plus extra tokens per decisive win.

**Comparing v1 and v2.** The round-1 and round-2 runs come from different sessions, so their absolute numbers can drift. The v1-vs-v2 comparison therefore uses each version's ratio or win share **against its own baseline**, and it is descriptive only.

## Known limitations

- **Small sample.** 24 pairs, and only 6 holdout pairs. Only a large effect can be decisive.
- **Overfitting.** v2 was tuned on the six seen tasks. The holdout is the check, but it is small.
- **Author bias.** The same assistant wrote the skill, the tasks, the hidden tests and the plan. Pre-registration by hash, hidden tests and blind judging are the mitigations.
- **The rest is as in round 1:** Python only, one model, synthetic tasks, LLM judges of the same family, triggering not tested.
