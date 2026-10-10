# Monthly schedule kind

I added a `"monthly"` kind to `jobs/schedule.py`. All 13 tests pass (the 3 original ones plus 10 new ones).

## What changed

- **`next_run(job, now)`**: a monthly job runs on day `day` of the current month at `hour:minute`. If that time is not strictly after `now`, it runs next month instead (December rolls over to January). In a month with fewer than `day` days, it runs on the month's last day. For example, day 31 runs on 30 April and on 28 or 29 February. A short month only affects its own run: the run after 30 April is 31 May. A small helper, `_monthly_run`, picks the day and keeps the timezone of `now`, as the daily and weekly code already does.
- **`describe(job)`** returns `every month on day <day> at HH:MM`, for example `every month on day 5 at 09:00`.
- **`validate(job)`** adds `day must be 1-31` when a monthly job's `day` is missing, not an integer, or outside 1–31. The unknown-kind error now reads `kind must be daily, weekly or monthly`.

The three functions keep their names and signatures.

## Daily and weekly are unchanged

I ran the original code and the new code side by side on 200,000 random inputs. The inputs mixed daily and weekly jobs, missing fields, invalid values (strings, floats, `None`, booleans, out-of-range numbers) and both naive and timezone-aware `now` values. `next_run`, `describe` and `validate` gave the same results and raised the same errors every time. The only difference was the unknown-kind error text, which was meant to change.

I also checked monthly `next_run` on 100,000 random cases against a simple month-by-month search.

## Tests added (`tests/test_schedule.py`)

- Run later this month, later the same day, and exactly at `now` (moves to next month)
- Day 31 in April, and day 30 or 31 in February in a normal year and a leap year
- December rolling over to January
- The `describe` text
- Valid monthly jobs give no errors
- `day` missing, 0, 32, -1, `"5"`, `5.0` or `None` gives `day must be 1-31`
- The new unknown-kind error text

## One thing to know

The `day` check works like the existing `hour`, `minute` and `weekday` checks. Python counts `True` and `False` as integers, so `"day": True` passes validation as day 1. I left it that way so all the checks behave alike. Rejecting booleans would mean adding the same rule to every field.
