from datetime import date, datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user

from app import db
from app.models import Goal, Activity


goals_bp = Blueprint("goals", __name__, url_prefix="/goals")


@goals_bp.route("/")
@login_required
def index():
    goals = (
        Goal.query
        .filter_by(user_id=current_user.id)
        .order_by(Goal.created_at.desc())
        .all()
    )

    return render_template(
        "goals/index.html",
        goals=goals
    )


@goals_bp.route("/new", methods=["GET", "POST"])
@login_required
def create():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        goal_type = request.form.get("goal_type", "").strip()

        target_value_raw = request.form.get("target_value", "").strip()
        unit = request.form.get("unit", "").strip()

        start_date_raw = request.form.get("start_date", "").strip()
        deadline_raw = request.form.get("deadline", "").strip()

        if not title or not goal_type or not start_date_raw:
            flash(
                "Title, goal type and start date are required.",
                "danger"
            )
            return render_template(
                "goals/create.html",
                today=date.today()
            )

        try:
            target_value = (
                float(target_value_raw)
                if target_value_raw
                else None
            )

            start_date = date.fromisoformat(start_date_raw)

            deadline = (
                date.fromisoformat(deadline_raw)
                if deadline_raw
                else None
            )

        except ValueError:
            flash("Please check the target value and dates.", "danger")
            return render_template(
                "goals/create.html",
                today=date.today()
            )

        if deadline and deadline < start_date:
            flash(
                "Deadline cannot be earlier than the start date.",
                "danger"
            )
            return render_template(
                "goals/create.html",
                today=date.today()
            )

        goal = Goal(
            user_id=current_user.id,
            title=title,
            description=description or None,
            category=category or None,
            goal_type=goal_type,
            target_value=target_value,
            unit=unit or None,
            start_date=start_date,
            deadline=deadline,
            status="active"
        )

        db.session.add(goal)
        db.session.commit()

        flash("Goal created successfully.", "success")

        return redirect(url_for("goals.index"))

    return render_template(
        "goals/create.html",
        today=date.today()
    )

@goals_bp.route("/<int:goal_id>/activities/new", methods=["GET", "POST"])
@login_required
def create_activity(goal_id):
    goal = Goal.query.filter_by(
        id=goal_id,
        user_id=current_user.id
    ).first_or_404()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        measurement_type = request.form.get("measurement_type", "").strip()
        target_value_raw = request.form.get("target_value", "").strip()
        unit = request.form.get("unit", "").strip()
        
        frequency = request.form.get("frequency", "").strip()
        valid_frequencies = {
            "daily",
            "weekdays",
            "weekends"
        }

        if frequency not in valid_frequencies:
            flash("Please select a valid frequency.", "danger")
            return redirect(request.url)

        start_date_str = request.form.get("start_date")

        start_date = datetime.strptime(
            start_date_str,
            "%Y-%m-%d"
        ).date()

        # Validate the date
        if start_date < goal.start_date:
            flash("Activity start date cannot be before the goal start date.")
            return redirect(request.url)

        if not title or not measurement_type or not frequency:
            flash(
                "Activity, measurement type and frequency are required.",
                "danger"
            )
            return render_template(
                "goals/create_activity.html",
                goal=goal
            )

        try:
            target_value = (
                float(target_value_raw)
                if target_value_raw
                else None
            )
        except ValueError:
            flash("Target must be a valid number.", "danger")
            return render_template(
                "goals/create_activity.html",
                goal=goal
            )

        if measurement_type in ("numeric", "duration"):
            if target_value is None or target_value <= 0:
                flash(
                    "Numeric and duration activities require a target greater than 0.",
                    "danger"
                )
                return render_template(
                    "goals/create_activity.html",
                    goal=goal
                )

        activity = Activity(
            goal_id=goal.id,
            title=title,
            measurement_type=measurement_type,
            target_value=target_value,
            unit=unit or None,
            frequency=frequency,
            is_active=True,
            start_date=start_date,
        )

        db.session.add(activity)
        db.session.commit()

        flash("Activity created successfully.", "success")

        return redirect(url_for("goals.index"))

    return render_template(
        "goals/create_activity.html",
        goal=goal
    )

@goals_bp.route("/<int:goal_id>/edit", methods=["GET", "POST"])
@login_required
def edit(goal_id):
    goal = Goal.query.filter_by(
        id=goal_id,
        user_id=current_user.id
    ).first_or_404()

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()
        goal_type = request.form.get("goal_type", "").strip()

        target_value_raw = request.form.get("target_value", "").strip()
        unit = request.form.get("unit", "").strip()

        start_date_raw = request.form.get("start_date", "").strip()
        deadline_raw = request.form.get("deadline", "").strip()

        if not title or not goal_type or not start_date_raw:
            flash(
                "Title, goal type and start date are required.",
                "danger"
            )
            return render_template("goals/edit.html", goal=goal)

        try:
            target_value = (
                float(target_value_raw)
                if target_value_raw
                else None
            )

            start_date = date.fromisoformat(start_date_raw)

            deadline = (
                date.fromisoformat(deadline_raw)
                if deadline_raw
                else None
            )

        except ValueError:
            flash(
                "Please check the target value and dates.",
                "danger"
            )
            return render_template("goals/edit.html", goal=goal)

        if deadline and deadline < start_date:
            flash(
                "Deadline cannot be earlier than the start date.",
                "danger"
            )
            return render_template("goals/edit.html", goal=goal)

        goal.title = title
        goal.description = description or None
        goal.category = category or None
        goal.goal_type = goal_type
        goal.target_value = target_value
        goal.unit = unit or None
        goal.start_date = start_date
        goal.deadline = deadline

        db.session.commit()

        flash("Goal updated successfully.", "success")

        return redirect(url_for("goals.index"))

    return render_template("goals/edit.html", goal=goal)

@goals_bp.route(
    "/activities/<int:activity_id>/edit",
    methods=["GET", "POST"]
)
@login_required
def edit_activity(activity_id):
    activity = (
        Activity.query
        .filter_by(id=activity_id)
        .filter(
            Activity.goal.has(
                user_id=current_user.id
            )
        )
        .first_or_404()
    )

    if request.method == "POST":
        title = request.form.get("title", "").strip()

        start_date = datetime.strptime(request.form["start_date"],"%Y-%m-%d").date()
        if start_date < activity.goal.start_date:
            flash("Activity start date cannot be before the goal start date.")
            return redirect(request.url)
        
        measurement_type = request.form.get(
            "measurement_type", ""
        ).strip()

        target_value_raw = request.form.get(
            "target_value", ""
        ).strip()

        unit = request.form.get("unit", "").strip()
        frequency = request.form.get("frequency", "").strip()
        valid_frequencies = {
            "daily",
            "weekdays",
            "weekends"
        }

        if frequency not in valid_frequencies:
            flash("Please select a valid frequency.", "danger")
            return redirect(request.url)

        if not title or not measurement_type or not frequency:
            flash(
                "Activity, measurement type and frequency are required.",
                "danger"
            )
            return render_template(
                "goals/edit_activity.html",
                activity=activity
            )

        try:
            target_value = (
                float(target_value_raw)
                if target_value_raw
                else None
            )
        except ValueError:
            flash("Target must be a valid number.", "danger")
            return render_template(
                "goals/edit_activity.html",
                activity=activity
            )

        if measurement_type in ("numeric", "duration"):
            if target_value is None or target_value <= 0:
                flash(
                    "Numeric and duration activities require "
                    "a target greater than 0.",
                    "danger"
                )
                return render_template(
                    "goals/edit_activity.html",
                    activity=activity
                )

        activity.title = title
        activity.start_date = start_date
        activity.measurement_type = measurement_type
        activity.target_value = target_value
        activity.unit = unit or None
        activity.frequency = frequency

        db.session.commit()

        flash("Activity updated successfully.", "success")

        return redirect(url_for("goals.index"))

    return render_template(
        "goals/edit_activity.html",
        activity=activity
    )

@goals_bp.route(
    "/activities/<int:activity_id>/archive",
    methods=["POST"]
)
@login_required
def archive_activity(activity_id):
    activity = (
        Activity.query
        .filter_by(id=activity_id)
        .filter(
            Activity.goal.has(
                user_id=current_user.id
            )
        )
        .first_or_404()
    )

    activity.is_active = False
    db.session.commit()

    flash("Activity archived.", "success")

    return redirect(url_for("goals.index"))


@goals_bp.route(
    "/activities/<int:activity_id>/restore",
    methods=["POST"]
)
@login_required
def restore_activity(activity_id):
    activity = (
        Activity.query
        .filter_by(id=activity_id)
        .filter(
            Activity.goal.has(
                user_id=current_user.id
            )
        )
        .first_or_404()
    )

    activity.is_active = True
    db.session.commit()

    flash("Activity restored.", "success")

    return redirect(url_for("goals.index"))