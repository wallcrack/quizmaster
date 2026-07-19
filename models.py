import datetime
import enum

from flask_login import UserMixin

from extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    questions = db.relationship("Question", backref="creator", lazy="dynamic")
    sessions = db.relationship("PracticeSession", backref="user", lazy="dynamic")

    def __repr__(self):
        return f"<User {self.username}>"


class QuestionType(enum.Enum):
    single = "single"
    multiple = "multiple"
    true_false = "true_false"
    subjective = "subjective"


class Difficulty(enum.Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class MasteryLevel(enum.Enum):
    unknown = "unknown"
    weak = "weak"
    familiar = "familiar"
    mastered = "mastered"


question_tag = db.Table(
    "question_tag",
    db.Column("question_id", db.Integer, db.ForeignKey("questions.id"), primary_key=True),
    db.Column("tag_id", db.Integer, db.ForeignKey("tags.id"), primary_key=True),
)


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False, index=True)

    questions = db.relationship(
        "Question", secondary=question_tag, back_populates="tags"
    )

    def __repr__(self):
        return f"<Tag {self.name}>"


class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.Enum(QuestionType), nullable=False)
    content = db.Column(db.Text, nullable=False)
    options = db.Column(db.JSON, nullable=True)  # list of strings for objective questions
    answer = db.Column(db.Text, nullable=False)  # correct answer / reference answer
    explanation = db.Column(db.Text, nullable=True)
    difficulty = db.Column(db.Enum(Difficulty), default=Difficulty.medium)
    source = db.Column(db.String(200), nullable=True)  # book/course name
    chapter = db.Column(db.String(200), nullable=True)
    image = db.Column(db.String(500), nullable=True)  # uploaded image filename
    created_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    tags = db.relationship("Tag", secondary=question_tag, back_populates="questions")
    records = db.relationship("AnswerRecord", backref="question", lazy="dynamic")

    def __repr__(self):
        return f"<Question {self.id} {self.type.value}>"


class PracticeMode(enum.Enum):
    random = "random"
    tag = "tag"
    chapter = "chapter"
    wrong = "wrong"


class PracticeSession(db.Model):
    __tablename__ = "practice_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    mode = db.Column(db.Enum(PracticeMode), nullable=False)
    config = db.Column(db.JSON, nullable=False, default=dict)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)

    records = db.relationship(
        "AnswerRecord", backref="session", lazy="dynamic", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<PracticeSession {self.id} {self.mode.value}>"


class AnswerRecord(db.Model):
    __tablename__ = "answer_records"

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(
        db.Integer, db.ForeignKey("practice_sessions.id"), nullable=False
    )
    question_id = db.Column(db.Integer, db.ForeignKey("questions.id"), nullable=False)
    user_answer = db.Column(db.Text, nullable=True)
    score = db.Column(db.Float, default=0.0)  # 0-100
    is_correct = db.Column(db.Boolean, nullable=True)  # for objective questions
    self_evaluation = db.Column(db.Integer, nullable=True)  # 0-100 for subjective
    note = db.Column(db.Text, nullable=True)
    mastery_level = db.Column(db.Enum(MasteryLevel), default=MasteryLevel.unknown)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<AnswerRecord {self.id} score={self.score}>"


class UserTagStats(db.Model):
    __tablename__ = "user_tag_stats"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    tag_id = db.Column(db.Integer, db.ForeignKey("tags.id"), nullable=False)
    total_count = db.Column(db.Integer, default=0)
    correct_count = db.Column(db.Integer, default=0)
    avg_score = db.Column(db.Float, default=0.0)
    last_practiced_at = db.Column(db.DateTime, nullable=True)

    user = db.relationship("User", backref="tag_stats")
    tag = db.relationship("Tag")

    __table_args__ = (db.UniqueConstraint("user_id", "tag_id", name="uix_user_tag"),)

    def __repr__(self):
        return f"<UserTagStats user={self.user_id} tag={self.tag_id}>"
