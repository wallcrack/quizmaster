import datetime
from itertools import chain

from sqlalchemy import func

from extensions import db
from models import (
    AnswerRecord,
    Difficulty,
    MasteryLevel,
    PracticeMode,
    PracticeSession,
    Question,
    QuestionType,
    Tag,
    UserTagStats,
)


def start_session(user_id, mode, config):
    """Create a practice session and pre-generate answer records.

    mode: random | tag | chapter | wrong
    config: dict with keys like count, tag_ids, chapter, source, show_explanation
    """
    mode_enum = PracticeMode(mode)
    count = int(config.get("count", 10))

    query = Question.query

    if mode_enum == PracticeMode.tag:
        tag_ids = config.get("tag_ids") or []
        if tag_ids:
            query = query.join(Question.tags).filter(Tag.id.in_(tag_ids))
    elif mode_enum == PracticeMode.chapter:
        chapter = config.get("chapter", "").strip()
        if chapter:
            query = query.filter(Question.chapter.ilike(f"%{chapter}%"))
    elif mode_enum == PracticeMode.wrong:
        # Load recent wrong answers (objective wrong or subjective < 60)
        wrong_subquery = (
            db.session.query(AnswerRecord.question_id)
            .filter(AnswerRecord.session.has(user_id=user_id))
            .filter(
                (AnswerRecord.is_correct == False)
                | (AnswerRecord.self_evaluation < 60)
            )
            .distinct()
            .subquery()
        )
        query = query.filter(Question.id.in_(wrong_subquery))

    questions = query.order_by(func.random()).limit(count).all()

    if not questions:
        return None

    session = PracticeSession(
        user_id=user_id,
        mode=mode_enum,
        config={
            "count": count,
            "show_explanation": config.get("show_explanation", False),
            "tag_ids": config.get("tag_ids") or [],
            "chapter": config.get("chapter", ""),
            "source": config.get("source", ""),
        },
    )
    db.session.add(session)
    db.session.flush()  # Generate session.id before creating records

    for question in questions:
        record = AnswerRecord(session_id=session.id, question_id=question.id)
        db.session.add(record)

    db.session.commit()
    return session


def get_session_questions(session):
    """Return ordered questions for a session."""
    records = (
        AnswerRecord.query.filter_by(session_id=session.id)
        .order_by(AnswerRecord.id)
        .all()
    )
    return records


def score_objective(question, user_answer):
    """Return (score, is_correct) for an objective question."""
    if question.type == QuestionType.true_false:
        correct = str(user_answer).strip().lower() == str(question.answer).strip().lower()
        return (100.0 if correct else 0.0, correct)

    if question.type == QuestionType.single:
        correct = str(user_answer).strip() == str(question.answer).strip()
        return (100.0 if correct else 0.0, correct)

    if question.type == QuestionType.multiple:
        correct_set = _split_indices(question.answer)
        user_set = _split_indices(user_answer)
        if not user_set:
            return 0.0, False
        if user_set == correct_set:
            return 100.0, True
        # Partial credit if all selected are correct (no wrong options)
        if user_set.issubset(correct_set):
            return 50.0, False
        return 0.0, False

    return 0.0, False


def _split_indices(value):
    if value is None:
        return set()
    parts = str(value).replace(",", " ").split()
    return set(p.strip() for p in parts if p.strip() != "")


def submit_answer(record_id, user_answer):
    """Save a user's answer for one record. For objective questions, auto-score."""
    record = AnswerRecord.query.get_or_404(record_id)
    record.user_answer = user_answer

    question = record.question
    if question.type == QuestionType.subjective:
        # Subjective questions are scored later by self-evaluation
        record.score = 0.0
        record.is_correct = None
    else:
        score, is_correct = score_objective(question, user_answer)
        record.score = score
        record.is_correct = is_correct

    db.session.commit()
    return record


def finish_session(session, subjective_scores=None):
    """Finish a session. subjective_scores: {record_id: {'score': int, 'note': str}}"""
    if subjective_scores:
        for record_id, data in subjective_scores.items():
            record = db.session.get(AnswerRecord, int(record_id))
            if record and record.question.type == QuestionType.subjective:
                record.self_evaluation = int(data.get("score", 0))
                record.score = float(record.self_evaluation)
                record.note = data.get("note", "") or None
                record.is_correct = record.self_evaluation >= 60

    session.completed_at = datetime.datetime.utcnow()
    db.session.commit()

    _update_user_tag_stats(session)

    return session


def _update_user_tag_stats(session):
    """Update per-user per-tag statistics after finishing a session."""
    records = AnswerRecord.query.filter_by(session_id=session.id).all()

    tag_stats_map = {}
    for record in records:
        question = record.question
        tags = question.tags
        if not tags:
            continue
        for tag in tags:
            key = tag.id
            if key not in tag_stats_map:
                existing = UserTagStats.query.filter_by(
                    user_id=session.user_id, tag_id=tag.id
                ).first()
                if existing is None:
                    existing = UserTagStats(
                        user_id=session.user_id,
                        tag_id=tag.id,
                        total_count=0,
                        correct_count=0,
                        avg_score=0.0,
                    )
                    db.session.add(existing)
                tag_stats_map[key] = existing

            stats = tag_stats_map[key]
            stats.total_count += 1
            if record.is_correct:
                stats.correct_count += 1
            stats.last_practiced_at = datetime.datetime.utcnow()

    for stats in tag_stats_map.values():
        if stats.total_count > 0:
            stats.avg_score = round(
                (stats.correct_count / stats.total_count) * 100, 2
            )

    db.session.commit()


def get_session_summary(session):
    """Return summary statistics for a completed session."""
    records = (
        AnswerRecord.query.filter_by(session_id=session.id)
        .order_by(AnswerRecord.id)
        .all()
    )

    total = len(records)
    objective_records = [r for r in records if r.question.type != QuestionType.subjective]
    subjective_records = [r for r in records if r.question.type == QuestionType.subjective]

    objective_correct = sum(1 for r in objective_records if r.is_correct)
    objective_total = len(objective_records)

    subjective_total_score = sum(r.score or 0 for r in subjective_records)
    subjective_max = len(subjective_records) * 100
    subjective_avg = (
        round(subjective_total_score / subjective_max * 100, 2)
        if subjective_max > 0
        else None
    )

    total_score = sum(r.score or 0 for r in records)
    max_score = total * 100
    overall = round(total_score / max_score * 100, 2) if max_score > 0 else 0

    return {
        "total": total,
        "objective_total": objective_total,
        "objective_correct": objective_correct,
        "subjective_count": len(subjective_records),
        "subjective_avg": subjective_avg,
        "overall_score": overall,
        "records": records,
    }
