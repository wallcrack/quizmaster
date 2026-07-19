from extensions import db
from models import Difficulty, Question, QuestionType, User
from services import quiz_service


def create_test_user():
    user = User(username="quizuser", password_hash="hash")
    db.session.add(user)
    db.session.commit()
    return user


def create_test_question(user_id, qtype=QuestionType.single, answer="0", **kwargs):
    question = Question(
        type=qtype,
        content=kwargs.get("content", "Test question"),
        options=kwargs.get("options"),
        answer=answer,
        explanation=kwargs.get("explanation"),
        difficulty=kwargs.get("difficulty", Difficulty.medium),
        source=kwargs.get("source"),
        chapter=kwargs.get("chapter"),
        created_by=user_id,
    )
    db.session.add(question)
    db.session.commit()
    return question


def test_score_single_choice(app):
    with app.app_context():
        user = create_test_user()
        q = create_test_question(user.id, QuestionType.single, answer="0")

        score, is_correct = quiz_service.score_objective(q, "0")
        assert score == 100.0
        assert is_correct is True

        score, is_correct = quiz_service.score_objective(q, "1")
        assert score == 0.0
        assert is_correct is False


def test_score_multiple_choice(app):
    with app.app_context():
        user = create_test_user()
        q = create_test_question(user.id, QuestionType.multiple, answer="0,1,2")

        # All correct
        score, is_correct = quiz_service.score_objective(q, "0,1,2")
        assert score == 100.0
        assert is_correct is True

        # Partial correct (subset, no wrong)
        score, is_correct = quiz_service.score_objective(q, "0,1")
        assert score == 50.0
        assert is_correct is False

        # With wrong option
        score, is_correct = quiz_service.score_objective(q, "0,1,3")
        assert score == 0.0
        assert is_correct is False


def test_score_true_false(app):
    with app.app_context():
        user = create_test_user()
        q = create_test_question(user.id, QuestionType.true_false, answer="正确")

        score, is_correct = quiz_service.score_objective(q, "正确")
        assert score == 100.0
        assert is_correct is True

        score, is_correct = quiz_service.score_objective(q, "错误")
        assert score == 0.0
        assert is_correct is False


def test_start_session_random(app):
    with app.app_context():
        user = create_test_user()
        for i in range(5):
            create_test_question(user.id, QuestionType.single, answer="0")

        session = quiz_service.start_session(user.id, "random", {"count": 3, "show_explanation": False})
        assert session is not None
        assert session.user_id == user.id
        assert session.mode.value == "random"

        records = quiz_service.get_session_questions(session)
        assert len(records) == 3


def test_start_session_no_questions(app):
    with app.app_context():
        user = create_test_user()
        session = quiz_service.start_session(user.id, "random", {"count": 5, "show_explanation": False})
        assert session is None


def test_start_session_tag_mode(app):
    from models import Tag

    with app.app_context():
        user = create_test_user()
        tag = Tag(name="python")
        db.session.add(tag)
        db.session.commit()

        q = create_test_question(user.id, QuestionType.single, answer="0")
        q.tags.append(tag)
        db.session.commit()

        session = quiz_service.start_session(
            user.id, "tag", {"count": 5, "tag_ids": [tag.id], "show_explanation": False}
        )
        assert session is not None
        records = quiz_service.get_session_questions(session)
        assert len(records) == 1


def test_finish_session_updates_stats(app):
    from models import Tag

    with app.app_context():
        user = create_test_user()
        tag = Tag(name="python")
        db.session.add(tag)
        db.session.commit()

        q = create_test_question(user.id, QuestionType.single, answer="0")
        q.tags.append(tag)
        db.session.commit()

        session = quiz_service.start_session(user.id, "random", {"count": 1, "show_explanation": False})
        record = quiz_service.get_session_questions(session)[0]
        quiz_service.submit_answer(record.id, "0")
        quiz_service.finish_session(session)

        # Check session completed
        assert session.completed_at is not None

        # Check user tag stats
        from models import UserTagStats
        stats = UserTagStats.query.filter_by(user_id=user.id, tag_id=tag.id).first()
        assert stats is not None
        assert stats.total_count == 1
        assert stats.correct_count == 1
        assert stats.avg_score == 100.0
