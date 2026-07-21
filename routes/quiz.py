from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from extensions import db
from models import AnswerRecord, PracticeSession, Question, QuestionType, Tag
from services import quiz_service

bp = Blueprint("quiz", __name__, url_prefix="/quiz")


@bp.route("/setup")
@login_required
def setup():
    tags = Tag.query.order_by(Tag.name).all()
    # 按来源分组章节，用于两级联动选择
    rows = (
        db.session.query(Question.source, Question.chapter)
        .filter(Question.source.isnot(None), Question.chapter.isnot(None))
        .filter(Question.source != "", Question.chapter != "")
        .distinct()
        .order_by(Question.source, Question.chapter)
        .all()
    )
    chapters_by_source = {}
    for src, ch in rows:
        chapters_by_source.setdefault(src, []).append(ch)

    return render_template(
        "quiz/setup.html",
        tags=tags,
        chapters_by_source=chapters_by_source,
    )


@bp.route("/start", methods=("POST",))
@login_required
def start():
    mode = request.form.get("mode", "random")
    count = request.form.get("count", 10, type=int)
    show_explanation = bool(request.form.get("show_explanation"))

    config = {"count": count, "show_explanation": show_explanation}

    if mode == "tag":
        tag_ids = request.form.getlist("tag_ids", type=int)
        if not tag_ids:
            flash("请至少选择一个知识点标签。", "danger")
            return redirect(url_for("quiz.setup"))
        config["tag_ids"] = tag_ids
    elif mode == "chapter":
        source = request.form.get("source", "").strip()
        chapter = request.form.get("chapter", "").strip()
        if not source and not chapter:
            flash("请选择书本或章节。", "danger")
            return redirect(url_for("quiz.setup"))
        config["source"] = source
        config["chapter"] = chapter

    session = quiz_service.start_session(current_user.id, mode, config)
    if session is None:
        flash("没有找到符合条件的题目。", "warning")
        return redirect(url_for("quiz.setup"))

    return redirect(url_for("quiz.do", session_id=session.id))


@bp.route("/<int:session_id>")
@login_required
def do(session_id):
    session = PracticeSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        flash("无权访问该练习。", "danger")
        return redirect(url_for("quiz.setup"))

    records = quiz_service.get_session_questions(session)
    if not records:
        flash("本次练习没有题目。", "warning")
        return redirect(url_for("quiz.setup"))

    # Determine current question (first unanswered)
    current_record = None
    current_index = 0
    for idx, record in enumerate(records, start=1):
        if record.user_answer is None:
            current_record = record
            current_index = idx
            break

    # If all answered, go to result
    if current_record is None:
        return redirect(url_for("quiz.result", session_id=session.id))

    return render_template(
        "quiz/do.html",
        session=session,
        records=records,
        current_record=current_record,
        current_index=current_index,
        total=len(records),
        show_explanation=session.config.get("show_explanation", False),
    )


@bp.route("/<int:session_id>/answer", methods=("POST",))
@login_required
def answer(session_id):
    session = PracticeSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        flash("无权访问该练习。", "danger")
        return redirect(url_for("quiz.setup"))

    record_id = request.form.get("record_id", type=int)
    record = db.session.get(AnswerRecord, record_id)
    if not record or record.session_id != session.id:
        flash("无效的答题记录。", "danger")
        return redirect(url_for("quiz.setup"))

    question = record.question
    if question.type == QuestionType.multiple:
        values = request.form.getlist("user_answer")
        user_answer = ",".join(values)
    else:
        user_answer = request.form.get("user_answer", "")

    quiz_service.submit_answer(record_id, user_answer)
    return redirect(url_for("quiz.do", session_id=session.id))


@bp.route("/<int:session_id>/finish", methods=("GET", "POST"))
@login_required
def finish(session_id):
    session = PracticeSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        flash("无权访问该练习。", "danger")
        return redirect(url_for("quiz.setup"))

    records = quiz_service.get_session_questions(session)
    subjective_records = [
        r for r in records if r.question.type == QuestionType.subjective
    ]

    if request.method == "POST":
        subjective_scores = {}
        for record in subjective_records:
            score = request.form.get(f"score_{record.id}", type=int)
            note = request.form.get(f"note_{record.id}", "")
            if score is not None and 0 <= score <= 100:
                subjective_scores[record.id] = {"score": score, "note": note}

        quiz_service.finish_session(session, subjective_scores)
        return redirect(url_for("quiz.result", session_id=session.id))

    return render_template(
        "quiz/finish.html",
        session=session,
        subjective_records=subjective_records,
    )


@bp.route("/<int:session_id>/result")
@login_required
def result(session_id):
    session = PracticeSession.query.get_or_404(session_id)
    if session.user_id != current_user.id:
        flash("无权访问该练习。", "danger")
        return redirect(url_for("quiz.setup"))

    summary = quiz_service.get_session_summary(session)
    return render_template("quiz/result.html", session=session, summary=summary)
