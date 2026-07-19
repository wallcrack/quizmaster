import os
import uuid
from pathlib import Path

from flask import (
    Blueprint,
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename

from extensions import db
from models import Difficulty, Question, QuestionType, Tag
from services.import_service import import_questions

bp = Blueprint("question", __name__, url_prefix="/questions")


ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}


def allowed_image(filename):
    return Path(filename).suffix.lower() in ALLOWED_IMAGE_EXTENSIONS


def save_image(file):
    if not file or not file.filename:
        return None
    if not allowed_image(file.filename):
        return None

    ext = Path(file.filename).suffix.lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = Path(current_app.config["UPLOAD_FOLDER"]) / filename
    file.save(filepath)
    return filename


def delete_image(filename):
    if not filename:
        return
    filepath = Path(current_app.config["UPLOAD_FOLDER"]) / filename
    if filepath.exists():
        try:
            os.remove(filepath)
        except OSError:
            pass


QUESTION_TYPES = [
    ("single", "单选题"),
    ("multiple", "多选题"),
    ("true_false", "判断题"),
    ("subjective", "主观题"),
]

DIFFICULTIES = [
    ("easy", "简单"),
    ("medium", "中等"),
    ("hard", "困难"),
]


@bp.route("/")
@login_required
def list_questions():
    query = Question.query

    qtype = request.args.get("type")
    if qtype:
        query = query.filter(Question.type == QuestionType(qtype))

    chapter = request.args.get("chapter", "").strip()
    if chapter:
        query = query.filter(Question.chapter.ilike(f"%{chapter}%"))

    source = request.args.get("source", "").strip()
    if source:
        query = query.filter(Question.source.ilike(f"%{source}%"))

    tag_name = request.args.get("tag", "").strip()
    if tag_name:
        query = query.join(Question.tags).filter(Tag.name == tag_name)

    page = request.args.get("page", 1, type=int)
    pagination = query.order_by(Question.id.desc()).paginate(
        page=page, per_page=current_app.config["QUESTIONS_PER_PAGE"], error_out=False
    )

    tags = Tag.query.order_by(Tag.name).all()
    return render_template(
        "question/list.html",
        questions=pagination.items,
        pagination=pagination,
        types=QUESTION_TYPES,
        difficulties=DIFFICULTIES,
        tags=tags,
        filters=request.args,
    )


@bp.route("/new", methods=("GET", "POST"))
@login_required
def create():
    if request.method == "POST":
        question = _question_from_form(Question())
        if question:
            db.session.add(question)
            db.session.commit()
            flash("题目已创建。", "success")
            return redirect(url_for("question.list_questions"))

    tags = Tag.query.order_by(Tag.name).all()
    return render_template(
        "question/form.html",
        question=None,
        types=QUESTION_TYPES,
        difficulties=DIFFICULTIES,
        tags=tags,
    )


@bp.route("/<int:id>/edit", methods=("GET", "POST"))
@login_required
def edit(id):
    question = Question.query.get_or_404(id)
    if question.created_by != current_user.id:
        abort(403)

    if request.method == "POST":
        if _question_from_form(question):
            db.session.commit()
            flash("题目已更新。", "success")
            return redirect(url_for("question.list_questions"))

    tags = Tag.query.order_by(Tag.name).all()
    return render_template(
        "question/form.html",
        question=question,
        types=QUESTION_TYPES,
        difficulties=DIFFICULTIES,
        tags=tags,
    )


@bp.route("/<int:id>/delete", methods=("POST",))
@login_required
def delete(id):
    question = Question.query.get_or_404(id)
    if question.created_by != current_user.id:
        abort(403)
    delete_image(question.image)
    db.session.delete(question)
    db.session.commit()
    flash("题目已删除。", "success")
    return redirect(url_for("question.list_questions"))


@bp.route("/import", methods=("GET", "POST"))
@login_required
def import_page():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("请选择文件。", "danger")
            return redirect(url_for("question.import_page"))

        ext = Path(file.filename).suffix.lower()
        content = file.read().decode("utf-8")
        created, errors = import_questions(content, ext, current_user.id)

        if created:
            flash(f"成功导入 {created} 道题目。", "success")
        if errors:
            for err in errors[:10]:
                flash(err, "warning")

        return redirect(url_for("question.list_questions"))

    return render_template("question/import.html")


def _question_from_form(question):
    qtype = request.form.get("type")
    content = request.form.get("content", "").strip()
    answer = request.form.get("answer", "").strip()
    explanation = request.form.get("explanation", "").strip() or None
    difficulty = request.form.get("difficulty", "medium")
    source = request.form.get("source", "").strip() or None
    chapter = request.form.get("chapter", "").strip() or None
    tag_ids = request.form.getlist("tags", type=int)

    if not content:
        flash("题干不能为空。", "danger")
        return None

    if qtype in ("single", "multiple", "true_false") and not answer:
        flash("客观题必须填写正确答案。", "danger")
        return None

    options = None
    if qtype in ("single", "multiple"):
        raw_options = request.form.get("options", "").strip().splitlines()
        options = [opt.strip() for opt in raw_options if opt.strip()]
        if len(options) < 2:
            flash("选择题至少需要两个选项。", "danger")
            return None

    try:
        question.type = QuestionType(qtype)
    except ValueError:
        flash("无效的题型。", "danger")
        return None

    question.content = content
    question.options = options
    question.answer = answer
    question.explanation = explanation
    question.difficulty = Difficulty(difficulty)
    question.source = source
    question.chapter = chapter
    question.created_by = current_user.id

    # Handle image upload
    image_file = request.files.get("image")
    if image_file and image_file.filename:
        if not allowed_image(image_file.filename):
            flash("仅支持 png/jpg/jpeg/gif/webp 图片格式。", "danger")
            return None
        # Delete old image if replacing
        if question.image:
            delete_image(question.image)
        question.image = save_image(image_file)
    elif request.form.get("remove_image") == "1":
        delete_image(question.image)
        question.image = None

    # Update tags
    question.tags = []
    for tag_id in tag_ids:
        tag = db.session.get(Tag, tag_id)
        if tag:
            question.tags.append(tag)

    return question
