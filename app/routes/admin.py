"""Administrator user and event oversight."""

import csv
from io import StringIO

from flask import Blueprint, flash, make_response, redirect, render_template, request, url_for
from flask_login import current_user

from ..decorators import roles_required
from ..extensions import db
from ..models import Attendance, Event, Feedback, Registration, User

bp = Blueprint("admin", __name__, url_prefix="/admin")


@bp.get("/users")
@roles_required("admin")
def users():
    all_users = User.query.order_by(User.created_at.desc()).all()
    return render_template("admin/users.html", users=all_users)


@bp.post("/users/<int:user_id>/toggle")
@roles_required("admin")
def toggle_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash("You cannot deactivate your own administrator account.", "error")
    else:
        user.is_active = not user.is_active
        db.session.commit()
        flash(f"Account {'activated' if user.is_active else 'deactivated'}.", "success")
    return redirect(url_for("admin.users"))


@bp.post("/users/<int:user_id>/role")
@roles_required("admin")
def change_role(user_id):
    user = User.query.get_or_404(user_id)
    role = request.form.get("role", "")
    if role not in {"student", "organizer", "admin"}:
        flash("Invalid role.", "error")
    elif user.id == current_user.id and role != "admin":
        flash("You cannot remove your own administrator role.", "error")
    else:
        user.role = role
        db.session.commit()
        flash("User role updated.", "success")
    return redirect(url_for("admin.users"))


@bp.get("/events")
@roles_required("admin")
def events():
    all_events = Event.query.order_by(Event.created_at.desc()).all()
    return render_template("admin/events.html", events=all_events)


@bp.post("/events/<int:event_id>/toggle")
@roles_required("admin")
def toggle_event(event_id):
    event = Event.query.get_or_404(event_id)
    event.is_published = not event.is_published
    db.session.commit()
    flash(f"Event {'published' if event.is_published else 'unpublished'}.", "success")
    return redirect(url_for("admin.events"))


@bp.get("/reports.csv")
@roles_required("admin")
def export_reports():
    """Export event participation, attendance and feedback summaries as CSV."""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Event ID", "Event Name", "Organizer", "Event Date", "Category",
        "Registration Limit", "Registrations", "Attendance", "Feedback Responses", "Average Rating",
    ])
    for event in Event.query.order_by(Event.starts_at.asc()).all():
        registrations = Registration.query.filter_by(event_id=event.id, status="registered").all()
        attendance_count = Attendance.query.join(Registration).filter(
            Registration.event_id == event.id, Registration.status == "registered"
        ).count()
        feedback_rows = Feedback.query.filter_by(event_id=event.id).all()
        average = round(sum(row.rating for row in feedback_rows) / len(feedback_rows), 2) if feedback_rows else ""
        writer.writerow([
            event.id, event.event_name, event.organizer.full_name, event.starts_at.isoformat(),
            event.category, event.registration_limit, len(registrations), attendance_count,
            len(feedback_rows), average,
        ])

    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=college-event-report.csv"
    return response
