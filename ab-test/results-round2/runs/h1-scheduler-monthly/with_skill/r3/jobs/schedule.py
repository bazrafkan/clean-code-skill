# Job schedules for the task runner.
import calendar
from datetime import timedelta

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def next_run(job, now):
    # job: dict with "kind", "hour", "minute"
    # (+ "weekday" for weekly, 0 = Monday; + "day" of the month for monthly, 1-31)
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
        return _next_monthly_run(job, now)
    else:
        raise ValueError("unknown kind: " + str(k))


def _next_monthly_run(job, now):
    run = _monthly_run_in_month_of(job, now)
    if run <= now:
        run = _monthly_run_in_month_of(job, _first_of_next_month(now))
    return run


def _monthly_run_in_month_of(job, moment):
    days_in_month = calendar.monthrange(moment.year, moment.month)[1]
    return moment.replace(
        day=min(job["day"], days_in_month),
        hour=job["hour"],
        minute=job["minute"],
        second=0,
        microsecond=0,
    )


def _first_of_next_month(moment):
    if moment.month == 12:
        return moment.replace(year=moment.year + 1, month=1, day=1)
    return moment.replace(month=moment.month + 1, day=1)


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
        day = job.get("day")
        if not isinstance(day, int) or day < 1 or day > 31:
            errors.append("day must be 1-31")
    return errors
