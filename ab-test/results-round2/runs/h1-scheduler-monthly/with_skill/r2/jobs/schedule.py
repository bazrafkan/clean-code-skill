# Job schedules for the task runner.
import calendar
from datetime import timedelta

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def next_run(job, now):
    # job: dict with "kind", "hour", "minute"
    # (+ "weekday" for weekly, 0 = Monday; + "day" for monthly, 1-31)
    # returns the first run strictly after now
    k = job["kind"]
    if k == "daily":
        c = now.replace(hour=job["hour"], minute=job["minute"], second=0, microsecond=0)
        if c <= now:
            c = c + timedelta(days=1)
        return c
    elif k == "weekly":
        c = now.replace(hour=job["hour"], minute=job["minute"], second=0, microsecond=0)
        d = (job["weekday"] - now.weekday()) % 7
        c = c + timedelta(days=d)
        if c <= now:
            c = c + timedelta(days=7)
        return c
    elif k == "monthly":
        run = _monthly_run_in_month_of(now, job)
        if run <= now:
            # The 1st of any month plus 31 days always falls in the following month.
            run = _monthly_run_in_month_of(now.replace(day=1) + timedelta(days=31), job)
        return run
    else:
        raise ValueError("unknown kind: " + str(k))


def _monthly_run_in_month_of(date, job):
    # Months with fewer than job["day"] days run on their last day.
    last_day = calendar.monthrange(date.year, date.month)[1]
    return date.replace(
        day=min(job["day"], last_day),
        hour=job["hour"],
        minute=job["minute"],
        second=0,
        microsecond=0,
    )


def describe(job):
    k = job["kind"]
    t = "%02d:%02d" % (job["hour"], job["minute"])
    if k == "daily":
        return "every day at " + t
    elif k == "weekly":
        return "every " + DAYS[job["weekday"]] + " at " + t
    elif k == "monthly":
        return "every month on day " + str(job["day"]) + " at " + t
    else:
        raise ValueError("unknown kind: " + str(k))


def validate(job):
    errors = []
    k = job.get("kind")
    if k not in ("daily", "weekly", "monthly"):
        errors.append("kind must be daily, weekly or monthly")
    h = job.get("hour")
    if not isinstance(h, int) or h < 0 or h > 23:
        errors.append("hour must be 0-23")
    m = job.get("minute")
    if not isinstance(m, int) or m < 0 or m > 59:
        errors.append("minute must be 0-59")
    if k == "weekly":
        w = job.get("weekday")
        if not isinstance(w, int) or w < 0 or w > 6:
            errors.append("weekday must be 0-6")
    if k == "monthly":
        d = job.get("day")
        if not isinstance(d, int) or d < 1 or d > 31:
            errors.append("day must be 1-31")
    return errors
