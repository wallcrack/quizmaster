import os
import re
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
    """保存图片（UUID 哈希命名，适用于单题表单上传）。"""
    if not file or not file.filename:
        return None
    if not allowed_image(file.filename):
        return None

    ext = Path(file.filename).suffix.lower()
    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = Path(current_app.config["UPLOAD_FOLDER"]) / filename
    file.save(filepath)
    return filename


def save_image_keep_name(file):
    """保存图片（保留原始文件名，适用于批量导入场景）。"""
    if not file or not file.filename:
        return None
    if not allowed_image(file.filename):
        return None

    filename = secure_filename(file.filename)
    if not filename:
        return None
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


def _extract_markdown_images(text):
    """从 Markdown 文本中提取图片文件名（如 ![](foo.png) → foo.png）。"""
    if not text:
        return []
    # 匹配 ![alt](filename) 或 ![](/static/uploads/filename)
    pattern = r"!\[.*?\]\((?:/static/uploads/)?([^)]+)\)"
    return re.findall(pattern, text)


def _get_referenced_images(question):
    """获取一道题目引用的所有图片文件名（image 字段 + Markdown 内联图）。"""
    files = set()
    if question.image:
        files.add(question.image)
    files.update(_extract_markdown_images(question.content or ""))
    files.update(_extract_markdown_images(question.explanation or ""))
    return files


def _is_image_used(filename):
    """检查图片是否被任意题目引用。"""
    if Question.query.filter(Question.image == filename).first():
        return True
    # 检查 Markdown 内容中的引用（用括号包裹以防部分匹配）
    pattern = f"({filename})"
    if Question.query.filter(Question.content.contains(pattern)).first():
        return True
    if Question.query.filter(Question.explanation.contains(pattern)).first():
        return True
    return False


def _cleanup_orphan_images():
    """清理上传目录中所有未被引用的图片，返回删除数量。"""
    upload_dir = Path(current_app.config["UPLOAD_FOLDER"])
    if not upload_dir.exists():
        return 0

    all_refs = set()
    for q in Question.query.all():
        all_refs.update(_get_referenced_images(q))

    deleted = 0
    for filepath in upload_dir.iterdir():
        if filepath.is_file() and filepath.name not in all_refs:
            try:
                os.remove(filepath)
                deleted += 1
            except OSError:
                pass
    return deleted


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
        query = query.filter(Question.chapter == chapter)

    source = request.args.get("source", "").strip()
    if source:
        query = query.filter(Question.source == source)

    tag_name = request.args.get("tag", "").strip()
    if tag_name:
        query = query.join(Question.tags).filter(Tag.name == tag_name)

    page = request.args.get("page", 1, type=int)

    # 排除 page 参数，避免分页链接中 page 重复
    filters = {k: v for k, v in request.args.items() if k != "page"}
    # 检查是否有筛选项（排除 page 后的非空参数）
    has_filter = any(v for k, v in request.args.items() if k != "page")

    if has_filter:
        pagination = query.order_by(Question.id.desc()).paginate(
            page=page, per_page=current_app.config["QUESTIONS_PER_PAGE"], error_out=False
        )
        questions = pagination.items
    else:
        pagination = None
        questions = []

    tags = Tag.query.order_by(Tag.name).all()
    all_sources = [
        r[0] for r in
        db.session.query(Question.source).filter(Question.source.isnot(None), Question.source != "").distinct().order_by(Question.source).all()
    ]
    # 出处→章节 两级联动数据
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
        "question/list.html",
        questions=questions,
        pagination=pagination,
        types=QUESTION_TYPES,
        difficulties=DIFFICULTIES,
        tags=tags,
        all_sources=all_sources,
        chapters_by_source=chapters_by_source,
        filters=filters,
        has_filter=has_filter,
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
    # 收集该题目引用的所有图片，删除题目后再判断是否可清理
    image_refs = _get_referenced_images(question)
    db.session.delete(question)
    db.session.commit()

    for filename in image_refs:
        if not _is_image_used(filename):
            delete_image(filename)

    # 清理无关联题目的空标签和孤儿图片
    _cleanup_orphan_tags()

    flash("题目已删除。", "success")
    return redirect(url_for("question.list_questions"))


@bp.route("/batch-delete", methods=("POST",))
@login_required
def batch_delete():
    ids = request.form.getlist("ids", type=int)
    if not ids:
        flash("未选择任何题目。", "warning")
        return redirect(url_for("question.list_questions"))

    questions = Question.query.filter(Question.id.in_(ids)).all()

    # 收集所有将被删除题目引用的图片
    all_image_refs = set()
    for q in questions:
        all_image_refs.update(_get_referenced_images(q))

    for q in questions:
        db.session.delete(q)
    db.session.commit()

    # 删除不再被任何题目引用的图片
    for filename in all_image_refs:
        if not _is_image_used(filename):
            delete_image(filename)

    # 清理无关联题目的空标签
    _cleanup_orphan_tags()

    flash(f"已删除 {len(questions)} 道题目。", "success")
    return redirect(url_for("question.list_questions"))


@bp.route("/<int:id>/preview")
@login_required
def preview(id):
    question = Question.query.get_or_404(id)

    # 构建与列表页相同的筛选查询，用于连续预览翻题
    query = Question.query

    qtype = request.args.get("type")
    if qtype:
        query = query.filter(Question.type == QuestionType(qtype))

    chapter = request.args.get("chapter", "").strip()
    if chapter:
        query = query.filter(Question.chapter == chapter)

    source = request.args.get("source", "").strip()
    if source:
        query = query.filter(Question.source == source)

    tag_name = request.args.get("tag", "").strip()
    if tag_name:
        query = query.join(Question.tags).filter(Tag.name == tag_name)

    # 获取筛选后的题目 ID 列表（与列表页同序）
    filtered_ids = [
        r[0] for r in
        query.order_by(Question.id.desc()).with_entities(Question.id).all()
    ]

    # 保留筛选参数用于导航链接
    filters = {k: v for k, v in request.args.items()}

    # 查找当前题目在筛选结果中的位置
    try:
        idx = filtered_ids.index(id)
    except ValueError:
        idx = -1

    prev_id = filtered_ids[idx - 1] if idx > 0 else None
    next_id = filtered_ids[idx + 1] if idx >= 0 and idx < len(filtered_ids) - 1 else None

    return render_template(
        "question/preview.html",
        question=question,
        types=QUESTION_TYPES,
        prev_id=prev_id,
        next_id=next_id,
        filters=filters,
        current_index=idx + 1 if idx >= 0 else 0,
        total=len(filtered_ids),
    )


def _cleanup_orphan_tags():
    """删除无题目关联的空标签。"""
    orphan_tags = Tag.query.filter(~Tag.questions.any()).all()
    for tag in orphan_tags:
        db.session.delete(tag)
    if orphan_tags:
        db.session.commit()


@bp.route("/import", methods=("GET", "POST"))
@login_required
def import_page():
    if request.method == "POST":
        file = request.files.get("file")
        if not file or not file.filename:
            flash("请选择导入文件。", "danger")
            return redirect(url_for("question.import_page"))

        # 1. 批量保存上传的图片（保留原始文件名，与导入文件中的引用一致）
        saved_images = []
        image_files = request.files.getlist("images")
        for img_file in image_files:
            if img_file and img_file.filename:
                filename = save_image_keep_name(img_file)
                if filename:
                    saved_images.append(filename)

        if saved_images:
            names = ", ".join(saved_images)
            flash(f"已保存 {len(saved_images)} 张图片：{names}", "info")

        # 2. 解析并导入题目
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
