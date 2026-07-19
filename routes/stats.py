from flask import Blueprint, render_template
from flask_login import current_user, login_required

from services import stats_service

bp = Blueprint("stats", __name__, url_prefix="/stats")


@bp.route("/")
@login_required
def index():
    overview = stats_service.get_overview_stats(current_user.id)
    tag_stats = stats_service.get_tag_stats(current_user.id)
    weak_points = stats_service.get_weak_points(current_user.id)

    return render_template(
        "stats/index.html",
        overview=overview,
        tag_stats=tag_stats,
        weak_points=weak_points,
    )
