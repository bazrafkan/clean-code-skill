import itertools
from datetime import datetime, timedelta

import pytest

from jobs.schedule import describe, next_run, validate

_DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def _legacy_next_run(job, now):
    c = now.replace(hour=job["hour"], minute=job["minute"], second=0, microsecond=0)
    if job["kind"] == "daily":
        if c <= now:
            c = c + timedelta(days=1)
        return c
    c = c + timedelta(days=(job["weekday"] - now.weekday()) % 7)
    if c <= now:
        c = c + timedelta(days=7)
    return c


def _legacy_validate(job):
    errors = []
    k = job.get("kind")
    if k != "daily" and k != "weekly":
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
    return errors


NOWS = [
    datetime(2026, 3, 10, 9, 0),
    datetime(2026, 3, 10, 9, 0, 30),
    datetime(2026, 12, 31, 23, 59),
    datetime(2028, 2, 28, 23, 0),
    datetime(2026, 6, 14, 0, 0),
]
TIMES = [(0, 0), (9, 0), (23, 59)]


@pytest.mark.parametrize("now,time", list(itertools.product(NOWS, TIMES)))
def test_daily_next_run_unchanged(now, time):
    job = {"kind": "daily", "hour": time[0], "minute": time[1]}
    assert next_run(job, now) == _legacy_next_run(job, now)


@pytest.mark.parametrize("now,time,weekday", list(itertools.product(NOWS, TIMES, range(7))))
def test_weekly_next_run_unchanged(now, time, weekday):
    job = {"kind": "weekly", "weekday": weekday, "hour": time[0], "minute": time[1]}
    assert next_run(job, now) == _legacy_next_run(job, now)


def test_daily_and_weekly_descriptions_unchanged():
    assert describe({"kind": "daily", "hour": 7, "minute": 5}) == "every day at 07:05"
    for weekday, name in enumerate(_DAYS):
        job = {"kind": "weekly", "weekday": weekday, "hour": 18, "minute": 30}
        assert describe(job) == "every " + name + " at 18:30"


@pytest.mark.parametrize(
    "job",
    [
        {"kind": "daily", "hour": 0, "minute": 0},
        {"kind": "daily", "hour": 24, "minute": 0},
        {"kind": "daily", "hour": 1, "minute": 60},
        {"kind": "daily", "hour": "1", "minute": 5},
        {"kind": "daily"},
        {"kind": "weekly", "hour": 1, "minute": 1, "weekday": 6},
        {"kind": "weekly", "hour": 1, "minute": 1, "weekday": 7},
        {"kind": "weekly", "hour": 1, "minute": 1},
        {"kind": "weekly", "hour": -1, "minute": 99, "weekday": "mon"},
    ],
)
def test_daily_and_weekly_validation_unchanged(job):
    assert validate(job) == _legacy_validate(job)


def test_unknown_kind_message():
    assert validate({"kind": "yearly", "hour": 1, "minute": 1}) == ["kind must be daily, weekly or monthly"]
    assert validate({"hour": 1, "minute": 1}) == ["kind must be daily, weekly or monthly"]


def test_unknown_kind_still_raises_in_next_run_and_describe():
    job = {"kind": "yearly", "hour": 1, "minute": 1}
    with pytest.raises(ValueError):
        next_run(job, datetime(2026, 1, 1))
    with pytest.raises(ValueError):
        describe(job)


def _monthly(day, hour=9, minute=0):
    return {"kind": "monthly", "day": day, "hour": hour, "minute": minute}


@pytest.mark.parametrize(
    "job,now,expected",
    [
        (_monthly(15), datetime(2026, 3, 10, 12, 0), datetime(2026, 3, 15, 9, 0)),
        (_monthly(15), datetime(2026, 3, 15, 8, 59), datetime(2026, 3, 15, 9, 0)),
        (_monthly(15), datetime(2026, 3, 15, 9, 0), datetime(2026, 4, 15, 9, 0)),
        (_monthly(15), datetime(2026, 3, 15, 9, 0, 1), datetime(2026, 4, 15, 9, 0)),
        (_monthly(15), datetime(2026, 3, 20, 0, 0), datetime(2026, 4, 15, 9, 0)),
        (_monthly(1, 0, 0), datetime(2026, 12, 31, 23, 59), datetime(2027, 1, 1, 0, 0)),
        (_monthly(10), datetime(2026, 12, 11, 0, 0), datetime(2027, 1, 10, 9, 0)),
        (_monthly(31), datetime(2026, 1, 31, 10, 0), datetime(2026, 2, 28, 9, 0)),
        (_monthly(31), datetime(2028, 1, 31, 10, 0), datetime(2028, 2, 29, 9, 0)),
        (_monthly(30), datetime(2026, 2, 1, 0, 0), datetime(2026, 2, 28, 9, 0)),
        (_monthly(31), datetime(2026, 2, 28, 8, 0), datetime(2026, 2, 28, 9, 0)),
        (_monthly(29), datetime(2026, 2, 28, 10, 0), datetime(2026, 3, 29, 9, 0)),
        (_monthly(31), datetime(2026, 4, 1, 0, 0), datetime(2026, 4, 30, 9, 0)),
        (_monthly(31), datetime(2026, 4, 30, 9, 0), datetime(2026, 5, 31, 9, 0)),
        (_monthly(31, 23, 59), datetime(2026, 5, 31, 23, 58), datetime(2026, 5, 31, 23, 59)),
    ],
)
def test_monthly_next_run(job, now, expected):
    assert next_run(job, now) == expected


def test_monthly_description():
    assert describe(_monthly(5)) == "every month on day 5 at 09:00"
    assert describe(_monthly(31, 23, 5)) == "every month on day 31 at 23:05"


def test_valid_monthly_job_has_no_errors():
    assert validate(_monthly(1)) == []
    assert validate(_monthly(31, 23, 59)) == []


@pytest.mark.parametrize("day", [0, 32, -1, "5", 5.0, None])
def test_invalid_monthly_day(day):
    job = _monthly(1)
    job["day"] = day
    assert validate(job) == ["day must be 1-31"]


def test_missing_monthly_day():
    assert validate({"kind": "monthly", "hour": 9, "minute": 0}) == ["day must be 1-31"]


def test_monthly_job_still_checks_time():
    errors = validate({"kind": "monthly", "day": 3, "hour": 25, "minute": 0})
    assert errors == ["hour must be 0-23"]
