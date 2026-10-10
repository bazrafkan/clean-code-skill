# Job schedules for the task runner.
import calendar
from datetime import datetime, timedelta

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
KINDS = ("daily", "weekly", "monthly")


def next_run(job, now):
    """Return the first run of `job` strictly after `now`."""
    kind = job["kind"]
    if kind == "daily":
        candidate = _at_job_time(now, job)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate
    if kind == "weekly":
        candidate = _at_job_time(now, job) + timedelta(days=(job["weekday"] - now.weekday()) % 7)
        if candidate <= now:
            candidate += timedelta(days=7)
        return candidate
    if kind == "monthly":
        candidate = _monthly_run(now.year, now.month, job)
        if candidate <= now:
            year, month = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
            candidate = _monthly_run(year, month, job)
        return candidate
    raise ValueError("unknown kind: " + str(kind))


def _at_job_time(moment, job):
    return moment.replace(hour=job["hour"], minute=job["minute"], second=0, microsecond=0)


def _monthly_run(year, month, job):
    """The job's run in the given month; short months run on their last day."""
    last_day = calendar.monthrange(year, month)[1]
    return datetime(year, month, min(job["day"], last_day), job["hour"], job["minute"])


def describe(job):
    kind = job["kind"]
    time = "%02d:%02d" % (job["hour"], job["minute"])
    if kind == "daily":
        return "every day at " + time
    if kind == "weekly":
        return "every " + DAYS[job["weekday"]] + " at " + time
    if kind == "monthly":
        return "every month on day %d at %s" % (job["day"], time)
    raise ValueError("unknown kind: " + str(kind))


def validate(job):
    errors = []
    kind = job.get("kind")
    if kind not in KINDS:
        errors.append("kind must be daily, weekly or monthly")
    if not _int_in_range(job.get("hour"), 0, 23):
        errors.append("hour must be 0-23")
    if not _int_in_range(job.get("minute"), 0, 59):
        errors.append("minute must be 0-59")
    if kind == "weekly" and not _int_in_range(job.get("weekday"), 0, 6):
        errors.append("weekday must be 0-6")
    if kind == "monthly" and not _int_in_range(job.get("day"), 1, 31):
        errors.append("day must be 1-31")
    return errors


def _int_in_range(value, low, high):
    return isinstance(value, int) and low <= value <= high
