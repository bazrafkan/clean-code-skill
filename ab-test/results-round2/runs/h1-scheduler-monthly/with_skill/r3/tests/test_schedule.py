from datetime import datetime

import pytest

from jobs.schedule import describe, next_run, validate


def test_daily_later_today():
    job = {"kind": "daily", "hour": 18, "minute": 30}
    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 10, 18, 30)


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


def test_weekly_already_passed_today_runs_next_week():
    job = {"kind": "weekly", "weekday": 1, "hour": 7, "minute": 5}
    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 17, 7, 5)


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
    assert next_run(job, datetime(2026, 12, 15, 9, 0)) == datetime(2027, 1, 1, 9, 0)


@pytest.mark.parametrize(
    "now, expected",
    [
        (datetime(2026, 4, 1), datetime(2026, 4, 30, 9, 0)),
        (datetime(2026, 2, 1), datetime(2026, 2, 28, 9, 0)),
        (datetime(2028, 2, 1), datetime(2028, 2, 29, 9, 0)),
    ],
)
def test_monthly_runs_on_last_day_of_shorter_month(now, expected):
    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
    assert next_run(job, now) == expected


def test_monthly_returns_to_configured_day_after_shorter_month():
    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
    assert next_run(job, datetime(2026, 4, 30, 10, 0)) == datetime(2026, 5, 31, 9, 0)


def test_next_run_rejects_unknown_kind():
    with pytest.raises(ValueError, match="unknown kind: hourly"):
        next_run({"kind": "hourly", "hour": 9, "minute": 0}, datetime(2026, 3, 10))


def test_daily_description():
    assert describe({"kind": "daily", "hour": 9, "minute": 0}) == "every day at 09:00"


def test_weekly_description():
    job = {"kind": "weekly", "weekday": 0, "hour": 7, "minute": 5}
    assert describe(job) == "every Monday at 07:05"


def test_monthly_description():
    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
    assert describe(job) == "every month on day 5 at 09:00"


def test_describe_rejects_unknown_kind():
    with pytest.raises(ValueError, match="unknown kind: hourly"):
        describe({"kind": "hourly", "hour": 9, "minute": 0})


def test_valid_daily_job_has_no_errors():
    assert validate({"kind": "daily", "hour": 0, "minute": 0}) == []


def test_daily_job_reports_out_of_range_time():
    assert validate({"kind": "daily", "hour": 24, "minute": 60}) == [
        "hour must be 0-23",
        "minute must be 0-59",
    ]


def test_weekly_job_reports_missing_weekday():
    assert validate({"kind": "weekly", "hour": 9, "minute": 0}) == ["weekday must be 0-6"]


@pytest.mark.parametrize("day", [1, 31])
def test_valid_monthly_job_has_no_errors(day):
    assert validate({"kind": "monthly", "day": day, "hour": 9, "minute": 0}) == []


def test_monthly_job_reports_missing_day():
    assert validate({"kind": "monthly", "hour": 9, "minute": 0}) == ["day must be 1-31"]


@pytest.mark.parametrize("day", ["5", 0, 32])
def test_monthly_job_reports_invalid_day(day):
    job = {"kind": "monthly", "day": day, "hour": 9, "minute": 0}
    assert validate(job) == ["day must be 1-31"]


def test_unknown_kind_is_reported():
    assert validate({"kind": "hourly", "hour": 9, "minute": 0}) == [
        "kind must be daily, weekly or monthly"
    ]
