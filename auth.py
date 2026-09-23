"""
auth.py
Authentication helpers shared across app.py: route-protection decorators
and simple server-side input validation for registration/login forms.
"""

import re
from functools import wraps
from flask import session, redirect, url_for, flash

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\d{10}$")


def student_login_required(view_func):
    """Blocks access unless a student is logged in. Redirects to student login."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "student_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view_func(*args, **kwargs)

    return wrapped


def staff_login_required(view_func):
    """Blocks access unless a staff member is logged in. Redirects to staff login."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "staff_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("staff_login"))
        return view_func(*args, **kwargs)

    return wrapped


def admin_login_required(view_func):
    """Blocks access unless an admin is logged in. Redirects to admin login."""

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        if "admin_id" not in session:
            flash("Please log in as admin to continue.", "warning")
            return redirect(url_for("admin_login"))
        return view_func(*args, **kwargs)

    return wrapped


def validate_registration(name, email, phone, password, confirm_password, require_phone=True):
    """Returns a list of error strings; empty list means the form is valid.
    require_phone=False for staff registration — the staff table has no
    phone column, so it's not collected for that role."""
    errors = []

    if not name or len(name.strip()) < 2:
        errors.append("Please enter your full name.")

    if not email or not EMAIL_RE.match(email):
        errors.append("Please enter a valid college email address.")

    if require_phone and (not phone or not PHONE_RE.match(phone)):
        errors.append("Phone number must be exactly 10 digits.")

    if not password or len(password) < 8:
        errors.append("Password must be at least 8 characters long.")

    if password != confirm_password:
        errors.append("Password and confirm password do not match.")

    return errors


def validate_login(email, password):
    errors = []
    if not email or not EMAIL_RE.match(email):
        errors.append("Please enter a valid email address.")
    if not password:
        errors.append("Please enter your password.")
    return errors
