from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from extensions import db
from models import User

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/register", methods=("GET", "POST"))
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        error = None

        if not username:
            error = "用户名不能为空。"
        elif not password:
            error = "密码不能为空。"
        elif len(password) < 4:
            error = "密码至少需要 4 位。"
        elif User.query.filter_by(username=username).first():
            error = "用户名已存在。"

        if error is None:
            user = User(
                username=username,
                password_hash=generate_password_hash(password),
            )
            db.session.add(user)
            db.session.commit()
            login_user(user)
            return redirect(url_for("index"))

        flash(error, "danger")

    return render_template("auth/register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        error = None
        user = User.query.filter_by(username=username).first()

        if user is None:
            error = "用户名不存在。"
        elif not check_password_hash(user.password_hash, password):
            error = "密码错误。"

        if error is None:
            login_user(user, remember=True)
            next_page = request.args.get("next")
            if not next_page:
                next_page = url_for("index")
            return redirect(next_page)

        flash(error, "danger")

    return render_template("auth/login.html")


@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("已登出。", "info")
    return redirect(url_for("auth.login"))
