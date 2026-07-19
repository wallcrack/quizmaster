from extensions import db
from models import User


def test_register(client, app):
    response = client.post(
        "/auth/register",
        data={"username": "newuser", "password": "123456"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"newuser" in response.data

    # Verify user in database
    with app.app_context():
        user = User.query.filter_by(username="newuser").first()
        assert user is not None


def test_register_duplicate_username(client):
    client.post(
        "/auth/register",
        data={"username": "dupuser", "password": "123456"},
        follow_redirects=True,
    )
    response = client.post(
        "/auth/register",
        data={"username": "dupuser", "password": "123456"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "用户名已存在" in response.get_data(as_text=True)


def test_login_logout(client):
    # Register first
    client.post(
        "/auth/register",
        data={"username": "loginuser", "password": "123456"},
        follow_redirects=True,
    )

    # Logout
    response = client.get("/auth/logout", follow_redirects=True)
    assert response.status_code == 200

    # Login again
    response = client.post(
        "/auth/login",
        data={"username": "loginuser", "password": "123456"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "loginuser" in response.get_data(as_text=True)


def test_login_wrong_password(client):
    client.post(
        "/auth/register",
        data={"username": "wrongpass", "password": "123456"},
        follow_redirects=True,
    )
    client.get("/auth/logout", follow_redirects=True)

    response = client.post(
        "/auth/login",
        data={"username": "wrongpass", "password": "wrong"},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert "密码错误" in response.get_data(as_text=True)
