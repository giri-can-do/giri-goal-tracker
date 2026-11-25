from collections import defaultdict
from datetime import timedelta

from flask import Blueprint, abort, render_template, request
from flask_login import current_user, login_required

from app.calendar import monday, tokyo_today
from app.models import Activity, DailyEntry, Goal


dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/dashboard")


@dashboard_bp.route("/")
@login_required
def index():
    today = tokyo_today()
    starts = {"week": monday(today), "month": today.replace(day=1),
              "year": today.replace(month=1, day=1)}
    view = request.args.get("view", "overview")
    if view not in ("overview", *starts):
        abort(404)
    periods = starts if view == "overview" else {view: starts[view]}
    earliest = monday(min(periods.values()))
    activities = Activity.query.join(Goal).filter(Goal.user_id == current_user.id).all()
    entries = defaultdict(dict)
    for entry in DailyEntry.query.filter(
        DailyEntry.activity_id.in_([activity.id for activity in activities]),
        DailyEntry.entry_date.between(earliest, today),
    ):
        entries[entry.activity_id][entry.entry_date] = entry

    reports = {}
    for period, start in periods.items():
        rows = []
        for activity in activities:
            first_day = max(activity.start_date, activity.goal.start_date)
            if first_day > today:
                continue
            logged = entries[activity.id]
            if not activity.is_active and not any(day >= start for day in logged):
                continue
            total = sum(entry.value for day, entry in logged.items() if day >= start)
            daily_done = daily_due = weekly_done = weekly_due = 0
            open_week = None
            day = start
            while day <= today:
                target = activity.target_on(day)
                if target.frequency == "weekly":
                    week = monday(day)
                    if day == max(start, week) and week + timedelta(days=6) >= first_day:
                        amount = sum(
                            entry.value for entry_day, entry in logged.items()
                            if max(first_day, week) <= entry_day <= week + timedelta(days=6)
                        )
                        if week == monday(today):
                            open_week = (amount, target.target_value)
                        elif (
                                week + timedelta(days=6) >= start
                                and target.target_value
                            ):
                            weekly_due += 1
                            weekly_done += amount >= target.target_value
                elif day >= first_day and activity.is_scheduled_for(day):
                    daily_due += 1
                    daily_done += activity.is_completed(logged.get(day))
                day += timedelta(days=1)
            rows.append(dict(title=activity.title, total=total,
                             unit=activity.target_on(today).unit, daily_done=daily_done,
                             daily_due=daily_due, weekly_done=weekly_done,
                             weekly_due=weekly_due, open_week=open_week))
        reports[period] = rows
    return render_template("dashboard/index.html", view=view, reports=reports)
