from datetime import datetime

import pytest

from jobs.schedule import describe, next_run, validate


def test_daily_later_today():
    job = {"kind": "daily", "hour": 18, "minute": 30}
    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 10, 18, 30)


def test_weekly_description():
    job = {"kind": "weekly", "weekday": 0, "hour": 7, "minute": 5}
    assert describe(job) == "every Monday at 07:05"


def test_valid_daily_job_has_no_errors():
    assert validate({"kind": "daily", "hour": 0, "minute": 0}) == []


def test_daily_already_passed_runs_tomorrow():
    job = {"kind": "daily", "hour": 8, "minute": 0}
    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 11, 8, 0)


def test_daily_at_exact_run_time_runs_tomorrow():
    job = {"kind": "daily", "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 11, 9, 0)


def test_weekly_later_this_week():
    job = {"kind": "weekly", "weekday": 4, "hour": 7, "minute": 5}
    # 2026-03-10 is a Tuesday.
    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 13, 7, 5)


def test_weekly_same_weekday_already_passed_runs_next_week():
    job = {"kind": "weekly", "weekday": 1, "hour": 7, "minute": 5}
    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 17, 7, 5)


def test_daily_description():
    assert describe({"kind": "daily", "hour": 18, "minute": 30}) == "every day at 18:30"


def test_weekly_with_bad_weekday_and_time_reports_each_error():
    job = {"kind": "weekly", "weekday": 7, "hour": 24, "minute": -1}
    assert validate(job) == ["hour must be 0-23", "minute must be 0-59", "weekday must be 0-6"]


def test_unknown_kind_lists_all_kinds():
    assert validate({"kind": "yearly", "hour": 9, "minute": 0}) == [
        "kind must be daily, weekly or monthly"
    ]


def test_monthly_later_this_month():
    job = {"kind": "monthly", "day": 15, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 3, 10, 12, 0)) == datetime(2026, 3, 15, 9, 0)


def test_monthly_already_passed_runs_next_month():
    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 3, 10, 12, 0)) == datetime(2026, 4, 5, 9, 0)


def test_monthly_at_exact_run_time_runs_next_month():
    job = {"kind": "monthly", "day": 10, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 4, 10, 9, 0)


def test_monthly_in_december_runs_in_january_of_next_year():
    job = {"kind": "monthly", "day": 1, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 12, 20, 12, 0)) == datetime(2027, 1, 1, 9, 0)


def test_monthly_day_31_runs_on_last_day_of_april():
    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 4, 2, 12, 0)) == datetime(2026, 4, 30, 9, 0)


def test_monthly_day_31_runs_on_28_february():
    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 1, 31, 12, 0)) == datetime(2026, 2, 28, 9, 0)


def test_monthly_day_31_runs_on_29_february_in_leap_year():
    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2028, 2, 1, 12, 0)) == datetime(2028, 2, 29, 9, 0)


def test_monthly_after_shortened_run_uses_full_day_next_month():
    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 2, 28, 12, 0)) == datetime(2026, 3, 31, 9, 0)


def test_monthly_description():
    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
    assert describe(job) == "every month on day 5 at 09:00"


@pytest.mark.parametrize("day", [1, 31])
def test_monthly_with_day_in_range_has_no_errors(day):
    assert validate({"kind": "monthly", "day": day, "hour": 9, "minute": 0}) == []


@pytest.mark.parametrize("day", [None, "5", 5.0, 0, 32])
def test_monthly_with_bad_day_reports_day_error(day):
    job = {"kind": "monthly", "day": day, "hour": 9, "minute": 0}
    assert validate(job) == ["day must be 1-31"]


def test_monthly_without_day_reports_day_error():
    assert validate({"kind": "monthly", "hour": 9, "minute": 0}) == ["day must be 1-31"]
