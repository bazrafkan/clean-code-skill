from datetime import datetime

from jobs.schedule import describe, next_run, validate


def test_daily_later_today():
    job = {"kind": "daily", "hour": 18, "minute": 30}
    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 10, 18, 30)


def test_weekly_description():
    job = {"kind": "weekly", "weekday": 0, "hour": 7, "minute": 5}
    assert describe(job) == "every Monday at 07:05"


def test_valid_daily_job_has_no_errors():
    assert validate({"kind": "daily", "hour": 0, "minute": 0}) == []


def test_monthly_later_this_month():
    job = {"kind": "monthly", "day": 15, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 3, 10, 12, 0)) == datetime(2026, 3, 15, 9, 0)


def test_monthly_already_passed_moves_to_next_month():
    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 3, 5, 9, 0)) == datetime(2026, 4, 5, 9, 0)


def test_monthly_rolls_over_the_year():
    job = {"kind": "monthly", "day": 10, "hour": 8, "minute": 0}
    assert next_run(job, datetime(2026, 12, 20, 8, 0)) == datetime(2027, 1, 10, 8, 0)


def test_monthly_day_31_runs_on_last_day_of_short_month():
    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 4, 1, 0, 0)) == datetime(2026, 4, 30, 9, 0)
    assert next_run(job, datetime(2026, 2, 1, 0, 0)) == datetime(2026, 2, 28, 9, 0)
    assert next_run(job, datetime(2028, 2, 1, 0, 0)) == datetime(2028, 2, 29, 9, 0)


def test_monthly_after_clamped_run_goes_to_next_month():
    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 4, 30, 9, 0)) == datetime(2026, 5, 31, 9, 0)
    assert next_run(job, datetime(2026, 1, 31, 10, 0)) == datetime(2026, 2, 28, 9, 0)


def test_monthly_description():
    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
    assert describe(job) == "every month on day 5 at 09:00"


def test_valid_monthly_job_has_no_errors():
    assert validate({"kind": "monthly", "day": 31, "hour": 9, "minute": 0}) == []


def test_monthly_day_errors():
    base = {"kind": "monthly", "hour": 9, "minute": 0}
    assert validate(base) == ["day must be 1-31"]
    assert validate(dict(base, day="5")) == ["day must be 1-31"]
    assert validate(dict(base, day=0)) == ["day must be 1-31"]
    assert validate(dict(base, day=32)) == ["day must be 1-31"]


def test_unknown_kind_error():
    assert validate({"kind": "yearly", "hour": 9, "minute": 0}) == [
        "kind must be daily, weekly or monthly"
    ]
