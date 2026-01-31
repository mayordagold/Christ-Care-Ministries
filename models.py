import os
import psycopg2
import psycopg2.extras
from werkzeug.security import generate_password_hash
from flask import g
from flask_login import UserMixin

DB_URL = os.environ.get("DATABASE_URL")


# ----------------------
# Database connection
# ----------------------
def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor)
    return db

def close_db(e=None):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()
        g._database = None


# ----------------------
# Initialize tables
# ----------------------
def init_db():
    with psycopg2.connect(DB_URL) as db:
        with db.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    name TEXT,
                    email TEXT UNIQUE,
                    password TEXT,
                    role TEXT,
                    active INTEGER DEFAULT 1
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS attendance_summary (
                    id SERIAL PRIMARY KEY,
                    date TEXT,
                    service_type TEXT,
                    male INTEGER,
                    female INTEGER,
                    children INTEGER,
                    total INTEGER
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS giving_summary (
                    id SERIAL PRIMARY KEY,
                    date TEXT,
                    service_type TEXT,
                    tithe REAL,
                    offering REAL,
                    special REAL,
                    entered_by TEXT
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS expenses (
                    id SERIAL PRIMARY KEY,
                    date TEXT,
                    service_type TEXT,
                    category TEXT,
                    amount REAL,
                    payment_method TEXT,
                    description TEXT,
                    paid_by TEXT,
                    approved INTEGER DEFAULT 0,
                    approved_by TEXT
                );
            """)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS members (
                    id SERIAL PRIMARY KEY,
                    name TEXT NOT NULL,
                    email TEXT,
                    phone TEXT,
                    joined_date TEXT,
                    active INTEGER DEFAULT 1
                );
            """)
        db.commit()


# ----------------------
# User model for Flask-Login
# ----------------------
class User(UserMixin):
    def __init__(self, id, name, email, role, active=1):
        self.id = id
        self.name = name
        self.email = email
        self.role = role
        self.active = active

    def is_active(self):
        return self.active == 1


# ----------------------
# User helpers
# ----------------------
def get_user_by_email(email):
    with psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor) as db:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE email=%s;", (email,))
            user = cursor.fetchone()
            if user:
                return User(user['id'], user['name'], user['email'], user['role'], user['active'])
    return None


def load_user(user_id):
    with psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.RealDictCursor) as db:
        with db.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id=%s;", (int(user_id),))
            user = cursor.fetchone()
            if user:
                return User(user['id'], user['name'], user['email'], user['role'], user['active'])
    return None


def create_user(name, email, password, role):
    hashed_pw = generate_password_hash(password)
    try:
        with psycopg2.connect(DB_URL) as db:
            with db.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO users (name, email, password, role) VALUES (%s, %s, %s, %s);",
                    (name, email, hashed_pw, role)
                )
                db.commit()
                print(f"User {name} ({role}) created.")
    except psycopg2.errors.UniqueViolation:
        print(f"User {email} already exists.")


# ----------------------
# Idempotent default user seeding
# ----------------------
def seed_default_users():
    defaults = [
        ("Admin", "admin@church.com", "admin123", "admin"),
        ("John Usher", "usher@church.com", "password123", "usher"),
        ("Mary Finance", "finance@church.com", "password123", "finance"),
        ("Pastor Paul", "pastor@church.com", "password123", "pastor")
    ]

    for name, email, password, role in defaults:
        if not get_user_by_email(email):
            create_user(name, email, password, role)

    print("Default users checked/created successfully.")
