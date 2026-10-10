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


def test_daily_at_exactly_now_runs_tomorrow():
    job = {"kind": "daily", "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 11, 9, 0)


def test_weekly_already_passed_this_week_runs_next_week():
    job = {"kind": "weekly", "weekday": 1, "hour": 8, "minute": 0}
    tuesday_after_run = datetime(2026, 3, 10, 9, 0)
    assert next_run(job, tuesday_after_run) == datetime(2026, 3, 17, 8, 0)


def test_daily_description():
    assert describe({"kind": "daily", "hour": 18, "minute": 30}) == "every day at 18:30"


def test_weekly_job_with_bad_weekday_is_invalid():
    job = {"kind": "weekly", "weekday": 7, "hour": 8, "minute": 0}
    assert validate(job) == ["weekday must be 0-6"]


def test_unknown_kind_is_rejected_by_next_run_and_describe():
    job = {"kind": "yearly", "hour": 8, "minute": 0}
    with pytest.raises(ValueError, match="unknown kind: yearly"):
        next_run(job, datetime(2026, 3, 10, 9, 0))
    with pytest.raises(ValueError, match="unknown kind: yearly"):
        describe(job)


def test_unknown_kind_is_invalid():
    assert validate({"kind": "yearly", "hour": 8, "minute": 0}) == [
        "kind must be daily, weekly or monthly"
    ]


def test_monthly_later_this_month():
    job = {"kind": "monthly", "day": 15, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 3, 10, 12, 0)) == datetime(2026, 3, 15, 9, 0)


def test_monthly_at_exactly_now_runs_next_month():
    job = {"kind": "monthly", "day": 10, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 4, 10, 9, 0)


def test_monthly_in_december_after_run_rolls_over_to_january():
    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 12, 20, 9, 0)) == datetime(2027, 1, 5, 9, 0)


def test_monthly_day_31_runs_on_last_day_of_30_day_month():
    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 4, 2, 9, 0)) == datetime(2026, 4, 30, 9, 0)


def test_monthly_day_31_runs_on_28_february_in_common_year():
    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 2, 1, 9, 0)) == datetime(2026, 2, 28, 9, 0)


def test_monthly_day_31_runs_on_29_february_in_leap_year():
    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2028, 2, 1, 9, 0)) == datetime(2028, 2, 29, 9, 0)


def test_monthly_after_short_month_run_returns_to_requested_day():
    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
    just_after_april_run = datetime(2026, 4, 30, 9, 1)
    assert next_run(job, just_after_april_run) == datetime(2026, 5, 31, 9, 0)


def test_monthly_from_31st_into_shorter_month():
    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 1, 31, 10, 0)) == datetime(2026, 2, 28, 9, 0)


def test_monthly_description():
    assert describe({"kind": "monthly", "day": 5, "hour": 9, "minute": 0}) == (
        "every month on day 5 at 09:00"
    )


@pytest.mark.parametrize("day", [1, 31])
def test_monthly_job_with_day_at_boundary_is_valid(day):
    assert validate({"kind": "monthly", "day": day, "hour": 9, "minute": 0}) == []


@pytest.mark.parametrize("day", [0, 32, "5", None])
def test_monthly_job_with_bad_day_is_invalid(day):
    job = {"kind": "monthly", "day": day, "hour": 9, "minute": 0}
    assert validate(job) == ["day must be 1-31"]


def test_monthly_job_without_day_is_invalid():
    assert validate({"kind": "monthly", "hour": 9, "minute": 0}) == ["day must be 1-31"]
