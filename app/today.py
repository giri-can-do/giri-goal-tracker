from datetime import date

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from app.models import Goal, Activity, DailyEntry


today_bp = Blueprint("today", __name__)


@today_bp.route("/")
@login_required
def index():
    today = date.today()

    activities = (
        Activity.query
        .join(Activity.goal)
        .filter(
            Activity.is_active.is_(True),
            Activity.frequency == "daily",
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

    return render_template(
        "today/index.html",
        user=current_user,
        today=today,
        activities=activities,
        entries=entries
    )


@today_bp.route("/activities/<int:activity_id>/check-in", methods=["POST"])
@login_required
def check_in(activity_id):
    today = date.today()

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

    value_raw = request.form.get("value", "").strip()

    try:
        if activity.measurement_type == "boolean":
            value = 1.0
        else:
            value = float(value_raw)

            if value < 0:
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
