from sqlalchemy import func

from extensions import db
from models import AnswerRecord, PracticeSession, Question, Tag, UserTagStats


def get_overview_stats(user_id):
    """Return overall statistics for a user."""
    # Total completed sessions
    session_count = (
        PracticeSession.query.filter_by(user_id=user_id)
        .filter(PracticeSession.completed_at.isnot(None))
        .count()
    )

    # Total answered records
    record_query = (
        db.session.query(AnswerRecord)
        .join(PracticeSession)
        .filter(PracticeSession.user_id == user_id)
    )
    total_records = record_query.count()
    correct_records = record_query.filter(AnswerRecord.is_correct == True).count()

    # Average score
    avg_score_result = (
        db.session.query(func.avg(AnswerRecord.score))
        .join(PracticeSession)
        .filter(PracticeSession.user_id == user_id)
        .scalar()
    )
    avg_score = round(avg_score_result, 2) if avg_score_result else 0.0

    # Recent activity
    recent_sessions = (
        PracticeSession.query.filter_by(user_id=user_id)
        .filter(PracticeSession.completed_at.isnot(None))
        .order_by(PracticeSession.completed_at.desc())
        .limit(5)
        .all()
    )

    return {
        "session_count": session_count,
        "total_records": total_records,
        "correct_records": correct_records,
        "accuracy": round(correct_records / total_records * 100, 2) if total_records else 0.0,
        "avg_score": avg_score,
        "recent_sessions": recent_sessions,
    }


def get_tag_stats(user_id):
    """Return per-tag statistics for a user."""
    stats = (
        db.session.query(UserTagStats, Tag)
        .join(Tag, UserTagStats.tag_id == Tag.id)
        .filter(UserTagStats.user_id == user_id)
        .order_by(UserTagStats.avg_score.asc())
        .all()
    )

    result = []
    for stat, tag in stats:
        result.append({
            "tag": tag,
            "total_count": stat.total_count,
            "correct_count": stat.correct_count,
            "avg_score": stat.avg_score,
            "last_practiced_at": stat.last_practiced_at,
        })
    return result


def get_weak_points(user_id, limit=5):
    """Return weak points based on lowest avg_score and recent activity."""
    tag_stats = get_tag_stats(user_id)

    # Sort by avg_score ascending, then by total_count descending (more practice, still weak)
    weak = sorted(
        tag_stats,
        key=lambda x: (x["avg_score"], -x["total_count"]),
    )[:limit]

    # Add suggested action based on score
    for item in weak:
        score = item["avg_score"]
        if score < 40:
            item["suggestion"] = "需要重点复习"
        elif score < 70:
            item["suggestion"] = "需要加强练习"
        else:
            item["suggestion"] = "保持巩固"

    return weak
