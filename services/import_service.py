import json

import frontmatter
import yaml

from extensions import db
from models import Question, QuestionType, Difficulty, Tag


def parse_yaml(content):
    data = yaml.safe_load(content)
    return data.get("questions", []) if isinstance(data, dict) else data


def parse_json(content):
    data = json.loads(content)
    return data.get("questions", []) if isinstance(data, dict) else data


def parse_markdown(content):
    """Parse Markdown file with YAML frontmatter blocks.

    Format:
    ---
    type: single
    difficulty: easy
    ...
    ---
    题干内容（支持 Markdown 和 LaTeX）

    Multiple questions are separated by `---` on its own line after content.
    """
    questions = []
    lines = content.split("\n")
    i = 0
    n = len(lines)

    while i < n:
        # Find start of frontmatter
        while i < n and lines[i].strip() != "---":
            i += 1
        if i >= n:
            break

        doc_start = i
        i += 1

        # Find end of frontmatter
        while i < n and lines[i].strip() != "---":
            i += 1
        if i >= n:
            break

        i += 1

        # Find end of content (next --- or EOF)
        content_start = i
        while i < n and lines[i].strip() != "---":
            i += 1
        content_end = i

        # Parse document
        doc_lines = lines[doc_start:content_end]
        doc_text = "\n".join(doc_lines)
        try:
            post = frontmatter.loads(doc_text)
            if post.metadata:
                post.metadata["content"] = post.content.strip()
                questions.append(post.metadata)
        except Exception:
            pass

    return questions


def _normalize_question(raw):
    qtype = raw.get("type", "single")
    if qtype not in [t.value for t in QuestionType]:
        raise ValueError(f"不支持的题型: {qtype}")

    difficulty = raw.get("difficulty", "medium")
    if difficulty not in [d.value for d in Difficulty]:
        difficulty = "medium"

    return {
        "type": QuestionType(qtype),
        "content": str(raw.get("content", "")),
        "options": raw.get("options") if raw.get("options") is not None else None,
        "answer": str(raw.get("answer", "")),
        "explanation": raw.get("explanation") or None,
        "difficulty": Difficulty(difficulty),
        "source": raw.get("source") or None,
        "chapter": raw.get("chapter") or None,
        "tags": raw.get("tags") or [],
        "image": raw.get("image") or None,
    }


def import_questions(content, file_extension, user_id):
    """Import questions from YAML or JSON content.

    Returns (created_count, errors).
    """
    if file_extension in (".yaml", ".yml"):
        items = parse_yaml(content)
    elif file_extension == ".json":
        items = parse_json(content)
    elif file_extension in (".md", ".markdown"):
        items = parse_markdown(content)
    else:
        return 0, ["仅支持 .yaml / .yml / .json / .md 文件"]

    if not isinstance(items, list):
        return 0, ["文件格式错误：questions 应为列表"]

    created = 0
    errors = []
    tag_cache = {}

    for idx, raw in enumerate(items, start=1):
        try:
            data = _normalize_question(raw)
        except Exception as exc:
            errors.append(f"第 {idx} 题: {exc}")
            continue

        question = Question(
            type=data["type"],
            content=data["content"],
            options=data["options"],
            answer=data["answer"],
            explanation=data["explanation"],
            difficulty=data["difficulty"],
            source=data["source"],
            chapter=data["chapter"],
            image=data["image"],
            created_by=user_id,
        )
        db.session.add(question)

        for tag_name in data["tags"]:
            tag_name = str(tag_name).strip()
            if not tag_name:
                continue
            if tag_name not in tag_cache:
                tag = Tag.query.filter_by(name=tag_name).first()
                if tag is None:
                    tag = Tag(name=tag_name)
                    db.session.add(tag)
                    db.session.flush()  # Ensure tag has an id before association
                tag_cache[tag_name] = tag
            question.tags.append(tag_cache[tag_name])

        created += 1

    db.session.commit()
    return created, errors
