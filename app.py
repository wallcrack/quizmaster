from pathlib import Path

import bleach
import markdown as md
from flask import Flask, render_template
from markupsafe import Markup

from config import Config
from extensions import db, login_manager, migrate
from models import User
from routes import auth, question, quiz, review, stats


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Ensure upload folder exists
    Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "请先登录。"
    login_manager.login_message_category = "info"

    app.register_blueprint(auth.bp)
    app.register_blueprint(question.bp)
    app.register_blueprint(quiz.bp)
    app.register_blueprint(stats.bp)
    app.register_blueprint(review.bp)

    @app.template_filter("nl2br")
    def nl2br(value):
        if value is None:
            return ""
        return value.replace("\n", "<br>")

    @app.template_filter("markdown")
    def markdown_filter(text):
        if text is None:
            return ""
        html = md.markdown(text, extensions=["extra", "nl2br", "sane_lists"])
        allowed_tags = [
            "p", "br", "strong", "em", "ul", "ol", "li", "code", "pre",
            "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "a", "img",
            "table", "thead", "tbody", "tr", "th", "td", "hr", "div", "span"
        ]
        allowed_attributes = {
            "*": ["class"],
            "a": ["href", "title"],
            "img": ["src", "alt", "title"],
        }
        cleaned = bleach.clean(
            html,
            tags=allowed_tags,
            attributes=allowed_attributes,
            strip=True,
        )
        return Markup(cleaned)

    @app.route("/")
    def index():
        return render_template("index.html")

    @app.route("/health")
    def health():
        return {"status": "ok"}

    with app.app_context():
        db.create_all()

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
