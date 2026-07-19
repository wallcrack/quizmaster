import pytest

from app import create_app
from config import TestConfig
from extensions import db
from models import User


@pytest.fixture
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
    yield app
    with app.app_context():
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def test_user(app):
    with app.app_context():
        user = User(username="testuser", password_hash="pbkdf2:sha256:600000$test$hash")
        db.session.add(user)
        db.session.commit()
        return user


def login(client, username, password):
    return client.post(
        "/auth/login",
        data={"username": username, "password": password},
        follow_redirects=True,
    )


def logout(client):
    return client.get("/auth/logout", follow_redirects=True)
