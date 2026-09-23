"""
app.py
Flask entry point for the Smart College Complaint & Resolution System.

Phase 2: app skeleton + DB connectivity.
Phase 3: student + admin authentication (this file).
Phase 4: student-facing UI — landing, register, login, dashboard (this file).
Complaint CRUD (Phase 5), admin dashboard (Phase 6), and staff/resolution
management (Phase 7) extend this file further; route names already
defined here stay stable.
"""

from flask import Flask, render_template, jsonify, session, request, redirect, url_for, flash, send_from_directory
import os
from werkzeug.security import generate_password_hash, check_password_hash
from mysql.connector import Error, IntegrityError

from config import Config, config_debug_summary
from database import test_connection, execute_query
from auth import (
    student_login_required,
    admin_login_required,
    staff_login_required,
    validate_registration,
    validate_login,
)

app = Flask(__name__)
app.config.from_object(Config)
app.secret_key = Config.SECRET_KEY


# ------------------------------------------------------------------
# Landing page
# ------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/favicon.ico")
def favicon():
    return send_from_directory(
        os.path.join(app.root_path, "static", "images"), "favicon.ico"
    )


# ------------------------------------------------------------------
# STUDENT AUTH
# ------------------------------------------------------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    departments = execute_query(
        "SELECT department_id, department_name FROM departments ORDER BY department_name",
        fetch="all",
    )

    if request.method == "POST":
        role = request.form.get("role", "student")
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        phone = request.form.get("phone", "").strip()
        department_id = request.form.get("department_id") or None
        password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")

        if role == "staff":
            errors = validate_registration(name, email, phone, password, confirm_password, require_phone=False)

            if not errors:
                existing = execute_query(
                    "SELECT staff_id FROM staff WHERE email = %s", (email,), fetch="one"
                )
                if existing:
                    errors.append("A staff account with this email already exists.")

            if errors:
                for e in errors:
                    flash(e, "danger")
                return render_template("register.html", departments=departments, form=request.form, role=role)

            password_hash = generate_password_hash(password)
            try:
                execute_query(
                    """INSERT INTO staff (name, email, password_hash, department_id)
                       VALUES (%s, %s, %s, %s)""",
                    (name, email, password_hash, department_id),
                )
            except IntegrityError:
                flash("A staff account with this email already exists.", "danger")
                return render_template("register.html", departments=departments, form=request.form, role=role)
            except Error as e:
                flash(f"Registration failed: {e}", "danger")
                return render_template("register.html", departments=departments, form=request.form, role=role)

            flash("Staff account created successfully. Please log in.", "success")
            return redirect(url_for("staff_login"))

        # default: student registration
        errors = validate_registration(name, email, phone, password, confirm_password)

        if not errors:
            existing = execute_query(
                "SELECT student_id FROM students WHERE email = %s", (email,), fetch="one"
            )
            if existing:
                errors.append("An account with this email already exists.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("register.html", departments=departments, form=request.form, role=role)

        password_hash = generate_password_hash(password)
        try:
            execute_query(
                """INSERT INTO students (name, email, phone, department_id, password_hash)
                   VALUES (%s, %s, %s, %s, %s)""",
                (name, email, phone, department_id, password_hash),
            )
        except IntegrityError:
            flash("An account with this email already exists.", "danger")
            return render_template("register.html", departments=departments, form=request.form, role=role)
        except Error as e:
            flash(f"Registration failed: {e}", "danger")
            return render_template("register.html", departments=departments, form=request.form, role=role)

        flash("Account created successfully. Please log in.", "success")
        return redirect(url_for("login"))

    return render_template("register.html", departments=departments, form={}, role="student")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        remember = request.form.get("remember")

        errors = validate_login(email, password)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("login.html", email=email)

        student = execute_query(
            "SELECT student_id, name, password_hash FROM students WHERE email = %s",
            (email,),
            fetch="one",
        )

        if not student or not check_password_hash(student["password_hash"], password):
            flash("Invalid email or password.", "danger")
            return render_template("login.html", email=email)

        session["student_id"] = student["student_id"]
        session["student_name"] = student["name"]
        session.permanent = bool(remember)

        flash(f"Welcome back, {student['name']}!", "success")
        return redirect(url_for("dashboard"))

    return render_template("login.html", email="")


@app.route("/logout")
def logout():
    session.pop("student_id", None)
    session.pop("student_name", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


# ------------------------------------------------------------------
# STUDENT DASHBOARD
# ------------------------------------------------------------------
@app.route("/dashboard")
@student_login_required
def dashboard():
    student_id = session["student_id"]

    status_counts_rows = execute_query(
        """SELECT status, COUNT(*) AS total
           FROM complaints WHERE student_id = %s GROUP BY status""",
        (student_id,),
        fetch="all",
    )
    status_counts = {row["status"]: row["total"] for row in status_counts_rows}

    stats = {
        "total": sum(status_counts.values()),
        "submitted": status_counts.get("Submitted", 0),
        "in_progress": status_counts.get("In Progress", 0) + status_counts.get("Assigned", 0),
        "resolved": status_counts.get("Resolved", 0),
        "closed": status_counts.get("Closed", 0),
    }

    priority_rows = execute_query(
        """SELECT priority, COUNT(*) AS total
           FROM complaints WHERE student_id = %s GROUP BY priority""",
        (student_id,),
        fetch="all",
    )
    priority_counts = {row["priority"]: row["total"] for row in priority_rows}

    recent_complaints = execute_query(
        """SELECT complaint_id, title, category, priority, status, created_at
           FROM complaints WHERE student_id = %s
           ORDER BY created_at DESC LIMIT 5""",
        (student_id,),
        fetch="all",
    )

    return render_template(
        "dashboard.html",
        stats=stats,
        status_counts=status_counts,
        priority_counts=priority_counts,
        recent_complaints=recent_complaints,
    )


# ------------------------------------------------------------------
# STAFF AUTH & DASHBOARD
# ------------------------------------------------------------------
@app.route("/staff/login", methods=["GET", "POST"])
def staff_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        errors = validate_login(email, password)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("staff_login.html", email=email)

        staff = execute_query(
            "SELECT staff_id, name, password_hash FROM staff WHERE email = %s",
            (email,),
            fetch="one",
        )

        if not staff or not check_password_hash(staff["password_hash"], password):
            flash("Invalid email or password.", "danger")
            return render_template("staff_login.html", email=email)

        session["staff_id"] = staff["staff_id"]
        session["staff_name"] = staff["name"]

        flash(f"Welcome back, {staff['name']}!", "success")
        return redirect(url_for("staff_dashboard"))

    return render_template("staff_login.html", email="")


@app.route("/staff/logout")
def staff_logout():
    session.pop("staff_id", None)
    session.pop("staff_name", None)
    flash("You have been logged out.", "success")
    return redirect(url_for("index"))


def _get_staff_owned_complaint_or_none(complaint_id, staff_id):
    """Fetch a complaint only if it's assigned to the given staff member (row-level access control)."""
    return execute_query(
        """SELECT c.*, s.name AS student_name, s.email AS student_email, d.department_name
           FROM complaints c
           JOIN students s ON c.student_id = s.student_id
           LEFT JOIN departments d ON c.department_id = d.department_id
           WHERE c.complaint_id = %s AND c.staff_id = %s""",
        (complaint_id, staff_id),
        fetch="one",
    )


@app.route("/staff/dashboard")
@staff_login_required
def staff_dashboard():
    staff_id = session["staff_id"]

    status_rows = execute_query(
        """SELECT status, COUNT(*) AS total FROM complaints
           WHERE staff_id = %s GROUP BY status""",
        (staff_id,), fetch="all",
    )
    status_counts = {row["status"]: row["total"] for row in status_rows}
    stats = {
        "total": sum(status_counts.values()),
        "assigned": status_counts.get("Assigned", 0),
        "in_progress": status_counts.get("In Progress", 0),
        "resolved": status_counts.get("Resolved", 0) + status_counts.get("Closed", 0),
    }

    assigned_complaints = execute_query(
        """SELECT c.complaint_id, c.title, c.category, c.priority, c.status, c.created_at,
                  s.name AS student_name, d.department_name
           FROM complaints c
           JOIN students s ON c.student_id = s.student_id
           LEFT JOIN departments d ON c.department_id = d.department_id
           WHERE c.staff_id = %s
           ORDER BY FIELD(c.priority, 'High', 'Medium', 'Low'), c.created_at DESC""",
        (staff_id,), fetch="all",
    )

    return render_template(
        "staff_dashboard.html",
        stats=stats,
        assigned_complaints=assigned_complaints,
        stages=COMPLAINT_STATUS_STAGES,
        priorities=COMPLAINT_PRIORITIES,
    )


@app.route("/staff/complaints/<int:complaint_id>/manage")
@staff_login_required
def staff_manage_complaint(complaint_id):
    """Dedicated page for a staff member to manage one complaint assigned to
    them — real page, not a modal, so it never depends on JS/CDN reliability."""
    complaint = _get_staff_owned_complaint_or_none(complaint_id, session["staff_id"])
    if not complaint:
        flash("That complaint isn't assigned to you.", "danger")
        return redirect(url_for("staff_dashboard"))

    resolution = execute_query(
        "SELECT resolution_text, resolved_at FROM resolutions WHERE complaint_id = %s ORDER BY resolved_at DESC LIMIT 1",
        (complaint_id,), fetch="one",
    )

    return render_template(
        "staff_manage_complaint.html",
        complaint=complaint, resolution=resolution,
        stages=COMPLAINT_STATUS_STAGES, priorities=COMPLAINT_PRIORITIES,
    )


@app.route("/staff/complaints/<int:complaint_id>/update", methods=["POST"])
@staff_login_required
def staff_update_complaint(complaint_id):
    """Staff can change status/priority only on complaints assigned to them."""
    complaint = _get_staff_owned_complaint_or_none(complaint_id, session["staff_id"])
    if not complaint:
        flash("That complaint isn't assigned to you.", "danger")
        return redirect(url_for("staff_dashboard"))

    status = request.form.get("status")
    priority = request.form.get("priority")
    if status not in COMPLAINT_STATUS_STAGES or priority not in COMPLAINT_PRIORITIES:
        flash("Invalid status or priority value.", "danger")
        return redirect(url_for("staff_manage_complaint", complaint_id=complaint_id))

    execute_query(
        "UPDATE complaints SET status=%s, priority=%s WHERE complaint_id=%s AND staff_id=%s",
        (status, priority, complaint_id, session["staff_id"]),
    )
    flash(f"Complaint #{complaint_id} updated.", "success")
    return redirect(url_for("staff_manage_complaint", complaint_id=complaint_id))


@app.route("/staff/complaints/<int:complaint_id>/resolve", methods=["POST"])
@staff_login_required
def staff_resolve_complaint(complaint_id):
    """Staff can only resolve complaints assigned to them."""
    complaint = _get_staff_owned_complaint_or_none(complaint_id, session["staff_id"])
    if not complaint:
        flash("That complaint isn't assigned to you.", "danger")
        return redirect(url_for("staff_dashboard"))

    resolution_text = request.form.get("resolution_text", "").strip()
    if len(resolution_text) < 10:
        flash("Resolution notes must be at least 10 characters.", "danger")
        return redirect(url_for("staff_manage_complaint", complaint_id=complaint_id))

    execute_query(
        "INSERT INTO resolutions (complaint_id, staff_id, resolution_text) VALUES (%s, %s, %s)",
        (complaint_id, session["staff_id"], resolution_text),
    )
    execute_query(
        "UPDATE complaints SET status = 'Resolved' WHERE complaint_id = %s AND staff_id = %s",
        (complaint_id, session["staff_id"]),
    )
    flash(f"Complaint #{complaint_id} marked resolved.", "success")
    return redirect(url_for("staff_manage_complaint", complaint_id=complaint_id))


# ------------------------------------------------------------------
# ADMIN AUTH
# ------------------------------------------------------------------
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        errors = validate_login(email, password)
        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template("admin_login.html", email=email)

        admin = execute_query(
            "SELECT admin_id, name, password_hash FROM admins WHERE email = %s",
            (email,),
            fetch="one",
        )

        if not admin or not check_password_hash(admin["password_hash"], password):
            flash("Invalid admin email or password.", "danger")
            return render_template("admin_login.html", email=email)

        session["admin_id"] = admin["admin_id"]
        session["admin_name"] = admin["name"]

        flash(f"Welcome back, {admin['name']}!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("admin_login.html", email="")


@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_id", None)
    session.pop("admin_name", None)
    flash("Admin logged out.", "success")
    return redirect(url_for("index"))


@app.route("/admin/dashboard")
@admin_login_required
def admin_dashboard():
    status_rows = execute_query(
        "SELECT status, COUNT(*) AS total FROM complaints GROUP BY status", fetch="all"
    )
    status_counts = {row["status"]: row["total"] for row in status_rows}

    stats = {
        "total": sum(status_counts.values()),
        "pending": status_counts.get("Submitted", 0),
        "in_progress": status_counts.get("In Progress", 0) + status_counts.get("Assigned", 0),
        "resolved": status_counts.get("Resolved", 0) + status_counts.get("Closed", 0),
    }
    high_priority_row = execute_query(
        "SELECT COUNT(*) AS total FROM complaints WHERE priority = 'High'", fetch="one"
    )
    stats["high_priority"] = high_priority_row["total"] if high_priority_row else 0

    category_rows = execute_query(
        "SELECT category, COUNT(*) AS total FROM complaints GROUP BY category ORDER BY total DESC",
        fetch="all",
    )

    department_rows = execute_query(
        """SELECT d.department_name, COUNT(c.complaint_id) AS total
           FROM departments d
           LEFT JOIN complaints c ON d.department_id = c.department_id
           GROUP BY d.department_id, d.department_name
           ORDER BY total DESC""",
        fetch="all",
    )

    trend_rows = execute_query(
        """SELECT DATE_FORMAT(created_at, '%Y-%m') AS month, COUNT(*) AS total
           FROM complaints
           WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
           GROUP BY month ORDER BY month""",
        fetch="all",
    )

    recent_complaints = execute_query(
        """SELECT c.complaint_id, c.title, c.category, c.priority, c.status, c.created_at,
                  s.name AS student_name
           FROM complaints c
           JOIN students s ON c.student_id = s.student_id
           ORDER BY c.created_at DESC LIMIT 8""",
        fetch="all",
    )

    return render_template(
        "admin_dashboard.html",
        stats=stats,
        status_counts=status_counts,
        category_rows=category_rows,
        department_rows=department_rows,
        trend_rows=trend_rows,
        recent_complaints=recent_complaints,
    )


# ------------------------------------------------------------------
# ADMIN — COMPLAINT MANAGEMENT (Phase 7)
# ------------------------------------------------------------------
@app.route("/admin/complaints")
@admin_login_required
def manage_complaints():
    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "")
    priority_filter = request.args.get("priority", "")
    category_filter = request.args.get("category", "")
    department_filter = request.args.get("department", "")

    query = """
        SELECT c.complaint_id, c.title, c.description, c.category, c.location,
               c.priority, c.status, c.created_at, c.department_id, c.staff_id,
               s.name AS student_name, s.email AS student_email,
               d.department_name, st.name AS staff_name
        FROM complaints c
        JOIN students s ON c.student_id = s.student_id
        LEFT JOIN departments d ON c.department_id = d.department_id
        LEFT JOIN staff st ON c.staff_id = st.staff_id
        WHERE 1=1
    """
    params = []
    if search:
        query += " AND (c.title LIKE %s OR s.name LIKE %s)"
        params.extend([f"%{search}%", f"%{search}%"])
    if status_filter:
        query += " AND c.status = %s"
        params.append(status_filter)
    if priority_filter:
        query += " AND c.priority = %s"
        params.append(priority_filter)
    if category_filter:
        query += " AND c.category = %s"
        params.append(category_filter)
    if department_filter:
        query += " AND c.department_id = %s"
        params.append(department_filter)
    query += " ORDER BY c.created_at DESC"

    complaints = execute_query(query, tuple(params), fetch="all")
    departments = execute_query(
        "SELECT department_id, department_name FROM departments ORDER BY department_name", fetch="all"
    )
    staff_list = execute_query(
        "SELECT staff_id, name, department_id FROM staff ORDER BY name", fetch="all"
    )

    return render_template(
        "manage_complaints.html",
        complaints=complaints, departments=departments, staff_list=staff_list,
        categories=COMPLAINT_CATEGORIES, priorities=COMPLAINT_PRIORITIES,
        stages=COMPLAINT_STATUS_STAGES,
        search=search, status_filter=status_filter, priority_filter=priority_filter,
        category_filter=category_filter, department_filter=department_filter,
    )


@app.route("/admin/complaints/<int:complaint_id>/manage")
@admin_login_required
def admin_manage_complaint(complaint_id):
    """Dedicated full page for managing a single complaint — assign staff,
    change status/priority, add a resolution, or delete. Replaces the old
    modal-per-row approach, which depended on the Bootstrap JS bundle
    loading correctly; a real page works everywhere, every time."""
    complaint = execute_query(
        """SELECT c.complaint_id, c.title, c.description, c.category, c.location,
                  c.priority, c.status, c.created_at, c.updated_at, c.department_id, c.staff_id,
                  s.name AS student_name, s.email AS student_email,
                  d.department_name, st.name AS staff_name
           FROM complaints c
           JOIN students s ON c.student_id = s.student_id
           LEFT JOIN departments d ON c.department_id = d.department_id
           LEFT JOIN staff st ON c.staff_id = st.staff_id
           WHERE c.complaint_id = %s""",
        (complaint_id,), fetch="one",
    )
    if not complaint:
        flash("Complaint not found.", "danger")
        return redirect(url_for("manage_complaints"))

    resolution = execute_query(
        "SELECT resolution_text, resolved_at FROM resolutions WHERE complaint_id = %s ORDER BY resolved_at DESC LIMIT 1",
        (complaint_id,), fetch="one",
    )
    departments = execute_query(
        "SELECT department_id, department_name FROM departments ORDER BY department_name", fetch="all"
    )
    staff_list = execute_query(
        "SELECT staff_id, name, department_id FROM staff ORDER BY name", fetch="all"
    )

    return render_template(
        "admin_manage_complaint.html",
        complaint=complaint, resolution=resolution, departments=departments, staff_list=staff_list,
        stages=COMPLAINT_STATUS_STAGES, priorities=COMPLAINT_PRIORITIES,
    )


@app.route("/admin/complaints/<int:complaint_id>/update", methods=["POST"])
@admin_login_required
def admin_update_complaint(complaint_id):
    """Assign staff, and/or change department, status, priority — one combined form."""
    staff_id = request.form.get("staff_id") or None
    department_id = request.form.get("department_id") or None
    status = request.form.get("status")
    priority = request.form.get("priority")

    if status not in COMPLAINT_STATUS_STAGES or priority not in COMPLAINT_PRIORITIES:
        flash("Invalid status or priority value.", "danger")
        return redirect(url_for("admin_manage_complaint", complaint_id=complaint_id))

    execute_query(
        """UPDATE complaints SET staff_id=%s, department_id=%s, status=%s, priority=%s
           WHERE complaint_id=%s""",
        (staff_id, department_id, status, priority, complaint_id),
    )
    flash(f"Complaint #{complaint_id} updated.", "success")
    return redirect(url_for("admin_manage_complaint", complaint_id=complaint_id))


@app.route("/admin/complaints/<int:complaint_id>/resolve", methods=["POST"])
@admin_login_required
def admin_resolve_complaint(complaint_id):
    resolution_text = request.form.get("resolution_text", "").strip()
    staff_id = request.form.get("resolving_staff_id") or None

    if len(resolution_text) < 10:
        flash("Resolution notes must be at least 10 characters.", "danger")
        return redirect(url_for("admin_manage_complaint", complaint_id=complaint_id))

    execute_query(
        "INSERT INTO resolutions (complaint_id, staff_id, resolution_text) VALUES (%s, %s, %s)",
        (complaint_id, staff_id, resolution_text),
    )
    execute_query(
        "UPDATE complaints SET status = 'Resolved' WHERE complaint_id = %s", (complaint_id,)
    )
    flash(f"Resolution recorded for complaint #{complaint_id}.", "success")
    return redirect(url_for("admin_manage_complaint", complaint_id=complaint_id))


@app.route("/admin/complaints/<int:complaint_id>/delete", methods=["POST"])
@admin_login_required
def admin_delete_complaint(complaint_id):
    execute_query("DELETE FROM complaints WHERE complaint_id = %s", (complaint_id,))
    flash(f"Complaint #{complaint_id} was deleted.", "success")
    return redirect(url_for("manage_complaints"))


# ------------------------------------------------------------------
# ADMIN — STAFF MANAGEMENT (Phase 7)
# ------------------------------------------------------------------
@app.route("/admin/staff")
@admin_login_required
def manage_staff():
    staff_list = execute_query(
        """SELECT st.staff_id, st.name, st.email, st.department_id, d.department_name,
                  COUNT(c.complaint_id) AS assigned_count
           FROM staff st
           LEFT JOIN departments d ON st.department_id = d.department_id
           LEFT JOIN complaints c ON c.staff_id = st.staff_id
           GROUP BY st.staff_id, st.name, st.email, st.department_id, d.department_name
           ORDER BY st.name""",
        fetch="all",
    )
    departments = execute_query(
        "SELECT department_id, department_name FROM departments ORDER BY department_name", fetch="all"
    )
    return render_template("manage_staff.html", staff_list=staff_list, departments=departments)


@app.route("/admin/staff/add", methods=["POST"])
@admin_login_required
def add_staff():
    name = request.form.get("name", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")
    department_id = request.form.get("department_id") or None

    if not name or not email or len(password) < 8:
        flash("Please provide a name, valid email, and a password of at least 8 characters.", "danger")
        return redirect(url_for("manage_staff"))

    try:
        execute_query(
            "INSERT INTO staff (name, email, password_hash, department_id) VALUES (%s, %s, %s, %s)",
            (name, email, generate_password_hash(password), department_id),
        )
        flash(f"Staff member {name} added.", "success")
    except IntegrityError:
        flash("A staff member with this email already exists.", "danger")
    except Error as e:
        flash(f"Could not add staff: {e}", "danger")

    return redirect(url_for("manage_staff"))


@app.route("/admin/staff/<int:staff_id>/edit", methods=["GET", "POST"])
@admin_login_required
def edit_staff(staff_id):
    staff_member = execute_query(
        "SELECT staff_id, name, email, department_id FROM staff WHERE staff_id = %s",
        (staff_id,), fetch="one",
    )
    if not staff_member:
        flash("Staff member not found.", "danger")
        return redirect(url_for("manage_staff"))

    departments = execute_query(
        "SELECT department_id, department_name FROM departments ORDER BY department_name", fetch="all"
    )

    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        department_id = request.form.get("department_id") or None

        if not name or not email:
            flash("Name and email are required.", "danger")
            return render_template("edit_staff.html", staff_member=staff_member, departments=departments)

        try:
            execute_query(
                "UPDATE staff SET name=%s, email=%s, department_id=%s WHERE staff_id=%s",
                (name, email, department_id, staff_id),
            )
            flash(f"Staff member {name} updated.", "success")
            return redirect(url_for("manage_staff"))
        except IntegrityError:
            flash("Another staff member already uses this email.", "danger")
            return render_template("edit_staff.html", staff_member=staff_member, departments=departments)

    return render_template("edit_staff.html", staff_member=staff_member, departments=departments)


@app.route("/admin/staff/<int:staff_id>/delete", methods=["POST"])
@admin_login_required
def delete_staff(staff_id):
    execute_query("DELETE FROM staff WHERE staff_id = %s", (staff_id,))
    flash("Staff member removed.", "success")
    return redirect(url_for("manage_staff"))


# ------------------------------------------------------------------
# ADMIN — DEPARTMENT MANAGEMENT (Phase 7)
# ------------------------------------------------------------------
@app.route("/admin/departments")
@admin_login_required
def manage_departments():
    departments = execute_query(
        """SELECT d.department_id, d.department_name, d.description,
                  COUNT(c.complaint_id) AS complaint_count
           FROM departments d
           LEFT JOIN complaints c ON c.department_id = d.department_id
           GROUP BY d.department_id, d.department_name, d.description
           ORDER BY d.department_name""",
        fetch="all",
    )
    return render_template("manage_departments.html", departments=departments)


@app.route("/admin/departments/add", methods=["POST"])
@admin_login_required
def add_department():
    name = request.form.get("department_name", "").strip()
    description = request.form.get("description", "").strip()

    if not name:
        flash("Department name is required.", "danger")
        return redirect(url_for("manage_departments"))

    try:
        execute_query(
            "INSERT INTO departments (department_name, description) VALUES (%s, %s)",
            (name, description),
        )
        flash(f"Department '{name}' added.", "success")
    except IntegrityError:
        flash("A department with this name already exists.", "danger")

    return redirect(url_for("manage_departments"))


@app.route("/admin/departments/<int:department_id>/edit", methods=["GET", "POST"])
@admin_login_required
def edit_department(department_id):
    department = execute_query(
        "SELECT department_id, department_name, description FROM departments WHERE department_id = %s",
        (department_id,), fetch="one",
    )
    if not department:
        flash("Department not found.", "danger")
        return redirect(url_for("manage_departments"))

    if request.method == "POST":
        name = request.form.get("department_name", "").strip()
        description = request.form.get("description", "").strip()

        if not name:
            flash("Department name is required.", "danger")
            return render_template("edit_department.html", department=department)

        try:
            execute_query(
                "UPDATE departments SET department_name=%s, description=%s WHERE department_id=%s",
                (name, description, department_id),
            )
            flash(f"Department '{name}' updated.", "success")
            return redirect(url_for("manage_departments"))
        except IntegrityError:
            flash("Another department already uses this name.", "danger")
            return render_template("edit_department.html", department=department)

    return render_template("edit_department.html", department=department)


@app.route("/admin/departments/<int:department_id>/delete", methods=["POST"])
@admin_login_required
def delete_department(department_id):
    execute_query("DELETE FROM departments WHERE department_id = %s", (department_id,))
    flash("Department removed.", "success")
    return redirect(url_for("manage_departments"))


# ------------------------------------------------------------------
# COMPLAINT CRUD (Phase 5)
# ------------------------------------------------------------------
COMPLAINT_CATEGORIES = [
    "Classroom", "Electrical", "Computer/Lab", "Library", "Hostel",
    "Transport", "Sanitation", "Academic", "Security", "IT Support", "Other",
]
COMPLAINT_PRIORITIES = ["Low", "Medium", "High"]
COMPLAINT_STATUS_STAGES = ["Submitted", "Assigned", "In Progress", "Resolved", "Closed"]


def _get_owned_complaint_or_none(complaint_id, student_id):
    """Fetch a complaint only if it belongs to the given student (row-level access control)."""
    return execute_query(
        """SELECT c.*, d.department_name, s.name AS staff_name
           FROM complaints c
           LEFT JOIN departments d ON c.department_id = d.department_id
           LEFT JOIN staff s ON c.staff_id = s.staff_id
           WHERE c.complaint_id = %s AND c.student_id = %s""",
        (complaint_id, student_id),
        fetch="one",
    )


@app.route("/complaints/new", methods=["GET", "POST"])
@student_login_required
def submit_complaint():
    departments = execute_query(
        "SELECT department_id, department_name FROM departments ORDER BY department_name",
        fetch="all",
    )

    if request.method == "POST":
        category = request.form.get("category", "")
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        department_id = request.form.get("department_id") or None
        priority = request.form.get("priority", "Medium")

        errors = []
        if category not in COMPLAINT_CATEGORIES:
            errors.append("Please choose a valid category.")
        if not title or len(title) < 5:
            errors.append("Title must be at least 5 characters.")
        if not description or len(description) < 15:
            errors.append("Description must be at least 15 characters.")
        if priority not in COMPLAINT_PRIORITIES:
            errors.append("Please choose a valid priority.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "submit_complaint.html", departments=departments,
                categories=COMPLAINT_CATEGORIES, priorities=COMPLAINT_PRIORITIES,
                form=request.form,
            )

        result = execute_query(
            """INSERT INTO complaints
               (student_id, department_id, category, title, description, location, priority, status)
               VALUES (%s, %s, %s, %s, %s, %s, %s, 'Submitted')""",
            (session["student_id"], department_id, category, title, description, location, priority),
        )
        new_id = result["lastrowid"]
        flash(f"Complaint submitted successfully. Your complaint ID is #{new_id}.", "success")
        return redirect(url_for("complaint_details", complaint_id=new_id, new=1))

    return render_template(
        "submit_complaint.html", departments=departments,
        categories=COMPLAINT_CATEGORIES, priorities=COMPLAINT_PRIORITIES, form={},
    )


@app.route("/complaints")
@student_login_required
def my_complaints():
    student_id = session["student_id"]

    search = request.args.get("search", "").strip()
    status_filter = request.args.get("status", "")
    priority_filter = request.args.get("priority", "")
    category_filter = request.args.get("category", "")
    sort = request.args.get("sort", "newest")

    query = """
        SELECT c.complaint_id, c.title, c.category, c.priority, c.status, c.created_at,
               d.department_name
        FROM complaints c
        LEFT JOIN departments d ON c.department_id = d.department_id
        WHERE c.student_id = %s
    """
    params = [student_id]

    if search:
        query += " AND (c.title LIKE %s OR c.description LIKE %s)"
        params.extend([f"%{search}%", f"%{search}%"])
    if status_filter:
        query += " AND c.status = %s"
        params.append(status_filter)
    if priority_filter:
        query += " AND c.priority = %s"
        params.append(priority_filter)
    if category_filter:
        query += " AND c.category = %s"
        params.append(category_filter)

    query += " ORDER BY c.created_at " + ("ASC" if sort == "oldest" else "DESC")

    complaints = execute_query(query, tuple(params), fetch="all")

    return render_template(
        "complaints.html",
        complaints=complaints,
        categories=COMPLAINT_CATEGORIES,
        search=search, status_filter=status_filter,
        priority_filter=priority_filter, category_filter=category_filter, sort=sort,
    )


@app.route("/complaints/<int:complaint_id>")
@student_login_required
def complaint_details(complaint_id):
    complaint = _get_owned_complaint_or_none(complaint_id, session["student_id"])
    if not complaint:
        flash("Complaint not found.", "danger")
        return redirect(url_for("my_complaints"))

    resolution = execute_query(
        "SELECT resolution_text, resolved_at FROM resolutions WHERE complaint_id = %s ORDER BY resolved_at DESC LIMIT 1",
        (complaint_id,), fetch="one",
    )

    current_index = COMPLAINT_STATUS_STAGES.index(complaint["status"]) if complaint["status"] in COMPLAINT_STATUS_STAGES else 0

    return render_template(
        "complaint_details.html",
        complaint=complaint, resolution=resolution,
        stages=COMPLAINT_STATUS_STAGES, current_index=current_index,
    )


@app.route("/complaints/<int:complaint_id>/edit", methods=["GET", "POST"])
@student_login_required
def edit_complaint(complaint_id):
    complaint = _get_owned_complaint_or_none(complaint_id, session["student_id"])
    if not complaint:
        flash("Complaint not found.", "danger")
        return redirect(url_for("my_complaints"))

    if complaint["status"] != "Submitted":
        flash("This complaint is already being processed and can no longer be edited.", "warning")
        return redirect(url_for("complaint_details", complaint_id=complaint_id))

    departments = execute_query(
        "SELECT department_id, department_name FROM departments ORDER BY department_name", fetch="all"
    )

    if request.method == "POST":
        category = request.form.get("category", "")
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        location = request.form.get("location", "").strip()
        department_id = request.form.get("department_id") or None
        priority = request.form.get("priority", "Medium")

        errors = []
        if category not in COMPLAINT_CATEGORIES:
            errors.append("Please choose a valid category.")
        if not title or len(title) < 5:
            errors.append("Title must be at least 5 characters.")
        if not description or len(description) < 15:
            errors.append("Description must be at least 15 characters.")
        if priority not in COMPLAINT_PRIORITIES:
            errors.append("Please choose a valid priority.")

        if errors:
            for e in errors:
                flash(e, "danger")
            return render_template(
                "edit_complaint.html", complaint=complaint, departments=departments,
                categories=COMPLAINT_CATEGORIES, priorities=COMPLAINT_PRIORITIES,
            )

        execute_query(
            """UPDATE complaints SET category=%s, title=%s, description=%s,
               location=%s, department_id=%s, priority=%s WHERE complaint_id=%s AND student_id=%s""",
            (category, title, description, location, department_id, priority,
             complaint_id, session["student_id"]),
        )
        flash("Complaint updated successfully.", "success")
        return redirect(url_for("complaint_details", complaint_id=complaint_id))

    return render_template(
        "edit_complaint.html", complaint=complaint, departments=departments,
        categories=COMPLAINT_CATEGORIES, priorities=COMPLAINT_PRIORITIES,
    )


@app.route("/complaints/<int:complaint_id>/delete", methods=["POST"])
@student_login_required
def delete_complaint(complaint_id):
    complaint = _get_owned_complaint_or_none(complaint_id, session["student_id"])
    if not complaint:
        flash("Complaint not found.", "danger")
        return redirect(url_for("my_complaints"))

    execute_query(
        "DELETE FROM complaints WHERE complaint_id = %s AND student_id = %s",
        (complaint_id, session["student_id"]),
    )
    flash(f"Complaint #{complaint_id} was deleted.", "success")
    return redirect(url_for("my_complaints"))


# ------------------------------------------------------------------
# Health-check routes (from Phase 2, kept for ongoing debugging)
# ------------------------------------------------------------------
@app.route("/config-check")
def config_check():
    """
    Visit this in the browser first if MySQL connection errors show up.
    It tells you whether .env was actually found and what values it loaded —
    the #1 cause of 'Access denied ... using password: NO' is .env not
    being found (wrong location, or saved as '.env.txt' by a text editor)
    or MYSQL_PASSWORD being left blank.
    """
    return jsonify(config_debug_summary())


@app.route("/db-test")
def db_test():
    ok, info = test_connection()
    if ok:
        return jsonify({"status": "connected", "database_info": info})
    return jsonify({"status": "error", "message": info}), 500


@app.route("/db-test/departments")
def db_test_departments():
    try:
        rows = execute_query(
            "SELECT department_id, department_name FROM departments ORDER BY department_name",
            fetch="all",
        )
        return jsonify({"status": "ok", "count": len(rows), "departments": rows})
    except Error as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ------------------------------------------------------------------
# Error handlers
# ------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404


@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
