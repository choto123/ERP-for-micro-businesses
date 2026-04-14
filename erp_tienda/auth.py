from functools import wraps
from flask import session, redirect, url_for, flash, abort

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login"))
        if session.get("user_rol") != "admin":
            abort(403)
        return f(*args, **kwargs)
    return decorated

def can_edit():
    """Returns True if current user can create/edit/delete."""
    return session.get("user_rol") == "admin"
