"""Application factory for the College Event Management System."""

import os

import click
from dotenv import load_dotenv
from flask import Flask, render_template

from .extensions import csrf, db, login_manager, migrate
from .models import Event, User
from .timeutils import now_local


def create_app(test_config=None):
    load_dotenv()
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "dev-only-change-this-secret"),
        SQLALCHEMY_DATABASE_URI=os.getenv("DATABASE_URL", "sqlite:///event_management.db"),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
        REMEMBER_COOKIE_HTTPONLY=True,
        DEBUG=os.getenv("FLASK_DEBUG", "0") == "1",
    )
    if test_config:
        app.config.update(test_config)

    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access that page."
    login_manager.login_message_category = "info"
    migrate.init_app(app, db)
    csrf.init_app(app)

    from .routes.auth import bp as auth_bp
    from .routes.main import bp as main_bp
    from .routes.events import bp as events_bp
    from .routes.admin import bp as admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(admin_bp)

    @app.context_processor
    def inject_template_values():
        return {"current_year": now_local().year, "now_local": now_local()}

    @app.cli.command("init-db")
    def init_db_command():
        """Create database tables for a new development installation."""
        db.create_all()
        click.echo("Database tables created.")

    @app.cli.command("create-admin")
    def create_admin_command():
        """Interactively create the first administrator account."""
        full_name = click.prompt("Administrator full name").strip()
        email = click.prompt("Administrator email").strip().lower()
        password = click.prompt("Password (minimum 8 characters)", hide_input=True, confirmation_prompt=True)
        if not full_name or "@" not in email or len(password) < 8:
            raise click.ClickException("Enter a name, a valid email address and a password of at least 8 characters.")
        if User.query.filter_by(email=email).first():
            raise click.ClickException("An account with that email already exists.")
        admin = User(full_name=full_name, email=email, role="admin")
        admin.set_password(password)
        db.session.add(admin)
        db.session.commit()
        click.echo(f"Administrator account created for {email}.")

    @app.cli.command("seed-demo")
    def seed_demo_command():
        """Create demo accounts and sample events (safe to run more than once)."""
        from datetime import datetime, timedelta

        db.create_all()
        accounts = [
            ("Demo Student", "student@example.com", "student", "technology, coding, music, sports"),
            ("Demo Organizer", "organizer@example.com", "organizer", ""),
            ("Demo Administrator", "admin@example.com", "admin", ""),
        ]
        created = {}
        for name, email, role, interests in accounts:
            user = User.query.filter_by(email=email).first()
            if user is None:
                user = User(full_name=name, email=email, role=role, interests=interests)
                user.set_password("Demo@123")
                db.session.add(user)
            created[role] = user
        db.session.commit()

        if Event.query.count() == 0:
            samples = [
                ("CodeSprint Hackathon", "A collaborative coding challenge for student teams. Bring an idea and build a working prototype.", 7, "Auditorium", "Technology", 120),
                ("Campus Music Evening", "An evening of student performances, acoustic sets and open-mic acts.", 12, "Open Air Theatre", "Music", 200),
                ("Inter-Department Football", "A friendly inter-department football tournament. Register your interest to participate.", 16, "Sports Ground", "Sports", 80),
            ]
            for name, description, days, venue, category, limit in samples:
                db.session.add(Event(
                    event_name=name, description=description,
                    starts_at=now_local() + timedelta(days=days),
                    venue=venue, category=category, registration_limit=limit,
                    registration_deadline=now_local() + timedelta(days=days - 1),
                    is_published=True, organizer_id=created["organizer"].id,
                ))
            db.session.commit()
        click.echo("Demo data is ready. Password for all demo accounts: Demo@123")

    @app.errorhandler(403)
    def forbidden(_error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("errors/404.html"), 404

    return app
