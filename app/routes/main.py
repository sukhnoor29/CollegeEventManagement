"""Public event discovery and student-facing workflows."""

import secrets

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user
from flask_login import login_required
from sqlalchemy import or_

from ..extensions import db
from ..decorators import roles_required
from ..models import Attendance, Event, Feedback, Registration
from ..services.recommendations import recommend_events
from ..utils import qr_data_uri
from ..timeutils import now_local

bp = Blueprint("main", __name__)


@bp.get("/")
def index():
    search = request.args.get("q", "").strip()
    category = request.args.get("category", "").strip()
    query = Event.query.filter(Event.is_published.is_(True), Event.starts_at > now_local())
    if search:
        query = query.filter(
            or_(Event.event_name.ilike(f"%{search}%"), Event.description.ilike(f"%{search}%"), Event.venue.ilike(f"%{search}%"))
        )
    if category:
        query = query.filter(Event.category == category)
    events = query.order_by(Event.starts_at.asc()).all()
    categories = [row[0] for row in db.session.query(Event.category).filter(Event.is_published.is_(True)).distinct().order_by(Event.category).all()]
    return render_template("index.html", events=events, search=search, selected_category=category, categories=categories)


@bp.get("/dashboard")
@login_required
def dashboard():
    if current_user.role == "student":
        registrations = Registration.query.filter_by(student_id=current_user.id, status="registered").all()
        upcoming = [registration for registration in registrations if registration.event.starts_at > now_local()]
        recommendations, recommendation_method = recommend_events(current_user, limit=3)
        return render_template(
            "dashboard.html", registrations=registrations, upcoming_registrations=upcoming,
            recommendations=recommendations, recommendation_method=recommendation_method,
        )

    if current_user.role == "organizer":
        events = Event.query.filter_by(organizer_id=current_user.id).order_by(Event.starts_at.desc()).all()
        return render_template("dashboard.html", events=events)

    if current_user.role == "admin":
        from ..models import User
        metrics = {
            "users": User.query.count(), "events": Event.query.count(),
            "registrations": Registration.query.filter_by(status="registered").count(),
            "attendance": Attendance.query.count(), "feedback": Feedback.query.count(),
        }
        recent_events = Event.query.order_by(Event.created_at.desc()).limit(6).all()
        return render_template("dashboard.html", metrics=metrics, events=recent_events)

    abort(403)


@bp.get("/events/<int:event_id>")
def event_detail(event_id):
    event = Event.query.get_or_404(event_id)
    if not event.is_published and (not current_user.is_authenticated or current_user.role != "admin"):
        abort(404)
    registration = None
    if current_user.is_authenticated and current_user.role == "student":
        registration = Registration.query.filter_by(student_id=current_user.id, event_id=event.id).first()
    feedback_exists = False
    if current_user.is_authenticated and current_user.role == "student":
        feedback_exists = Feedback.query.filter_by(student_id=current_user.id, event_id=event.id).first() is not None
    return render_template("events/detail.html", event=event, registration=registration, feedback_exists=feedback_exists)


@bp.post("/events/<int:event_id>/register")
@roles_required("student")
def register_for_event(event_id):
    event = Event.query.filter_by(id=event_id).with_for_update().first_or_404()
    existing = Registration.query.filter_by(student_id=current_user.id, event_id=event.id).first()
    if existing and existing.status == "registered":
        flash("You are already registered for this event.", "info")
        return redirect(url_for("main.event_detail", event_id=event.id))
    if not event.is_registration_open:
        flash("Registration is closed or the event has reached its limit.", "error")
        return redirect(url_for("main.event_detail", event_id=event.id))

    if existing:
        existing.status = "registered"
        existing.registered_at = now_local()
        existing.qr_token = secrets.token_urlsafe(32)
    else:
        existing = Registration(student_id=current_user.id, event_id=event.id)
        db.session.add(existing)
    db.session.commit()
    flash("Registration successful. Your QR code is available under My Registrations.", "success")
    return redirect(url_for("main.my_registrations"))


@bp.get("/my-registrations")
@roles_required("student")
def my_registrations():
    registrations = Registration.query.filter_by(student_id=current_user.id).order_by(Registration.registered_at.desc()).all()
    return render_template("student/registrations.html", registrations=registrations, qr_data_uri=qr_data_uri)


@bp.get("/recommendations")
@roles_required("student")
def recommendations():
    events, method = recommend_events(current_user, limit=12)
    return render_template("student/recommendations.html", events=events, recommendation_method=method)


@bp.route("/events/<int:event_id>/feedback", methods=["GET", "POST"])
@roles_required("student")
def submit_feedback(event_id):
    event = Event.query.get_or_404(event_id)
    registration = Registration.query.filter_by(
        student_id=current_user.id, event_id=event.id, status="registered"
    ).first()
    if not registration:
        abort(403)
    if event.starts_at > now_local():
        flash("Feedback can be submitted after the event has taken place.", "error")
        return redirect(url_for("main.event_detail", event_id=event.id))

    existing = Feedback.query.filter_by(student_id=current_user.id, event_id=event.id).first()
    if request.method == "POST":
        try:
            rating = int(request.form.get("rating", "0"))
        except ValueError:
            rating = 0
        comments = request.form.get("comments", "").strip()
        if rating not in range(1, 6):
            flash("Choose a rating from 1 to 5.", "error")
        elif existing:
            flash("You have already submitted feedback for this event.", "info")
            return redirect(url_for("main.event_detail", event_id=event.id))
        else:
            db.session.add(Feedback(student_id=current_user.id, event_id=event.id, rating=rating, comments=comments))
            db.session.commit()
            flash("Thank you for your feedback.", "success")
            return redirect(url_for("main.event_detail", event_id=event.id))

    if existing:
        flash("You have already submitted feedback for this event.", "info")
        return redirect(url_for("main.event_detail", event_id=event.id))
    return render_template("events/feedback.html", event=event)
