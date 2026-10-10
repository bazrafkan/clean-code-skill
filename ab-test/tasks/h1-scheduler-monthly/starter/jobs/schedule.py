# Job schedules for the task runner.
from datetime import timedelta

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def next_run(job, now):
    # job: dict with "kind", "hour", "minute" (+ "weekday" for weekly, 0 = Monday)
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
    else:
        raise ValueError("unknown kind: " + str(k))


def describe(job):
    k = job["kind"]
    t = "%02d:%02d" % (job["hour"], job["minute"])
    if k == "daily":
        return "every day at " + t
    elif k == "weekly":
        return "every " + DAYS[job["weekday"]] + " at " + t
    else:
        raise ValueError("unknown kind: " + str(k))


def validate(job):
    errors = []
    k = job.get("kind")
    if k != "daily" and k != "weekly":
        errors.append("kind must be daily or weekly")
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
    return errors
