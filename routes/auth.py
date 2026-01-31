from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import get_db, load_user
from werkzeug.security import check_password_hash
from forms import LoginForm
from flask_login import login_user, logout_user, login_required, current_user

auth = Blueprint("auth", __name__)


@auth.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.view_dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data

        db = get_db()
        user_row = db.execute(
            "SELECT * FROM users WHERE email=? AND active=1",
            (email,)
        ).fetchone()

        if user_row and check_password_hash(user_row["password"], password):
            user = load_user(user_row["id"])
            login_user(user)
            flash(f"Welcome {user.name}!", "success")
            return redirect(url_for("dashboard.view_dashboard"))
        else:
            flash("Invalid credentials", "danger")

    return render_template("login.html", form=form)


@auth.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Logged out successfully", "success")
    return redirect(url_for("auth.login"))
