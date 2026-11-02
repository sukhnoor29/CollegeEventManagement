"""Authorization helpers."""

from functools import wraps

from flask import abort
from flask_login import current_user, login_required


def roles_required(*roles):
    def decorator(view_function):
        @wraps(view_function)
        @login_required
        def wrapped(*args, **kwargs):
            if not current_user.is_active or current_user.role not in roles:
                abort(403)
            return view_function(*args, **kwargs)

        return wrapped

    return decorator
