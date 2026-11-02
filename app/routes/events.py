"""Organizer event management, participant lists and QR attendance."""

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user

from ..decorators import roles_required
from ..extensions import db
from ..models import Attendance, Event, Feedback, Registration
from ..utils import parse_datetime_local

bp = Blueprint("events", __name__, url_prefix="/organizer")


def _event_for_manager(event_id):
    event = Event.query.get_or_404(event_id)
    if current_user.role != "admin" and event.organizer_id != current_user.id:
        abort(403)
    return event


def _save_event(event=None):
    event_name = request.form.get("event_name", "").strip()
    description = request.form.get("description", "").strip()
    starts_at = parse_datetime_local(request.form.get("starts_at", ""))
    venue = request.form.get("venue", "").strip()
    category = request.form.get("category", "").strip()
    deadline_raw = request.form.get("registration_deadline", "").strip()
    deadline = parse_datetime_local(deadline_raw) if deadline_raw else None
    try:
        limit = int(request.form.get("registration_limit", "0"))
    except ValueError:
        limit = 0

    if not all([event_name, description, starts_at, venue, category]) or limit < 1:
        flash("Complete all required fields and enter a registration limit greater than zero.", "error")
        return False
    if deadline_raw and deadline is None:
        flash("Enter a valid registration deadline.", "error")
        return False
    if deadline and deadline > starts_at:
        flash("Registration deadline cannot be later than the event start.", "error")
        return False
    if event and limit < event.registered_count:
        flash("The registration limit cannot be lower than the current number of registrations.", "error")
        return False

    if event is None:
        event = Event(organizer_id=current_user.id)
        db.session.add(event)
    event.event_name = event_name
    event.description = description
    event.starts_at = starts_at
    event.venue = venue
    event.category = category
    event.registration_limit = limit
    event.registration_deadline = deadline
    event.is_published = request.form.get("is_published") == "on"
    db.session.commit()
    flash("Event saved successfully.", "success")
    return event


@bp.get("/events")
@roles_required("organizer", "admin")
def event_list():
    query = Event.query if current_user.role == "admin" else Event.query.filter_by(organizer_id=current_user.id)
    events = query.order_by(Event.starts_at.desc()).all()
    return render_template("organizer/events.html", events=events)


@bp.route("/events/new", methods=["GET", "POST"])
@roles_required("organizer", "admin")
def create_event():
    if request.method == "POST":
        event = _save_event()
        if event:
            return redirect(url_for("events.event_list"))
    return render_template("events/form.html", event=None, page_title="Create event")


@bp.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@roles_required("organizer", "admin")
def edit_event(event_id):
    event = _event_for_manager(event_id)
    if request.method == "POST":
        saved = _save_event(event)
        if saved:
            return redirect(url_for("events.event_list"))
    return render_template("events/form.html", event=event, page_title="Edit event")


@bp.post("/events/<int:event_id>/delete")
@roles_required("organizer", "admin")
def delete_event(event_id):
    event = _event_for_manager(event_id)
    if event.registered_count:
        flash("This event has registrations and cannot be deleted. Unpublish it instead.", "error")
    else:
        db.session.delete(event)
        db.session.commit()
        flash("Event deleted.", "success")
    return redirect(url_for("events.event_list"))


@bp.get("/events/<int:event_id>/participants")
@roles_required("organizer", "admin")
def participants(event_id):
    event = _event_for_manager(event_id)
    registrations = Registration.query.filter_by(event_id=event.id, status="registered").order_by(Registration.registered_at.asc()).all()
    return render_template("organizer/participants.html", event=event, registrations=registrations)


@bp.route("/events/<int:event_id>/attendance", methods=["GET", "POST"])
@roles_required("organizer", "admin")
def attendance(event_id):
    event = _event_for_manager(event_id)
    if request.method == "POST":
        token = request.form.get("qr_token", "").strip()
        registration = Registration.query.filter_by(event_id=event.id, qr_token=token, status="registered").first()
        if not token or not registration:
            flash("QR code is not valid for this event.", "error")
        elif registration.attendance:
            flash(f"{registration.student.full_name} has already been checked in.", "info")
        else:
            db.session.add(Attendance(registration_id=registration.id, marked_by_id=current_user.id))
            db.session.commit()
            flash(f"Attendance marked for {registration.student.full_name}.", "success")
        return redirect(url_for("events.attendance", event_id=event.id))

    registrations = Registration.query.filter_by(event_id=event.id, status="registered").order_by(Registration.registered_at.asc()).all()
    attended_count = sum(1 for item in registrations if item.attendance)
    return render_template("organizer/attendance.html", event=event, registrations=registrations, attended_count=attended_count)


@bp.get("/events/<int:event_id>/feedback")
@roles_required("organizer", "admin")
def feedback_summary(event_id):
    event = _event_for_manager(event_id)
    feedback = Feedback.query.filter_by(event_id=event.id).order_by(Feedback.submitted_at.desc()).all()
    average = round(sum(item.rating for item in feedback) / len(feedback), 1) if feedback else None
    return render_template("organizer/feedback.html", event=event, feedback=feedback, average=average)
