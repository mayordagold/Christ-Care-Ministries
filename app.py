import os
from flask import Flask, redirect, url_for
from flask_wtf import CSRFProtect
from flask_login import LoginManager

from models import init_db, create_user, close_db, load_user, get_db

# Import Blueprints
from routes.auth import auth
from routes.dashboard import dashboard
from routes.expenses import expenses_bp
from routes.admin import admin_bp

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or 'fallback_secret_key'

# Security-related config
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    REMEMBER_COOKIE_HTTPONLY=True,
)
if os.environ.get("FLASK_ENV") == "production":
    app.config.update(SESSION_COOKIE_SECURE=True, REMEMBER_COOKIE_SECURE=True)

# CSRF protection
csrf = CSRFProtect(app)

# Login manager
login_manager = LoginManager()
login_manager.login_view = "auth.login"
login_manager.init_app(app)


@login_manager.user_loader
def _load_user(user_id):
    return load_user(user_id)


# Register Blueprints
app.register_blueprint(auth)
app.register_blueprint(dashboard)
app.register_blueprint(expenses_bp)
app.register_blueprint(admin_bp)

# Close DB connections on app context teardown
app.teardown_appcontext(close_db)

# Initialize database
init_db()


# -----------------------
# Idempotent default user seeding
# -----------------------
def seed_default_users():
    created = []

    defaults = [
        ("Admin", "admin@church.com", "password123", "admin"),
        ("John Usher", "usher@church.com", "password123", "usher"),
        ("Mary Finance", "finance@church.com", "password123", "finance"),
        ("Pastor Paul", "pastor@church.com", "password123", "pastor")
    ]

    for name, email, password, role in defaults:
        from models import get_user_by_email, create_user
        if not get_user_by_email(email):
            create_user(name, email, password, role)
            created.append(email)

    if created:
        print(f"Created default users: {', '.join(created)}")
    else:
        print("All default users already exist.")



@app.route("/")
def home():
    return redirect(url_for("auth.login"))


if __name__ == "__main__":
    debug_mode = os.environ.get("DEBUG", "True") == "True"
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", 10000))

    # Ensure DB seeding happens inside app context at startup
    with app.app_context():
        try:
            seed_default_users()
        except Exception as e:
            # Log error but don't prevent app from starting
            print(f"Seed skipped due to error: {e}")

    app.run(host=host, port=port, debug=debug_mode)
