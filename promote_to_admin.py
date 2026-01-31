import sqlite3

DB_PATH = 'database.db'  # Adjust path if needed
USER_EMAIL = 'info@passivora.com'  # Change to the email of the user to promote

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("UPDATE users SET role='admin', active=1 WHERE email=?", (USER_EMAIL,))
conn.commit()

if cursor.rowcount:
    print(f"User {USER_EMAIL} promoted to admin.")
else:
    print(f"No user found with email: {USER_EMAIL}")

conn.close()
