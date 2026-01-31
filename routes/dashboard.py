from flask import Blueprint, redirect, url_for, flash, render_template, request, make_response
from flask_login import current_user, login_required
from functools import wraps
from models import get_db
from datetime import datetime
from forms import AttendanceForm, GivingForm, ClearDataForm
import csv
from io import StringIO
from werkzeug.security import generate_password_hash
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, validators

# Blueprint must be defined before any route decorators
dashboard = Blueprint("dashboard", __name__)


# ---------------------------
# Role enforcement decorator
# ---------------------------
def role_required(allowed_roles):
    def wrapper(fn):
        @wraps(fn)
        def decorated(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in allowed_roles:
                flash("Access denied!", "danger")
                return redirect(url_for("auth.login"))
            return fn(*args, **kwargs)
        return decorated
    return wrapper


# ---------------------------
# Dashboard Home View
# ---------------------------
@dashboard.route("/dashboard", endpoint="view_dashboard")
@login_required
@role_required(["admin", "pastor", "usher", "finance"])
def view_dashboard():
    db = get_db()
    # Example metrics (customize as needed)
    total_members = db.execute("SELECT COUNT(*) FROM members").fetchone()[0]
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_attendance = db.execute("SELECT COUNT(*) FROM attendance_summary").fetchone()[0]
    total_giving = db.execute("SELECT SUM(tithe + offering + special) FROM giving_summary").fetchone()[0] or 0
    metrics = {
        "total_members": total_members,
        "total_users": total_users,
        "total_attendance": total_attendance,
        "total_giving": total_giving,
    }

    # Compute last attendance metrics for usher/pastor cards
    last_att_row = db.execute(
        "SELECT date, service_type, total FROM attendance_summary ORDER BY date DESC, id DESC LIMIT 1"
    ).fetchone()
    if last_att_row:
        metrics.update({
            "last_attendance_total": last_att_row['total'] or 0,
            "last_attendance_date": last_att_row['date']
        })
    else:
        metrics.update({
            "last_attendance_total": 0,
            "last_attendance_date": None
        })

    # Compute last giving metrics for finance card
    last_giving_row = db.execute(
        "SELECT date, service_type, tithe, offering, special FROM giving_summary ORDER BY date DESC, id DESC LIMIT 1"
    ).fetchone()
    if last_giving_row:
        last_giving_total = (last_giving_row['tithe'] or 0) + (last_giving_row['offering'] or 0) + (last_giving_row['special'] or 0)
        metrics.update({
            "last_giving_total": last_giving_total,
            "last_giving_date": last_giving_row['date']
        })
    else:
        metrics.update({
            "last_giving_total": 0.0,
            "last_giving_date": None
        })

    # Compute expense-related metrics for dashboard badges and summaries
    pending_expenses = db.execute("SELECT COUNT(*) FROM expenses WHERE approved=0").fetchone()[0]
    approved_expenses_total = db.execute("SELECT SUM(amount) FROM expenses WHERE approved=1").fetchone()[0] or 0.0
    metrics.update({
        "pending_expenses": pending_expenses,
        "approved_expenses_total": approved_expenses_total,
    })
    recent_att = db.execute(
        "SELECT date, service_type, male, female, children, total FROM attendance_summary ORDER BY date DESC, id DESC LIMIT 5"
    ).fetchall()
    recent_giv = db.execute(
        "SELECT date, service_type, tithe, offering, special, entered_by FROM giving_summary ORDER BY date DESC, id DESC LIMIT 5"
    ).fetchall()
    recent_exp = db.execute(
        "SELECT date, service_type, category, amount, payment_method, description, paid_by, approved FROM expenses ORDER BY date DESC, id DESC LIMIT 5"
    ).fetchall()
    form = ClearDataForm()
    return render_template("dashboard.html", metrics=metrics, recent_attendance=recent_att, recent_giving=recent_giv, recent_expenses=recent_exp, form=form)


# ---------------------------
# CSV export for monthly report
# ---------------------------
@dashboard.route('/download_report_csv')
@login_required
@role_required(["admin", "pastor", "usher", "finance"])
def download_report_csv():
    month = request.args.get('month')  # format: YYYY-MM
    db = get_db()
    output = StringIO()
    writer = csv.writer(output)

    # Per-service balance: for each (date, service_type), sum giving and approved expenses for the selected month
    writer.writerow(['Date', 'Service Type', 'Total Giving', 'Approved Expenses', 'Balance'])
    giving_data = db.execute(
        "SELECT date, service_type, SUM(tithe), SUM(offering), SUM(special) FROM giving_summary WHERE date LIKE ? GROUP BY date, service_type ORDER BY date DESC",
        (f'{month}%',)
    ).fetchall()
    for g in giving_data:
        date, service_type, tithe, offering, special = g
        norm_service_type = (service_type or '').lower()
        total_giving = (tithe or 0) + (offering or 0) + (special or 0)
        exp_row = db.execute(
            "SELECT SUM(amount) FROM expenses WHERE date=? AND LOWER(service_type)=? AND approved=1",
            (date, norm_service_type)
        ).fetchone()
        total_expenses = exp_row[0] or 0
        balance = total_giving - total_expenses
        writer.writerow([
            date,
            service_type,
            f"{total_giving:,.2f}",
            f"{total_expenses:,.2f}",
            f"{balance:,.2f}"
        ])

    output.seek(0)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=church_report_{month}.csv"
    response.headers["Content-type"] = "text/csv"
    return response


# ---------------------------
# User Management (Admin)
# ---------------------------
class UserForm(FlaskForm):
    name = StringField('Name', [validators.DataRequired()])
    email = StringField('Email', [validators.DataRequired(), validators.Email()])
    role = SelectField('Role', choices=[('admin','Admin'),('pastor','Pastor'),('finance','Finance'),('usher','Usher')])
    password = PasswordField('Password', [validators.Optional()])
    active = SelectField('Status', choices=[('1','Active'),('0','Inactive')], default='1')


@dashboard.route("/users")
@role_required(["admin"])
def users_list():
    db = get_db()
    users = db.execute("SELECT id, name, email, role, active FROM users ORDER BY name").fetchall()
    return render_template("users_list.html", users=users)


@dashboard.route("/users/new", methods=["GET", "POST"])
@role_required(["admin"])
def users_new():
    form = UserForm(request.form)
    if request.method == "POST" and form.validate():
        db = get_db()
        hashed_pw = generate_password_hash(form.password.data) if form.password.data else None
        try:
            db.execute(
                "INSERT INTO users (name, email, password, role, active) VALUES (?, ?, ?, ?, ?)",
                (form.name.data, form.email.data, hashed_pw or '', form.role.data, int(form.active.data))
            )
            db.commit()
            flash("User added.", "success")
            return redirect(url_for("dashboard.users_list"))
        except Exception as e:
            flash("Error adding user: " + str(e), "danger")
    return render_template("users_form.html", form=form, user=None)


@dashboard.route("/users/<int:user_id>/edit", methods=["GET", "POST"])
@role_required(["admin"])
def users_edit(user_id):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("dashboard.users_list"))
    form = UserForm(request.form, data=user)
    if request.method == "POST" and form.validate():
        hashed_pw = generate_password_hash(form.password.data) if form.password.data else user['password']
        try:
            db.execute(
                "UPDATE users SET name=?, email=?, password=?, role=?, active=? WHERE id=?",
                (form.name.data, form.email.data, hashed_pw, form.role.data, int(form.active.data), user_id)
            )
            db.commit()
            flash("User updated.", "success")
            return redirect(url_for("dashboard.users_list"))
        except Exception as e:
            flash("Error updating user: " + str(e), "danger")
    return render_template("users_form.html", form=form, user=user)


@dashboard.route("/users/<int:user_id>/delete", methods=["POST"])
@role_required(["pastor"])  # Keeping original role requirement

def users_delete(user_id):
    db = get_db()
    db.execute("DELETE FROM users WHERE id=?", (user_id,))
    db.commit()
    flash("User deleted.", "success")
    return redirect(url_for("dashboard.users_list"))


# ---------------------------
# Member Management (Pastor)
# ---------------------------
@dashboard.route("/members")
@role_required(["pastor"])
def members_list():
    db = get_db()
    members = db.execute(
        "SELECT id, name, email, phone, joined_date, active FROM members ORDER BY name"
    ).fetchall()
    return render_template("members_list.html", members=members)


@dashboard.route("/members/new", methods=["GET", "POST"])
@role_required(["pastor"])
def members_new():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        phone = request.form.get("phone", "").strip()
        joined_date = request.form.get("joined_date", "").strip()
        if name:
            db = get_db()
            db.execute(
                "INSERT INTO members (name, email, phone, joined_date, active) VALUES (?, ?, ?, ?, 1)",
                (name, email, phone, joined_date)
            )
            db.commit()
            flash("Member added", "success")
            return redirect(url_for("dashboard.members_list"))
        else:
            flash("Name is required", "danger")
    return render_template("members_form.html")


@dashboard.route("/members/<int:member_id>/toggle", methods=["POST"])
@role_required(["pastor"])
def members_toggle(member_id):
    db = get_db()
    # Toggle active flag
    db.execute(
        "UPDATE members SET active = CASE WHEN active=1 THEN 0 ELSE 1 END WHERE id=?",
        (member_id,)
    )
    db.commit()
    flash("Member status updated", "success")
    return redirect(url_for("dashboard.members_list"))


# ---------------------------
# Attendance Entry (Ushers)
# ---------------------------
@dashboard.route("/attendance", methods=["GET", "POST"])
@role_required(["usher"])
def attendance():
    form = AttendanceForm()
    message = ""
    # set default date on GET
    if request.method == 'GET':
        try:
            form.date.data = datetime.today().strftime('%Y-%m-%d')
        except Exception:
            pass

    if form.validate_on_submit():
        date = form.date.data
        service_type = form.service_type.data
        try:
            male = int(form.male.data or 0)
        except ValueError:
            male = 0
        try:
            female = int(form.female.data or 0)
        except ValueError:
            female = 0
        try:
            children = int(form.children.data or 0)
        except ValueError:
            children = 0

        total = male + female + children

        db = get_db()
        db.execute(
            "INSERT INTO attendance_summary (date, service_type, male, female, children, total) VALUES (?, ?, ?, ?, ?, ?)",
            (date, service_type, male, female, children, total)
        )
        db.commit()
        flash(f"Attendance for {date} saved successfully.", "success")
        return redirect(url_for("dashboard.attendance"))

    # fetch recent attendance entries for display
    db = get_db()
    recent_attendance = db.execute(
        "SELECT date, service_type, male, female, children, total FROM attendance_summary ORDER BY date DESC, id DESC LIMIT 5"
    ).fetchall()

    return render_template("attendance.html", form=form, message=message, recent_attendance=recent_attendance)


# ---------------------------
# Tithe & Offering Entry (Finance Officers)
# ---------------------------
@dashboard.route("/giving", methods=["GET", "POST"])
@role_required(["finance"])
def giving():
    form = GivingForm()
    message = ""
    if form.validate_on_submit():
        date = form.date.data
        service_type = form.service_type.data.strip().lower() if form.service_type.data else ''

        def to_float(s):
            try:
                return float(s or 0)
            except (ValueError, TypeError):
                return 0.0

        tithe = to_float(form.tithe.data)
        offering = to_float(form.offering.data)
        special = to_float(form.special.data)
        entered_by = current_user.name

        db = get_db()
        db.execute(
            "INSERT INTO giving_summary (date, service_type, tithe, offering, special, entered_by) VALUES (?, ?, ?, ?, ?, ?)",
            (date, service_type, tithe, offering, special, entered_by)
        )
        db.commit()
        flash(f"Tithe & Offering for {date} saved successfully.", "success")
        return redirect(url_for("dashboard.giving"))

    # fetch recent giving entries for display
    db = get_db()
    recent_giving = db.execute(
        "SELECT date, service_type, tithe, offering, special, entered_by FROM giving_summary ORDER BY date DESC, id DESC LIMIT 5"
    ).fetchall()

    return render_template("giving.html", form=form, message=message, recent_giving=recent_giving)


# ---------------------------
# Expense Approval (Pastor only)
# ---------------------------
@dashboard.route("/expense", methods=["GET", "POST"])
@role_required(["pastor"])
def approve_expenses():
    db = get_db()
    message = ""

    if request.method == "POST":
        # Get expense ID from form
        expense_id = int(request.form["expense_id"])
        db.execute("UPDATE expenses SET approved=1 WHERE id=?", (expense_id,))
        db.commit()
        message = f"Expense ID {expense_id} approved successfully."

    # Fetch all pending expenses
    pending_expenses = db.execute(
        "SELECT id, date, service_type, category, amount, payment_method, description, paid_by "
        "FROM expenses WHERE approved=0"
    ).fetchall()

    # Show per-service balance for the most recent 5 services
    balance_data = []
    giving_data = db.execute(
        "SELECT date, service_type, SUM(tithe), SUM(offering), SUM(special) FROM giving_summary GROUP BY date, service_type ORDER BY date DESC LIMIT 5"
    ).fetchall()
    for g in giving_data:
        date, service_type, tithe, offering, special = g
        total_giving = (tithe or 0) + (offering or 0) + (special or 0)
        exp_row = db.execute(
            "SELECT SUM(amount) FROM expenses WHERE date=? AND service_type=? AND approved=1",
            (date, service_type)
        ).fetchone()
        total_expenses = exp_row[0] or 0
        balance = total_giving - total_expenses
        balance_data.append({
            'date': date,
            'service_type': service_type,
            'total_giving': total_giving,
            'total_expenses': total_expenses,
            'balance': balance
        })

    return render_template("expense.html", expenses=pending_expenses, message=message, balance_data=balance_data)


# ---------------------------
# Reports Page (All roles listed)
# ---------------------------
@dashboard.route("/reports")
@role_required(["admin", "pastor", "usher", "finance"])
def reports():
    db = get_db()

    # Attendance summary: total per service date
    attendance_data = db.execute(
        "SELECT date, service_type, male, female, children, total FROM attendance_summary ORDER BY date DESC"
    ).fetchall()

    # Giving summary: totals per service date
    giving_data = db.execute(
        "SELECT date, service_type, SUM(tithe), SUM(offering), SUM(special) FROM giving_summary GROUP BY date, service_type ORDER BY date DESC"
    ).fetchall()

    # Expenses summary: detailed approved expenses grouped by date and service_type
    expenses_data = db.execute(
        "SELECT date, service_type, category, amount, payment_method, description, paid_by "
        "FROM expenses WHERE approved=1 ORDER BY date DESC, service_type"
    ).fetchall()

    # Per-service balance: for each (date, service_type), sum giving and approved expenses
    balance_data = []
    for g in giving_data:
        date, service_type, tithe, offering, special = g
        norm_service_type = (service_type or '').lower()
        total_giving = (tithe or 0) + (offering or 0) + (special or 0)
        exp_row = db.execute(
            "SELECT SUM(amount) FROM expenses WHERE date=? AND LOWER(service_type)=? AND approved=1",
            (date, norm_service_type)
        ).fetchone()
        total_expenses = exp_row[0] or 0
        balance = total_giving - total_expenses
        balance_data.append({
            'date': date,
            'service_type': service_type,
            'total_giving': total_giving,
            'total_expenses': total_expenses,
            'balance': balance
        })

    return render_template(
        "reports.html",
        attendance_data=attendance_data,
        giving_data=giving_data,
        expenses_data=expenses_data,
        balance_data=balance_data
    )
