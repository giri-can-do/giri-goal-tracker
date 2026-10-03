from flask import Blueprint, render_template
from flask_login import login_required, current_user


today_bp = Blueprint("today", __name__)


@today_bp.route("/")
@login_required
def index():
    return render_template(
        "today/index.html",
        user=current_user
    )
