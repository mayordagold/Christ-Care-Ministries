import sqlite3
from flask import g
from werkzeug.security import generate_password_hash
from flask_login import UserMixin

DB_NAME = "database.db"


def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB_NAME)
        db.row_factory = sqlite3.Row
    return db


def close_db(e=None):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()
        g._database = None


def init_db():
    # Use a standalone connection for initialization (no app context required)
    db = sqlite3.connect(DB_NAME)
    cursor = db.cursor()
    cursor.execute("""CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT UNIQUE,
        password TEXT,
        role TEXT,
        active INTEGER DEFAULT 1
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS attendance_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        service_type TEXT,
        male INTEGER,
        female INTEGER,
        children INTEGER,
        total INTEGER
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS giving_summary (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        service_type TEXT,
        tithe REAL,
        offering REAL,
        special REAL,
        entered_by TEXT
    )""")

    cursor.execute("""CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        service_type TEXT,
        category TEXT,
        amount REAL,
        payment_method TEXT,
        description TEXT,
        paid_by TEXT,
        approved INTEGER DEFAULT 0,
        approved_by TEXT
    )""")

    # Migration: add approved_by column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE expenses ADD COLUMN approved_by TEXT")
    except Exception:
        pass  # Column already exists

    # Members table
    cursor.execute("""CREATE TABLE IF NOT EXISTS members (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        phone TEXT,
        joined_date TEXT,
        active INTEGER DEFAULT 1
    )""")
    db.commit()
    db.close()


# ----------------------
# User helper for flask-login
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


def get_user_by_email(email):
    db = sqlite3.connect(DB_NAME)
    db.row_factory = sqlite3.Row
    user = db.execute("SELECT * FROM users WHERE email=?", (email,)).fetchone()
    db.close()
    if user:
        return User(user['id'], user['name'], user['email'], user['role'], user['active'])
    return None


def load_user(user_id):
    db = sqlite3.connect(DB_NAME)
    db.row_factory = sqlite3.Row
    user = db.execute("SELECT * FROM users WHERE id=?", (int(user_id),)).fetchone()
    db.close()
    if user:
        return User(user['id'], user['name'], user['email'], user['role'], user['active'])
    return None


# ----------------------
# Function to create users
# ----------------------
def create_user(name, email, password, role):
    hashed_pw = generate_password_hash(password)
    db = sqlite3.connect(DB_NAME)
    try:
        db.execute(
            "INSERT INTO users (name, email, password, role) VALUES (?, ?, ?, ?)",
            (name, email, hashed_pw, role)
        )
        db.commit()
        print(f"User {name} ({role}) created.")
    except sqlite3.IntegrityError:
        print(f"User {email} already exists.")
    finally:
        db.close()
