import sqlite3
import os

# Locate DB next to this script (backend folder)
db_path = os.path.join(os.path.dirname(__file__), "ecoquest.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\n--- Tables ---")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
for t in cursor.fetchall():
    print(t[0])

print("\n--- Users / Leaderboard ---")
cursor.execute("SELECT username, role, points FROM users ORDER BY points DESC;")
users = cursor.fetchall()
if not users:
    print("No users yet.")
else:
    for username, role, points in users:
        if role == "admin":
            print(f"{username} (ADMIN): {points} pts")
        else:
            print(f"{username}: {points} pts")

print("\n--- Challenges ---")
cursor.execute("SELECT id, title, description, points FROM challenges;")
challenges = cursor.fetchall()
if not challenges:
    print("No challenges yet.")
else:
    for c in challenges:
        print(f"ID {c[0]}: {c[1]} ({c[3]} pts) - {c[2]}")

print("\n--- Submissions ---")
cursor.execute("""
SELECT s.id, u.username, c.title, s.proof_text, s.status
FROM submissions s
JOIN users u ON s.user_id = u.id
JOIN challenges c ON s.challenge_id = c.id;
""")
subs = cursor.fetchall()
if not subs:
    print("No submissions yet.")
else:
    for s in subs:
        print(f"Submission {s[0]} by {s[1]} for '{s[2]}': {s[3]} [{s[4]}]")

conn.close()
