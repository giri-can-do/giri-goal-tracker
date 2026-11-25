from math import isfinite
from app.calendar import monday, tokyo_today

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from app.models import Goal, Activity, DailyEntry


today_bp = Blueprint("today", __name__)


@today_bp.route("/")
@login_required
def index():
    today = tokyo_today()

    activities = (
        Activity.query
        .join(Activity.goal)
        .filter(
            Activity.is_active.is_(True),
            Activity.goal.has(
                user_id=current_user.id,
                status="active"
            ),
            Activity.goal.has(
                Goal.start_date <= today
            )
        )
        .all()
    )

    # Only include activities scheduled for today.
    activities = [
        activity
        for activity in activities
        if activity.is_scheduled_for(today)
    ]

    entries = {
        entry.activity_id: entry
        for entry in DailyEntry.query
        .filter(
            DailyEntry.activity_id.in_(
                [activity.id for activity in activities]
            ),
            DailyEntry.entry_date == today
        )
        .all()
    } if activities else {}

    weekly = [activity for activity in activities if activity.target_on(today).frequency == "weekly"]
    activities = [activity for activity in activities if activity not in weekly]
    week_start = monday(today)
    weekly_totals = dict(
        db.session.query(DailyEntry.activity_id, db.func.sum(DailyEntry.value))
        .filter(DailyEntry.activity_id.in_([activity.id for activity in weekly]),
                DailyEntry.entry_date.between(week_start, today))
        .group_by(DailyEntry.activity_id).all()
    )
    total_activities = len(activities)

    completed_activities = sum(
        1
        for activity in activities
        if activity.is_completed(
            entries.get(activity.id)
        )
    )

    if total_activities:
        day_completion_percentage = round(
            (completed_activities / total_activities) * 100
        )
    else:
        day_completion_percentage = 0

    return render_template(
        "today/index.html",
        user=current_user,
        today=today,
        activities=activities,
        entries=entries,
        weekly=weekly,
        weekly_totals=weekly_totals,
        total_activities=total_activities,
        completed_activities=completed_activities,
        day_completion_percentage=day_completion_percentage
    )


@today_bp.route("/activities/<int:activity_id>/check-in", methods=["POST"])
@login_required
def check_in(activity_id):
    today = tokyo_today()

    activity = (
        Activity.query
        .filter_by(id=activity_id, is_active=True)
        .filter(
            Activity.goal.has(
                user_id=current_user.id,
                status="active"
            )
        )
        .first_or_404()
    )

    if today < activity.goal.start_date or not activity.is_scheduled_for(today):
        return redirect(url_for("today.index"))

    value_raw = request.form.get("value", "").strip()

    try:
        if activity.target_on(today).measurement_type == "boolean":
            value = 1.0
        else:
            value = float(value_raw)

            if not isfinite(value) or value < 0:
                raise ValueError

    except ValueError:
        flash("Please enter a valid progress value.", "danger")
        return redirect(url_for("today.index"))

    entry = DailyEntry.query.filter_by(
        activity_id=activity.id,
        entry_date=today
    ).first()

    if entry:
        entry.value = value
    else:
        entry = DailyEntry(
            activity_id=activity.id,
            entry_date=today,
            value=value
        )
        db.session.add(entry)

    db.session.commit()

    flash("Today's progress updated.", "success")

    return redirect(url_for("today.index"))
