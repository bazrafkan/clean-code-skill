Add a "monthly" schedule kind to `jobs/schedule.py`.

A monthly job looks like `{"kind": "monthly", "day": 31, "hour": 9, "minute": 0}`, where `day` is the day of the month (1–31).

- `next_run(job, now)` returns the first run strictly after `now`: day `day` of a month, at `hour:minute`. In a month that has fewer than `day` days, the job runs on that month's last day instead (for example, day 31 runs on 30 April and on 28 or 29 February).
- `describe(job)` returns `every month on day <day> at HH:MM`, for example `every month on day 5 at 09:00`.
- `validate(job)` reports `day must be 1-31` when a monthly job's `day` is missing, not an integer, or out of range. The error for an unknown kind becomes `kind must be daily, weekly or monthly`.

Requirements:
- Apart from that one error message, daily and weekly jobs must behave exactly as they do today, in all three functions.
- The three functions must keep their current names and signatures.
