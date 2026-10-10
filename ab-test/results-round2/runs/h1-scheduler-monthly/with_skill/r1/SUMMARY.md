# Monthly schedule kind

I added a `"monthly"` kind to `jobs/schedule.py`. All three functions keep their names and signatures.

## What changed

- **`next_run(job, now)`**: for a monthly job, it tries day `day` of the current month at `hour:minute`. If that time is not strictly after `now`, it uses next month instead, and December rolls over to January of the next year. When a month has fewer than `day` days, the job runs on that month's last day: day 31 runs on 30 April, and on 28 or 29 February. Two small private helpers do the work: `_monthly_run_in_month_of` and `_first_day_of_next_month`. They use `datetime.replace`, the same way the existing branches do, so a timezone-aware `now` keeps its `tzinfo`.
- **`describe(job)`**: returns `every month on day <day> at HH:MM`, for example `every month on day 5 at 09:00`.
- **`validate(job)`**: reports `day must be 1-31` when a monthly job's `day` is missing, not an `int`, or outside 1–31. The unknown-kind error now reads `kind must be daily, weekly or monthly`.
- I updated the comment at the top of `next_run` to mention the `day` field, because it had become out of date.

Daily and weekly code paths are unchanged. The only daily/weekly difference is the new unknown-kind message.

## Tests (`tests/test_schedule.py`)

- Before changing anything, I added 6 tests that lock in today's daily and weekly behaviour, since there were only 3 tests:
  - a daily run that has already passed today, or is exactly now, moves to tomorrow
  - weekly runs later this week, and a weekly run on today's weekday that has already passed moves to next week
  - the daily description
  - the combined weekly validation errors
- Then I wrote the monthly tests first and confirmed they failed. They cover:
  - later this month, already passed, and exactly at the run time
  - December rolling over to January
  - day 31 in April, in February, and in February of a leap year
  - a run that was moved to a short month's last day going back to the full day the next month (28 Feb → 31 Mar)
  - the description
  - day values 1 and 31 being valid
  - day missing, `None`, `"5"`, `5.0`, `0` and `32` each giving `day must be 1-31`
  - the new unknown-kind message
- Result: `python3 -m pytest` gives **27 passed**. The project has no linter, formatter or type checker set up, so there was nothing else to run.

## Notes

- **Cleanups beyond the request:** none. The only touched line I rewrote is the kind check, which now uses `k not in (...)` because I had to edit that line anyway.
- **Left out on purpose:**
  - No extra checks in `next_run` or `describe` for a bad or missing `day`. They behave like the existing kinds and raise on a malformed job, and `validate` is the function meant to catch bad input.
  - No `KINDS` constant. The list of kinds appears only once.
- **Patterns introduced:** none.
- **Problems outside this task that I didn't touch:**
  - All three functions use the same `if/elif` chain on `kind`. That's why adding a kind needed edits in three places. If more kinds are coming, one table of per-kind behaviour would avoid this, but I didn't make that refactor here because it would have made the change bigger.
  - Because `isinstance(True, int)` is `True` in Python, `validate` accepts booleans for `hour`, `minute`, `weekday` and now `day`. The new check matches the existing ones; I didn't fix the bool case for any of them.
  - The existing code uses one-letter local names (`k`, `c`, `d`, `h`, `m`, `w`).
