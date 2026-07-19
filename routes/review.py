from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import AnswerRecord, MasteryLevel, PracticeSession, QuestionType

bp = Blueprint("review", __name__, url_prefix="/review")


@bp.route("/wrong")
@login_required
def wrong():
    """Show wrong answers (objective wrong or subjective < 60)."""
    records = (
        db.session.query(AnswerRecord)
        .join(PracticeSession)
        .filter(PracticeSession.user_id == current_user.id)
        .filter(
            (AnswerRecord.is_correct == False)
            | ((AnswerRecord.question.has(type=QuestionType.subjective)) & (AnswerRecord.self_evaluation < 60))
        )
        .order_by(AnswerRecord.created_at.desc())
        .all()
    )

    return render_template("review/wrong.html", records=records)


@bp.route("/notes")
@login_required
def notes():
    """Show all answer records that have notes."""
    records = (
        db.session.query(AnswerRecord)
        .join(PracticeSession)
        .filter(PracticeSession.user_id == current_user.id)
        .filter(AnswerRecord.note.isnot(None))
        .order_by(AnswerRecord.created_at.desc())
        .all()
    )

    return render_template("review/notes.html", records=records)


@bp.route("/records/<int:record_id>/update", methods=("POST",))
@login_required
def update_record(record_id):
    """Update note and mastery level for an answer record."""
    record = AnswerRecord.query.get_or_404(record_id)
    if record.session.user_id != current_user.id:
        flash("无权修改该记录。", "danger")
        return redirect(url_for("review.wrong"))

    note = request.form.get("note", "").strip()
    mastery = request.form.get("mastery", "unknown")

    record.note = note or None
    try:
        record.mastery_level = MasteryLevel(mastery)
    except ValueError:
        record.mastery_level = MasteryLevel.unknown

    db.session.commit()
    flash("已更新。", "success")
    return redirect(request.referrer or url_for("review.wrong"))
