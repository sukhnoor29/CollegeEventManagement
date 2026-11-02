from datetime import timedelta

import pytest

from app import create_app
from app.extensions import db
from app.models import Event, Registration, User
from app.timeutils import now_local


@pytest.fixture()
def app():
    app = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        "SECRET_KEY": "test-secret",
    })
    with app.app_context():
        db.create_all()
        student = User(full_name="Test Student", email="student@test.local", role="student", interests="technology")
        student.set_password("TestPass123")
        organizer = User(full_name="Test Organizer", email="organizer@test.local", role="organizer")
        organizer.set_password("TestPass123")
        admin = User(full_name="Test Admin", email="admin@test.local", role="admin")
        admin.set_password("TestPass123")
        db.session.add_all([student, organizer, admin])
        db.session.commit()
        event = Event(
            event_name="Test Technology Event",
            description="A test event for technology students.",
            starts_at=now_local() + timedelta(days=5),
            venue="Main Hall",
            category="Technology",
            registration_limit=1,
            organizer_id=organizer.id,
            is_published=True,
        )
        db.session.add(event)
        db.session.commit()
        app.config["TEST_EVENT_ID"] = event.id
    yield app
    with app.app_context():
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


def login(client, email, password="TestPass123"):
    return client.post("/login", data={"email": email, "password": password}, follow_redirects=True)


def test_homepage_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Upcoming events" in response.data


def test_student_can_register_once_for_event(app, client):
    login(client, "student@test.local")
    event_id = app.config["TEST_EVENT_ID"]

    response = client.post(f"/events/{event_id}/register", follow_redirects=True)
    assert response.status_code == 200
    assert b"Registration successful" in response.data

    with app.app_context():
        assert Registration.query.filter_by(event_id=event_id).count() == 1

    duplicate = client.post(f"/events/{event_id}/register", follow_redirects=True)
    assert duplicate.status_code == 200
    with app.app_context():
        assert Registration.query.filter_by(event_id=event_id).count() == 1


def test_student_cannot_access_organizer_tools(client):
    login(client, "student@test.local")
    response = client.get("/organizer/events")
    assert response.status_code == 403


def test_organizer_can_open_event_creation(client):
    login(client, "organizer@test.local")
    response = client.get("/organizer/events/new")
    assert response.status_code == 200
    assert b"Create event" in response.data


def test_student_registration_page_displays_qr(app, client):
    login(client, "student@test.local")
    event_id = app.config["TEST_EVENT_ID"]
    client.post(f"/events/{event_id}/register", follow_redirects=True)
    response = client.get("/my-registrations")
    assert response.status_code == 200
    assert b"data:image/png;base64" in response.data


def test_admin_dashboard_shows_system_metrics(client):
    login(client, "admin@test.local")
    response = client.get("/dashboard")
    assert response.status_code == 200
    assert b"System overview" in response.data


def test_event_capacity_prevents_another_registration(app, client):
    with app.app_context():
        second_student = User(full_name="Second Student", email="second@test.local", role="student")
        second_student.set_password("TestPass123")
        db.session.add(second_student)
        db.session.commit()
        event_id = app.config["TEST_EVENT_ID"]

    login(client, "student@test.local")
    client.post(f"/events/{event_id}/register", follow_redirects=True)
    client.post("/logout", follow_redirects=True)
    login(client, "second@test.local")
    response = client.post(f"/events/{event_id}/register", follow_redirects=True)
    assert response.status_code == 200
    assert b"registration is closed or the event has reached its limit" in response.data.lower()


def test_admin_can_export_csv_report(client):
    login(client, "admin@test.local")
    response = client.get("/admin/reports.csv")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/csv")
    assert b"Event Name" in response.data
