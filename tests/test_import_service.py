import json

from extensions import db
from models import Question, QuestionType, User
from services.import_service import import_questions


def create_test_user():
    user = User(username="importuser", password_hash="hash")
    db.session.add(user)
    db.session.commit()
    return user


def test_import_yaml(app):
    yaml_content = """
questions:
  - type: single
    content: "Test question 1"
    options: ["A", "B"]
    answer: "0"
    difficulty: easy
    chapter: "Chapter 1"
    tags: ["test", "yaml"]
  - type: subjective
    content: "Test subjective"
    answer: "Reference answer"
    difficulty: hard
    tags: ["test"]
"""

    with app.app_context():
        user = create_test_user()
        created, errors = import_questions(yaml_content, ".yaml", user.id)
        assert created == 2
        assert len(errors) == 0

        questions = Question.query.all()
        assert len(questions) == 2
        assert questions[0].type == QuestionType.single
        assert questions[0].chapter == "Chapter 1"
        assert len(questions[0].tags) == 2


def test_import_json(app):
    json_content = json.dumps({
        "questions": [
            {
                "type": "multiple",
                "content": "Test multiple",
                "options": ["A", "B", "C"],
                "answer": "0,1",
                "difficulty": "medium",
                "tags": ["json"]
            }
        ]
    })

    with app.app_context():
        user = create_test_user()
        created, errors = import_questions(json_content, ".json", user.id)
        assert created == 1
        assert len(errors) == 0

        q = Question.query.first()
        assert q.type == QuestionType.multiple
        assert q.answer == "0,1"


def test_import_markdown(app):
    md_content = """---
type: single
difficulty: easy
chapter: 第1章
tags: [python, markdown]
options:
  - A
  - B
answer: "0"
explanation: Test explanation
---
这是题干内容，支持 **Markdown** 和 $E=mc^2$。
---
type: subjective
difficulty: medium
tags: [test]
---
这是主观题题干。
---
"""

    with app.app_context():
        user = create_test_user()
        created, errors = import_questions(md_content, ".md", user.id)
        assert created == 2
        assert len(errors) == 0

        questions = Question.query.all()
        assert len(questions) == 2
        assert questions[0].type == QuestionType.single
        assert "Markdown" in questions[0].content
        assert questions[1].type == QuestionType.subjective


def test_import_invalid_type(app):
    content = """
questions:
  - type: invalid_type
    content: "Invalid"
    answer: "0"
"""

    with app.app_context():
        user = create_test_user()
        created, errors = import_questions(content, ".yaml", user.id)
        assert created == 0
        assert len(errors) == 1
        assert "不支持的题型" in errors[0]


def test_import_unsupported_file(app):
    with app.app_context():
        user = create_test_user()
        created, errors = import_questions("test", ".txt", user.id)
        assert created == 0
        assert len(errors) == 1
        assert "仅支持" in errors[0]
