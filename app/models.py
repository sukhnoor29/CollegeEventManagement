"""Database models for users, events, registrations, attendance and feedback."""

import secrets

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db, login_manager
from .timeutils import now_local


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default="student", index=True)
    interests = db.Column(db.Text, nullable=True, default="")
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    created_at = db.Column(db.DateTime, nullable=False, default=now_local)

    organized_events = db.relationship("Event", back_populates="organizer", lazy="select")
    registrations = db.relationship(
        "Registration", back_populates="student", cascade="all, delete-orphan", lazy="select"
    )
    feedback_entries = db.relationship(
        "Feedback", back_populates="student", cascade="all, delete-orphan", lazy="select"
    )

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    @property
    def is_student(self) -> bool:
        return self.role == "student"

    @property
    def is_organizer(self) -> bool:
        return self.role == "organizer"


class Event(db.Model):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    event_name = db.Column(db.String(160), nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    starts_at = db.Column(db.DateTime, nullable=False, index=True)
    venue = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(80), nullable=False, index=True)
    registration_limit = db.Column(db.Integer, nullable=False)
    registration_deadline = db.Column(db.DateTime, nullable=True)
    is_published = db.Column(db.Boolean, nullable=False, default=True, index=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=now_local)

    organizer = db.relationship("User", back_populates="organized_events")
    registrations = db.relationship(
        "Registration", back_populates="event", cascade="all, delete-orphan", lazy="select"
    )
    feedback_entries = db.relationship(
        "Feedback", back_populates="event", cascade="all, delete-orphan", lazy="select"
    )

    @property
    def registered_count(self) -> int:
        return sum(1 for registration in self.registrations if registration.status == "registered")

    @property
    def seats_remaining(self) -> int:
        return max(self.registration_limit - self.registered_count, 0)

    @property
    def is_registration_open(self) -> bool:
        now = now_local()
        return (
            self.is_published
            and self.starts_at > now
            and (self.registration_deadline is None or self.registration_deadline >= now)
            and self.seats_remaining > 0
        )


class Registration(db.Model):
    __tablename__ = "registrations"
    __table_args__ = (db.UniqueConstraint("student_id", "event_id", name="uq_student_event"),)

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False, index=True)
    registered_at = db.Column(db.DateTime, nullable=False, default=now_local)
    status = db.Column(db.String(20), nullable=False, default="registered", index=True)
    qr_token = db.Column(db.String(96), unique=True, nullable=False, default=lambda: secrets.token_urlsafe(32))

    student = db.relationship("User", back_populates="registrations")
    event = db.relationship("Event", back_populates="registrations")
    attendance = db.relationship(
        "Attendance", back_populates="registration", uselist=False, cascade="all, delete-orphan"
    )


class Attendance(db.Model):
    __tablename__ = "attendance"

    id = db.Column(db.Integer, primary_key=True)
    registration_id = db.Column(
        db.Integer, db.ForeignKey("registrations.id"), nullable=False, unique=True, index=True
    )
    checked_in_at = db.Column(db.DateTime, nullable=False, default=now_local)
    marked_by_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    registration = db.relationship("Registration", back_populates="attendance")
    marked_by = db.relationship("User", foreign_keys=[marked_by_id])


class Feedback(db.Model):
    __tablename__ = "feedback"
    __table_args__ = (db.UniqueConstraint("student_id", "event_id", name="uq_feedback_student_event"),)

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=False, index=True)
    rating = db.Column(db.Integer, nullable=False)
    comments = db.Column(db.Text, nullable=False, default="")
    submitted_at = db.Column(db.DateTime, nullable=False, default=now_local)

    student = db.relationship("User", back_populates="feedback_entries")
    event = db.relationship("Event", back_populates="feedback_entries")


@login_manager.user_loader
def load_user(user_id: str):
    try:
        return db.session.get(User, int(user_id))
    except (TypeError, ValueError):
        return None
