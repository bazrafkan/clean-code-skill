You are reviewing two implementations of the same task, written by two different developers.
For each pair below, compare Implementation 1 and Implementation 2 on these criteria:

- readability: names, structure, how easy the code is to read
- design: decomposition and abstraction level; penalize both over-engineering and under-engineering
- robustness: error handling, edge cases, likely bugs you can see by reading
- tests: quality and relevance of tests added or changed (tie if neither adds tests)
- scope: the change is limited to what the task needs; required behavior is preserved
- overall: which one you would rather merge and maintain

Judge only what you can see in the diffs. Longer is not better: extra code, comments or abstractions
that the task does not need count against an implementation. Ties are allowed when there is no real difference.

Reply with only a JSON object (no other text, no code fence), with exactly this shape:
{"pairs": [{"pair": <pair number>, "readability": "1"|"2"|"tie", "design": "1"|"2"|"tie",
"robustness": "1"|"2"|"tie", "tests": "1"|"2"|"tie", "scope": "1"|"2"|"tie", "overall": "1"|"2"|"tie",
"confidence": "low"|"medium"|"high", "reason": "<at most two sentences>"}, ...]}

Read only this packet file. Do not look at any other file or directory, and do not write any files.


## Task given to both developers

Add a "monthly" schedule kind to `jobs/schedule.py`.

A monthly job looks like `{"kind": "monthly", "day": 31, "hour": 9, "minute": 0}`, where `day` is the day of the month (1–31).

- `next_run(job, now)` returns the first run strictly after `now`: day `day` of a month, at `hour:minute`. In a month that has fewer than `day` days, the job runs on that month's last day instead (for example, day 31 runs on 30 April and on 28 or 29 February).
- `describe(job)` returns `every month on day <day> at HH:MM`, for example `every month on day 5 at 09:00`.
- `validate(job)` reports `day must be 1-31` when a monthly job's `day` is missing, not an integer, or out of range. The error for an unknown kind becomes `kind must be daily, weekly or monthly`.

Requirements:
- Apart from that one error message, daily and weekly jobs must behave exactly as they do today, in all three functions.
- The three functions must keep their current names and signatures.

## Pair 1

### Implementation 1

```diff
diff -ruN before/jobs/schedule.py after/jobs/schedule.py
--- before/jobs/schedule.py
+++ after/jobs/schedule.py
@@ -1,11 +1,28 @@
 # Job schedules for the task runner.
+import calendar
 from datetime import timedelta
 
 DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
 
 
+def _monthly_run_in(now, year, month, job):
+    # The monthly run time in the given month. A month shorter than job["day"]
+    # runs on its last day instead (day 31 -> 30 April, 28/29 February).
+    last_day = calendar.monthrange(year, month)[1]
+    return now.replace(
+        year=year,
+        month=month,
+        day=min(job["day"], last_day),
+        hour=job["hour"],
+        minute=job["minute"],
+        second=0,
+        microsecond=0,
+    )
+
+
 def next_run(job, now):
-    # job: dict with "kind", "hour", "minute" (+ "weekday" for weekly, 0 = Monday)
+    # job: dict with "kind", "hour", "minute"
+    #   (+ "weekday" for weekly, 0 = Monday; + "day" for monthly, 1-31)
     # returns the first run strictly after now
     k = job["kind"]
     if k == "daily":
@@ -20,6 +37,14 @@
         if c <= now:
             c = c + timedelta(days=7)
         return c
+    elif k == "monthly":
+        c = _monthly_run_in(now, now.year, now.month, job)
+        if c <= now:
+            if now.month == 12:
+                c = _monthly_run_in(now, now.year + 1, 1, job)
+            else:
+                c = _monthly_run_in(now, now.year, now.month + 1, job)
+        return c
     else:
         raise ValueError("unknown kind: " + str(k))
 
@@ -31,6 +56,8 @@
         return "every day at " + t
     elif k == "weekly":
         return "every " + DAYS[job["weekday"]] + " at " + t
+    elif k == "monthly":
+        return "every month on day %d at %s" % (job["day"], t)
     else:
         raise ValueError("unknown kind: " + str(k))
 
@@ -38,8 +65,8 @@
 def validate(job):
     errors = []
     k = job.get("kind")
-    if k != "daily" and k != "weekly":
-        errors.append("kind must be daily or weekly")
+    if k != "daily" and k != "weekly" and k != "monthly":
+        errors.append("kind must be daily, weekly or monthly")
     h = job.get("hour")
     if not isinstance(h, int) or h < 0 or h > 23:
         errors.append("hour must be 0-23")
@@ -50,4 +77,8 @@
         w = job.get("weekday")
         if not isinstance(w, int) or w < 0 or w > 6:
             errors.append("weekday must be 0-6")
+    if k == "monthly":
+        d = job.get("day")
+        if not isinstance(d, int) or d < 1 or d > 31:
+            errors.append("day must be 1-31")
     return errors
diff -ruN before/tests/test_schedule.py after/tests/test_schedule.py
--- before/tests/test_schedule.py
+++ after/tests/test_schedule.py
@@ -15,3 +15,66 @@
 
 def test_valid_daily_job_has_no_errors():
     assert validate({"kind": "daily", "hour": 0, "minute": 0}) == []
+
+
+def test_monthly_later_this_month():
+    job = {"kind": "monthly", "day": 15, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 12, 0)) == datetime(2026, 3, 15, 9, 0)
+
+
+def test_monthly_later_today():
+    job = {"kind": "monthly", "day": 10, "hour": 18, "minute": 30}
+    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 10, 18, 30)
+
+
+def test_monthly_exactly_now_moves_to_next_month():
+    job = {"kind": "monthly", "day": 10, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 4, 10, 9, 0)
+
+
+def test_monthly_day_31_runs_on_last_day_of_april():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 4, 1, 0, 0)) == datetime(2026, 4, 30, 9, 0)
+
+
+def test_monthly_day_31_runs_on_28_february():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 1, 31, 10, 0)) == datetime(2026, 2, 28, 9, 0)
+
+
+def test_monthly_day_31_runs_on_29_february_in_leap_year():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2028, 2, 1, 0, 0)) == datetime(2028, 2, 29, 9, 0)
+
+
+def test_monthly_after_short_month_returns_to_full_day():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 4, 30, 9, 0)) == datetime(2026, 5, 31, 9, 0)
+
+
+def test_monthly_wraps_into_next_year():
+    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 12, 20, 9, 0)) == datetime(2027, 1, 5, 9, 0)
+
+
+def test_monthly_description():
+    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
+    assert describe(job) == "every month on day 5 at 09:00"
+
+
+def test_valid_monthly_job_has_no_errors():
+    assert validate({"kind": "monthly", "day": 31, "hour": 9, "minute": 0}) == []
+
+
+def test_monthly_day_missing_wrong_type_or_out_of_range():
+    for day in (None, "5", 5.0, 0, 32):
+        job = {"kind": "monthly", "hour": 9, "minute": 0}
+        if day is not None:
+            job["day"] = day
+        assert validate(job) == ["day must be 1-31"]
+
+
+def test_unknown_kind_error_lists_all_kinds():
+    assert validate({"kind": "yearly", "hour": 9, "minute": 0}) == [
+        "kind must be daily, weekly or monthly"
+    ]
```

### Implementation 2

```diff
diff -ruN before/jobs/schedule.py after/jobs/schedule.py
--- before/jobs/schedule.py
+++ after/jobs/schedule.py
@@ -1,11 +1,13 @@
 # Job schedules for the task runner.
+import calendar
 from datetime import timedelta
 
 DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
 
 
 def next_run(job, now):
-    # job: dict with "kind", "hour", "minute" (+ "weekday" for weekly, 0 = Monday)
+    # job: dict with "kind", "hour", "minute"
+    #   (+ "weekday" for weekly, 0 = Monday; + "day" of the month for monthly)
     # returns the first run strictly after now
     k = job["kind"]
     if k == "daily":
@@ -20,10 +22,27 @@
         if c <= now:
             c = c + timedelta(days=7)
         return c
+    elif k == "monthly":
+        c = _monthly_run_in_month_of(job, now)
+        if c <= now:
+            c = _monthly_run_in_month_of(job, _first_day_of_next_month(now))
+        return c
     else:
         raise ValueError("unknown kind: " + str(k))
 
 
+def _monthly_run_in_month_of(job, when):
+    days_in_month = calendar.monthrange(when.year, when.month)[1]
+    day = min(job["day"], days_in_month)
+    return when.replace(day=day, hour=job["hour"], minute=job["minute"], second=0, microsecond=0)
+
+
+def _first_day_of_next_month(when):
+    if when.month == 12:
+        return when.replace(year=when.year + 1, month=1, day=1)
+    return when.replace(month=when.month + 1, day=1)
+
+
 def describe(job):
     k = job["kind"]
     t = "%02d:%02d" % (job["hour"], job["minute"])
@@ -31,6 +50,8 @@
         return "every day at " + t
     elif k == "weekly":
         return "every " + DAYS[job["weekday"]] + " at " + t
+    elif k == "monthly":
+        return "every month on day " + str(job["day"]) + " at " + t
     else:
         raise ValueError("unknown kind: " + str(k))
 
@@ -38,8 +59,8 @@
 def validate(job):
     errors = []
     k = job.get("kind")
-    if k != "daily" and k != "weekly":
-        errors.append("kind must be daily or weekly")
+    if k not in ("daily", "weekly", "monthly"):
+        errors.append("kind must be daily, weekly or monthly")
     h = job.get("hour")
     if not isinstance(h, int) or h < 0 or h > 23:
         errors.append("hour must be 0-23")
@@ -50,4 +71,8 @@
         w = job.get("weekday")
         if not isinstance(w, int) or w < 0 or w > 6:
             errors.append("weekday must be 0-6")
+    if k == "monthly":
+        day = job.get("day")
+        if not isinstance(day, int) or day < 1 or day > 31:
+            errors.append("day must be 1-31")
     return errors
diff -ruN before/tests/test_schedule.py after/tests/test_schedule.py
--- before/tests/test_schedule.py
+++ after/tests/test_schedule.py
@@ -1,5 +1,7 @@
 from datetime import datetime
 
+import pytest
+
 from jobs.schedule import describe, next_run, validate
 
 
@@ -15,3 +17,99 @@
 
 def test_valid_daily_job_has_no_errors():
     assert validate({"kind": "daily", "hour": 0, "minute": 0}) == []
+
+
+def test_daily_already_passed_runs_tomorrow():
+    job = {"kind": "daily", "hour": 8, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 11, 8, 0)
+
+
+def test_daily_at_exact_run_time_runs_tomorrow():
+    job = {"kind": "daily", "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 11, 9, 0)
+
+
+def test_weekly_later_this_week():
+    job = {"kind": "weekly", "weekday": 4, "hour": 7, "minute": 5}
+    # 2026-03-10 is a Tuesday.
+    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 13, 7, 5)
+
+
+def test_weekly_same_weekday_already_passed_runs_next_week():
+    job = {"kind": "weekly", "weekday": 1, "hour": 7, "minute": 5}
+    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 17, 7, 5)
+
+
+def test_daily_description():
+    assert describe({"kind": "daily", "hour": 18, "minute": 30}) == "every day at 18:30"
+
+
+def test_weekly_with_bad_weekday_and_time_reports_each_error():
+    job = {"kind": "weekly", "weekday": 7, "hour": 24, "minute": -1}
+    assert validate(job) == ["hour must be 0-23", "minute must be 0-59", "weekday must be 0-6"]
+
+
+def test_unknown_kind_lists_all_kinds():
+    assert validate({"kind": "yearly", "hour": 9, "minute": 0}) == [
+        "kind must be daily, weekly or monthly"
+    ]
+
+
+def test_monthly_later_this_month():
+    job = {"kind": "monthly", "day": 15, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 12, 0)) == datetime(2026, 3, 15, 9, 0)
+
+
+def test_monthly_already_passed_runs_next_month():
+    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 12, 0)) == datetime(2026, 4, 5, 9, 0)
+
+
+def test_monthly_at_exact_run_time_runs_next_month():
+    job = {"kind": "monthly", "day": 10, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 4, 10, 9, 0)
+
+
+def test_monthly_in_december_runs_in_january_of_next_year():
+    job = {"kind": "monthly", "day": 1, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 12, 20, 12, 0)) == datetime(2027, 1, 1, 9, 0)
+
+
+def test_monthly_day_31_runs_on_last_day_of_april():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 4, 2, 12, 0)) == datetime(2026, 4, 30, 9, 0)
+
+
+def test_monthly_day_31_runs_on_28_february():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 1, 31, 12, 0)) == datetime(2026, 2, 28, 9, 0)
+
+
+def test_monthly_day_31_runs_on_29_february_in_leap_year():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2028, 2, 1, 12, 0)) == datetime(2028, 2, 29, 9, 0)
+
+
+def test_monthly_after_shortened_run_uses_full_day_next_month():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 2, 28, 12, 0)) == datetime(2026, 3, 31, 9, 0)
+
+
+def test_monthly_description():
+    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
+    assert describe(job) == "every month on day 5 at 09:00"
+
+
+@pytest.mark.parametrize("day", [1, 31])
+def test_monthly_with_day_in_range_has_no_errors(day):
+    assert validate({"kind": "monthly", "day": day, "hour": 9, "minute": 0}) == []
+
+
+@pytest.mark.parametrize("day", [None, "5", 5.0, 0, 32])
+def test_monthly_with_bad_day_reports_day_error(day):
+    job = {"kind": "monthly", "day": day, "hour": 9, "minute": 0}
+    assert validate(job) == ["day must be 1-31"]
+
+
+def test_monthly_without_day_reports_day_error():
+    assert validate({"kind": "monthly", "hour": 9, "minute": 0}) == ["day must be 1-31"]
```

## Pair 2

### Implementation 1

```diff
diff -ruN before/jobs/schedule.py after/jobs/schedule.py
--- before/jobs/schedule.py
+++ after/jobs/schedule.py
@@ -1,11 +1,20 @@
 # Job schedules for the task runner.
+import calendar
 from datetime import timedelta
 
 DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
 
 
+def _monthly_run(year, month, job, now):
+    # day "day" of the given month, clamped to the month's last day
+    d = min(job["day"], calendar.monthrange(year, month)[1])
+    return now.replace(year=year, month=month, day=d,
+                       hour=job["hour"], minute=job["minute"], second=0, microsecond=0)
+
+
 def next_run(job, now):
-    # job: dict with "kind", "hour", "minute" (+ "weekday" for weekly, 0 = Monday)
+    # job: dict with "kind", "hour", "minute"
+    #   (+ "weekday" for weekly, 0 = Monday; + "day" for monthly, 1-31)
     # returns the first run strictly after now
     k = job["kind"]
     if k == "daily":
@@ -20,6 +29,12 @@
         if c <= now:
             c = c + timedelta(days=7)
         return c
+    elif k == "monthly":
+        c = _monthly_run(now.year, now.month, job, now)
+        if c <= now:
+            y, m = (now.year + 1, 1) if now.month == 12 else (now.year, now.month + 1)
+            c = _monthly_run(y, m, job, now)
+        return c
     else:
         raise ValueError("unknown kind: " + str(k))
 
@@ -31,6 +46,8 @@
         return "every day at " + t
     elif k == "weekly":
         return "every " + DAYS[job["weekday"]] + " at " + t
+    elif k == "monthly":
+        return "every month on day " + str(job["day"]) + " at " + t
     else:
         raise ValueError("unknown kind: " + str(k))
 
@@ -38,8 +55,8 @@
 def validate(job):
     errors = []
     k = job.get("kind")
-    if k != "daily" and k != "weekly":
-        errors.append("kind must be daily or weekly")
+    if k != "daily" and k != "weekly" and k != "monthly":
+        errors.append("kind must be daily, weekly or monthly")
     h = job.get("hour")
     if not isinstance(h, int) or h < 0 or h > 23:
         errors.append("hour must be 0-23")
@@ -50,4 +67,8 @@
         w = job.get("weekday")
         if not isinstance(w, int) or w < 0 or w > 6:
             errors.append("weekday must be 0-6")
+    if k == "monthly":
+        d = job.get("day")
+        if not isinstance(d, int) or d < 1 or d > 31:
+            errors.append("day must be 1-31")
     return errors
diff -ruN before/tests/test_schedule.py after/tests/test_schedule.py
--- before/tests/test_schedule.py
+++ after/tests/test_schedule.py
@@ -15,3 +15,60 @@
 
 def test_valid_daily_job_has_no_errors():
     assert validate({"kind": "daily", "hour": 0, "minute": 0}) == []
+
+
+def test_monthly_later_this_month():
+    job = {"kind": "monthly", "day": 15, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 12, 0)) == datetime(2026, 3, 15, 9, 0)
+
+
+def test_monthly_strictly_after_now():
+    job = {"kind": "monthly", "day": 15, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 15, 9, 0)) == datetime(2026, 4, 15, 9, 0)
+
+
+def test_monthly_later_same_day():
+    job = {"kind": "monthly", "day": 15, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 15, 8, 59)) == datetime(2026, 3, 15, 9, 0)
+
+
+def test_monthly_day_31_runs_on_last_day_of_short_month():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 31, 10, 0)) == datetime(2026, 4, 30, 9, 0)
+    assert next_run(job, datetime(2026, 4, 30, 9, 0)) == datetime(2026, 5, 31, 9, 0)
+
+
+def test_monthly_february_clamping():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 2, 1, 0, 0)) == datetime(2026, 2, 28, 9, 0)
+    assert next_run(job, datetime(2028, 2, 1, 0, 0)) == datetime(2028, 2, 29, 9, 0)
+    job30 = {"kind": "monthly", "day": 30, "hour": 9, "minute": 0}
+    assert next_run(job30, datetime(2026, 1, 31, 0, 0)) == datetime(2026, 2, 28, 9, 0)
+
+
+def test_monthly_rolls_over_year_end():
+    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 12, 20, 0, 0)) == datetime(2027, 1, 5, 9, 0)
+
+
+def test_monthly_description():
+    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
+    assert describe(job) == "every month on day 5 at 09:00"
+
+
+def test_valid_monthly_job_has_no_errors():
+    assert validate({"kind": "monthly", "day": 31, "hour": 9, "minute": 0}) == []
+    assert validate({"kind": "monthly", "day": 1, "hour": 9, "minute": 0}) == []
+
+
+def test_monthly_day_errors():
+    base = {"kind": "monthly", "hour": 9, "minute": 0}
+    assert validate(base) == ["day must be 1-31"]
+    for bad in (0, 32, -1, "5", 5.0, None):
+        assert validate(dict(base, day=bad)) == ["day must be 1-31"]
+
+
+def test_unknown_kind_error():
+    assert validate({"kind": "yearly", "hour": 9, "minute": 0}) == [
+        "kind must be daily, weekly or monthly"
+    ]
```

### Implementation 2

```diff
diff -ruN before/jobs/schedule.py after/jobs/schedule.py
--- before/jobs/schedule.py
+++ after/jobs/schedule.py
@@ -1,11 +1,13 @@
 # Job schedules for the task runner.
+import calendar
 from datetime import timedelta
 
 DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
 
 
 def next_run(job, now):
-    # job: dict with "kind", "hour", "minute" (+ "weekday" for weekly, 0 = Monday)
+    # job: dict with "kind", "hour", "minute"
+    # (+ "weekday" for weekly, 0 = Monday; + "day" for monthly, 1-31)
     # returns the first run strictly after now
     k = job["kind"]
     if k == "daily":
@@ -20,10 +22,28 @@
         if c <= now:
             c = c + timedelta(days=7)
         return c
+    elif k == "monthly":
+        run = _monthly_run_in_month_of(now, job)
+        if run <= now:
+            # The 1st of any month plus 31 days always falls in the following month.
+            run = _monthly_run_in_month_of(now.replace(day=1) + timedelta(days=31), job)
+        return run
     else:
         raise ValueError("unknown kind: " + str(k))
 
 
+def _monthly_run_in_month_of(date, job):
+    # Months with fewer than job["day"] days run on their last day.
+    last_day = calendar.monthrange(date.year, date.month)[1]
+    return date.replace(
+        day=min(job["day"], last_day),
+        hour=job["hour"],
+        minute=job["minute"],
+        second=0,
+        microsecond=0,
+    )
+
+
 def describe(job):
     k = job["kind"]
     t = "%02d:%02d" % (job["hour"], job["minute"])
@@ -31,6 +51,8 @@
         return "every day at " + t
     elif k == "weekly":
         return "every " + DAYS[job["weekday"]] + " at " + t
+    elif k == "monthly":
+        return "every month on day " + str(job["day"]) + " at " + t
     else:
         raise ValueError("unknown kind: " + str(k))
 
@@ -38,8 +60,8 @@
 def validate(job):
     errors = []
     k = job.get("kind")
-    if k != "daily" and k != "weekly":
-        errors.append("kind must be daily or weekly")
+    if k not in ("daily", "weekly", "monthly"):
+        errors.append("kind must be daily, weekly or monthly")
     h = job.get("hour")
     if not isinstance(h, int) or h < 0 or h > 23:
         errors.append("hour must be 0-23")
@@ -50,4 +72,8 @@
         w = job.get("weekday")
         if not isinstance(w, int) or w < 0 or w > 6:
             errors.append("weekday must be 0-6")
+    if k == "monthly":
+        d = job.get("day")
+        if not isinstance(d, int) or d < 1 or d > 31:
+            errors.append("day must be 1-31")
     return errors
diff -ruN before/tests/test_schedule.py after/tests/test_schedule.py
--- before/tests/test_schedule.py
+++ after/tests/test_schedule.py
@@ -1,5 +1,7 @@
 from datetime import datetime
 
+import pytest
+
 from jobs.schedule import describe, next_run, validate
 
 
@@ -15,3 +17,99 @@
 
 def test_valid_daily_job_has_no_errors():
     assert validate({"kind": "daily", "hour": 0, "minute": 0}) == []
+
+
+def test_daily_at_exactly_now_runs_tomorrow():
+    job = {"kind": "daily", "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 11, 9, 0)
+
+
+def test_weekly_already_passed_this_week_runs_next_week():
+    job = {"kind": "weekly", "weekday": 1, "hour": 8, "minute": 0}
+    tuesday_after_run = datetime(2026, 3, 10, 9, 0)
+    assert next_run(job, tuesday_after_run) == datetime(2026, 3, 17, 8, 0)
+
+
+def test_daily_description():
+    assert describe({"kind": "daily", "hour": 18, "minute": 30}) == "every day at 18:30"
+
+
+def test_weekly_job_with_bad_weekday_is_invalid():
+    job = {"kind": "weekly", "weekday": 7, "hour": 8, "minute": 0}
+    assert validate(job) == ["weekday must be 0-6"]
+
+
+def test_unknown_kind_is_rejected_by_next_run_and_describe():
+    job = {"kind": "yearly", "hour": 8, "minute": 0}
+    with pytest.raises(ValueError, match="unknown kind: yearly"):
+        next_run(job, datetime(2026, 3, 10, 9, 0))
+    with pytest.raises(ValueError, match="unknown kind: yearly"):
+        describe(job)
+
+
+def test_unknown_kind_is_invalid():
+    assert validate({"kind": "yearly", "hour": 8, "minute": 0}) == [
+        "kind must be daily, weekly or monthly"
+    ]
+
+
+def test_monthly_later_this_month():
+    job = {"kind": "monthly", "day": 15, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 12, 0)) == datetime(2026, 3, 15, 9, 0)
+
+
+def test_monthly_at_exactly_now_runs_next_month():
+    job = {"kind": "monthly", "day": 10, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 4, 10, 9, 0)
+
+
+def test_monthly_in_december_after_run_rolls_over_to_january():
+    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 12, 20, 9, 0)) == datetime(2027, 1, 5, 9, 0)
+
+
+def test_monthly_day_31_runs_on_last_day_of_30_day_month():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 4, 2, 9, 0)) == datetime(2026, 4, 30, 9, 0)
+
+
+def test_monthly_day_31_runs_on_28_february_in_common_year():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 2, 1, 9, 0)) == datetime(2026, 2, 28, 9, 0)
+
+
+def test_monthly_day_31_runs_on_29_february_in_leap_year():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2028, 2, 1, 9, 0)) == datetime(2028, 2, 29, 9, 0)
+
+
+def test_monthly_after_short_month_run_returns_to_requested_day():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    just_after_april_run = datetime(2026, 4, 30, 9, 1)
+    assert next_run(job, just_after_april_run) == datetime(2026, 5, 31, 9, 0)
+
+
+def test_monthly_from_31st_into_shorter_month():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 1, 31, 10, 0)) == datetime(2026, 2, 28, 9, 0)
+
+
+def test_monthly_description():
+    assert describe({"kind": "monthly", "day": 5, "hour": 9, "minute": 0}) == (
+        "every month on day 5 at 09:00"
+    )
+
+
+@pytest.mark.parametrize("day", [1, 31])
+def test_monthly_job_with_day_at_boundary_is_valid(day):
+    assert validate({"kind": "monthly", "day": day, "hour": 9, "minute": 0}) == []
+
+
+@pytest.mark.parametrize("day", [0, 32, "5", None])
+def test_monthly_job_with_bad_day_is_invalid(day):
+    job = {"kind": "monthly", "day": day, "hour": 9, "minute": 0}
+    assert validate(job) == ["day must be 1-31"]
+
+
+def test_monthly_job_without_day_is_invalid():
+    assert validate({"kind": "monthly", "hour": 9, "minute": 0}) == ["day must be 1-31"]
```

## Pair 3

### Implementation 1

```diff
diff -ruN before/jobs/schedule.py after/jobs/schedule.py
--- before/jobs/schedule.py
+++ after/jobs/schedule.py
@@ -1,11 +1,20 @@
 # Job schedules for the task runner.
+import calendar
 from datetime import timedelta
 
 DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
 
 
+def _monthly_run(job, year, month, now):
+    # The run in the given month; a day past the month's end falls on its last day.
+    day = min(job["day"], calendar.monthrange(year, month)[1])
+    return now.replace(year=year, month=month, day=day,
+                       hour=job["hour"], minute=job["minute"], second=0, microsecond=0)
+
+
 def next_run(job, now):
-    # job: dict with "kind", "hour", "minute" (+ "weekday" for weekly, 0 = Monday)
+    # job: dict with "kind", "hour", "minute"
+    #   (+ "weekday" for weekly, 0 = Monday; + "day" for monthly, 1-31)
     # returns the first run strictly after now
     k = job["kind"]
     if k == "daily":
@@ -20,6 +29,16 @@
         if c <= now:
             c = c + timedelta(days=7)
         return c
+    elif k == "monthly":
+        if not 1 <= job["day"] <= 31:
+            raise ValueError("day must be 1-31")
+        c = _monthly_run(job, now.year, now.month, now)
+        if c <= now:
+            if now.month == 12:
+                c = _monthly_run(job, now.year + 1, 1, now)
+            else:
+                c = _monthly_run(job, now.year, now.month + 1, now)
+        return c
     else:
         raise ValueError("unknown kind: " + str(k))
 
@@ -31,6 +50,8 @@
         return "every day at " + t
     elif k == "weekly":
         return "every " + DAYS[job["weekday"]] + " at " + t
+    elif k == "monthly":
+        return "every month on day " + str(job["day"]) + " at " + t
     else:
         raise ValueError("unknown kind: " + str(k))
 
@@ -38,8 +59,8 @@
 def validate(job):
     errors = []
     k = job.get("kind")
-    if k != "daily" and k != "weekly":
-        errors.append("kind must be daily or weekly")
+    if k != "daily" and k != "weekly" and k != "monthly":
+        errors.append("kind must be daily, weekly or monthly")
     h = job.get("hour")
     if not isinstance(h, int) or h < 0 or h > 23:
         errors.append("hour must be 0-23")
@@ -50,4 +71,8 @@
         w = job.get("weekday")
         if not isinstance(w, int) or w < 0 or w > 6:
             errors.append("weekday must be 0-6")
+    if k == "monthly":
+        d = job.get("day")
+        if not isinstance(d, int) or d < 1 or d > 31:
+            errors.append("day must be 1-31")
     return errors
diff -ruN before/tests/test_schedule.py after/tests/test_schedule.py
--- before/tests/test_schedule.py
+++ after/tests/test_schedule.py
@@ -15,3 +15,54 @@
 
 def test_valid_daily_job_has_no_errors():
     assert validate({"kind": "daily", "hour": 0, "minute": 0}) == []
+
+
+def test_monthly_later_this_month():
+    job = {"kind": "monthly", "day": 15, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 12, 0)) == datetime(2026, 3, 15, 9, 0)
+
+
+def test_monthly_already_passed_moves_to_next_month():
+    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 5, 9, 0)) == datetime(2026, 4, 5, 9, 0)
+
+
+def test_monthly_rolls_over_the_year():
+    job = {"kind": "monthly", "day": 10, "hour": 8, "minute": 0}
+    assert next_run(job, datetime(2026, 12, 20, 8, 0)) == datetime(2027, 1, 10, 8, 0)
+
+
+def test_monthly_day_31_runs_on_last_day_of_short_month():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 4, 1, 0, 0)) == datetime(2026, 4, 30, 9, 0)
+    assert next_run(job, datetime(2026, 2, 1, 0, 0)) == datetime(2026, 2, 28, 9, 0)
+    assert next_run(job, datetime(2028, 2, 1, 0, 0)) == datetime(2028, 2, 29, 9, 0)
+
+
+def test_monthly_after_clamped_run_goes_to_next_month():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 4, 30, 9, 0)) == datetime(2026, 5, 31, 9, 0)
+    assert next_run(job, datetime(2026, 1, 31, 10, 0)) == datetime(2026, 2, 28, 9, 0)
+
+
+def test_monthly_description():
+    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
+    assert describe(job) == "every month on day 5 at 09:00"
+
+
+def test_valid_monthly_job_has_no_errors():
+    assert validate({"kind": "monthly", "day": 31, "hour": 9, "minute": 0}) == []
+
+
+def test_monthly_day_errors():
+    base = {"kind": "monthly", "hour": 9, "minute": 0}
+    assert validate(base) == ["day must be 1-31"]
+    assert validate(dict(base, day="5")) == ["day must be 1-31"]
+    assert validate(dict(base, day=0)) == ["day must be 1-31"]
+    assert validate(dict(base, day=32)) == ["day must be 1-31"]
+
+
+def test_unknown_kind_error():
+    assert validate({"kind": "yearly", "hour": 9, "minute": 0}) == [
+        "kind must be daily, weekly or monthly"
+    ]
```

### Implementation 2

```diff
diff -ruN before/jobs/schedule.py after/jobs/schedule.py
--- before/jobs/schedule.py
+++ after/jobs/schedule.py
@@ -1,11 +1,13 @@
 # Job schedules for the task runner.
+import calendar
 from datetime import timedelta
 
 DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
 
 
 def next_run(job, now):
-    # job: dict with "kind", "hour", "minute" (+ "weekday" for weekly, 0 = Monday)
+    # job: dict with "kind", "hour", "minute"
+    # (+ "weekday" for weekly, 0 = Monday; + "day" of the month for monthly, 1-31)
     # returns the first run strictly after now
     k = job["kind"]
     if k == "daily":
@@ -20,10 +22,36 @@
         if c <= now:
             c = c + timedelta(days=7)
         return c
+    elif k == "monthly":
+        return _next_monthly_run(job, now)
     else:
         raise ValueError("unknown kind: " + str(k))
 
 
+def _next_monthly_run(job, now):
+    run = _monthly_run_in_month_of(job, now)
+    if run <= now:
+        run = _monthly_run_in_month_of(job, _first_of_next_month(now))
+    return run
+
+
+def _monthly_run_in_month_of(job, moment):
+    days_in_month = calendar.monthrange(moment.year, moment.month)[1]
+    return moment.replace(
+        day=min(job["day"], days_in_month),
+        hour=job["hour"],
+        minute=job["minute"],
+        second=0,
+        microsecond=0,
+    )
+
+
+def _first_of_next_month(moment):
+    if moment.month == 12:
+        return moment.replace(year=moment.year + 1, month=1, day=1)
+    return moment.replace(month=moment.month + 1, day=1)
+
+
 def describe(job):
     k = job["kind"]
     t = "%02d:%02d" % (job["hour"], job["minute"])
@@ -31,6 +59,8 @@
         return "every day at " + t
     elif k == "weekly":
         return "every " + DAYS[job["weekday"]] + " at " + t
+    elif k == "monthly":
+        return "every month on day " + str(job["day"]) + " at " + t
     else:
         raise ValueError("unknown kind: " + str(k))
 
@@ -38,8 +68,8 @@
 def validate(job):
     errors = []
     k = job.get("kind")
-    if k != "daily" and k != "weekly":
-        errors.append("kind must be daily or weekly")
+    if k not in ("daily", "weekly", "monthly"):
+        errors.append("kind must be daily, weekly or monthly")
     h = job.get("hour")
     if not isinstance(h, int) or h < 0 or h > 23:
         errors.append("hour must be 0-23")
@@ -50,4 +80,8 @@
         w = job.get("weekday")
         if not isinstance(w, int) or w < 0 or w > 6:
             errors.append("weekday must be 0-6")
+    if k == "monthly":
+        day = job.get("day")
+        if not isinstance(day, int) or day < 1 or day > 31:
+            errors.append("day must be 1-31")
     return errors
diff -ruN before/tests/test_schedule.py after/tests/test_schedule.py
--- before/tests/test_schedule.py
+++ after/tests/test_schedule.py
@@ -1,5 +1,7 @@
 from datetime import datetime
 
+import pytest
+
 from jobs.schedule import describe, next_run, validate
 
 
@@ -8,10 +10,120 @@
     assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 10, 18, 30)
 
 
+def test_daily_already_passed_runs_tomorrow():
+    job = {"kind": "daily", "hour": 8, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 11, 8, 0)
+
+
+def test_daily_at_exact_run_time_runs_tomorrow():
+    job = {"kind": "daily", "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 11, 9, 0)
+
+
+def test_weekly_later_this_week():
+    job = {"kind": "weekly", "weekday": 4, "hour": 7, "minute": 5}
+    # 2026-03-10 is a Tuesday.
+    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 13, 7, 5)
+
+
+def test_weekly_already_passed_today_runs_next_week():
+    job = {"kind": "weekly", "weekday": 1, "hour": 7, "minute": 5}
+    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 3, 17, 7, 5)
+
+
+def test_monthly_later_this_month():
+    job = {"kind": "monthly", "day": 15, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 12, 0)) == datetime(2026, 3, 15, 9, 0)
+
+
+def test_monthly_already_passed_runs_next_month():
+    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 12, 0)) == datetime(2026, 4, 5, 9, 0)
+
+
+def test_monthly_at_exact_run_time_runs_next_month():
+    job = {"kind": "monthly", "day": 10, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 3, 10, 9, 0)) == datetime(2026, 4, 10, 9, 0)
+
+
+def test_monthly_in_december_runs_in_january_of_next_year():
+    job = {"kind": "monthly", "day": 1, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 12, 15, 9, 0)) == datetime(2027, 1, 1, 9, 0)
+
+
+@pytest.mark.parametrize(
+    "now, expected",
+    [
+        (datetime(2026, 4, 1), datetime(2026, 4, 30, 9, 0)),
+        (datetime(2026, 2, 1), datetime(2026, 2, 28, 9, 0)),
+        (datetime(2028, 2, 1), datetime(2028, 2, 29, 9, 0)),
+    ],
+)
+def test_monthly_runs_on_last_day_of_shorter_month(now, expected):
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, now) == expected
+
+
+def test_monthly_returns_to_configured_day_after_shorter_month():
+    job = {"kind": "monthly", "day": 31, "hour": 9, "minute": 0}
+    assert next_run(job, datetime(2026, 4, 30, 10, 0)) == datetime(2026, 5, 31, 9, 0)
+
+
+def test_next_run_rejects_unknown_kind():
+    with pytest.raises(ValueError, match="unknown kind: hourly"):
+        next_run({"kind": "hourly", "hour": 9, "minute": 0}, datetime(2026, 3, 10))
+
+
+def test_daily_description():
+    assert describe({"kind": "daily", "hour": 9, "minute": 0}) == "every day at 09:00"
+
+
 def test_weekly_description():
     job = {"kind": "weekly", "weekday": 0, "hour": 7, "minute": 5}
     assert describe(job) == "every Monday at 07:05"
 
 
+def test_monthly_description():
+    job = {"kind": "monthly", "day": 5, "hour": 9, "minute": 0}
+    assert describe(job) == "every month on day 5 at 09:00"
+
+
+def test_describe_rejects_unknown_kind():
+    with pytest.raises(ValueError, match="unknown kind: hourly"):
+        describe({"kind": "hourly", "hour": 9, "minute": 0})
+
+
 def test_valid_daily_job_has_no_errors():
     assert validate({"kind": "daily", "hour": 0, "minute": 0}) == []
+
+
+def test_daily_job_reports_out_of_range_time():
+    assert validate({"kind": "daily", "hour": 24, "minute": 60}) == [
+        "hour must be 0-23",
+        "minute must be 0-59",
+    ]
+
+
+def test_weekly_job_reports_missing_weekday():
+    assert validate({"kind": "weekly", "hour": 9, "minute": 0}) == ["weekday must be 0-6"]
+
+
+@pytest.mark.parametrize("day", [1, 31])
+def test_valid_monthly_job_has_no_errors(day):
+    assert validate({"kind": "monthly", "day": day, "hour": 9, "minute": 0}) == []
+
+
+def test_monthly_job_reports_missing_day():
+    assert validate({"kind": "monthly", "hour": 9, "minute": 0}) == ["day must be 1-31"]
+
+
+@pytest.mark.parametrize("day", ["5", 0, 32])
+def test_monthly_job_reports_invalid_day(day):
+    job = {"kind": "monthly", "day": day, "hour": 9, "minute": 0}
+    assert validate(job) == ["day must be 1-31"]
+
+
+def test_unknown_kind_is_reported():
+    assert validate({"kind": "hourly", "hour": 9, "minute": 0}) == [
+        "kind must be daily, weekly or monthly"
+    ]
```
