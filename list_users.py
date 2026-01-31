import sqlite3

DB_PATH = 'database.db'  # Adjust path if needed

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

print("Listing all users in the database:")
cursor.execute("SELECT id, name, email, role, active FROM users")
rows = cursor.fetchall()

if not rows:
    print("No users found.")
else:
    for row in rows:
        print(f"ID: {row[0]}, Name: {row[1]}, Email: {row[2]}, Role: {row[3]}, Active: {row[4]}")

conn.close()
