"""
migrate.py  —  Run once to add new columns to the existing SQLite database.
Safe to re-run: each ALTER TABLE is wrapped in a try/except so already-existing
columns are silently skipped.

Usage:
    python migrate.py
"""
import sqlite3, os

DB = os.path.join(os.path.dirname(__file__), 'instance', 'temp-database.db')

MIGRATIONS = [
    # Season — status + date fields (wireframe Image 3)
    ("season", "ALTER TABLE season ADD COLUMN status     VARCHAR(20) DEFAULT 'planning'"),
    ("season", "ALTER TABLE season ADD COLUMN reg_open   DATE"),
    ("season", "ALTER TABLE season ADD COLUMN reg_close  DATE"),
    ("season", "ALTER TABLE season ADD COLUMN start_date DATE"),
    ("season", "ALTER TABLE season ADD COLUMN end_date   DATE"),

    # SeasonEvent — status (wireframe Image 1: Active / Inactive per event-in-season)
    ("season_event", "ALTER TABLE season_event ADD COLUMN status VARCHAR(20) DEFAULT 'active'"),

    # Stage — distance (wireframe Image 1: Stage table has Distance column)
    ("stage", "ALTER TABLE stage ADD COLUMN distance VARCHAR(20)"),

    # Institution — contact fields + status (wireframe Image 2)
    ("institution", "ALTER TABLE institution ADD COLUMN contact_person VARCHAR(100)"),
    ("institution", "ALTER TABLE institution ADD COLUMN contact_email  VARCHAR(120)"),
    ("institution", "ALTER TABLE institution ADD COLUMN phone          VARCHAR(30)"),
    ("institution", "ALTER TABLE institution ADD COLUMN status         VARCHAR(20) DEFAULT 'active'"),

    # User — is_active + last_login (auth_views.py references these)
    ("users", "ALTER TABLE users ADD COLUMN is_active  BOOLEAN NOT NULL DEFAULT 1"),
    ("users", "ALTER TABLE users ADD COLUMN last_login DATETIME"),

    # Registration — division column
    ("registration", "ALTER TABLE registration ADD COLUMN division VARCHAR(20)"),
]

conn = sqlite3.connect(DB)
cur  = conn.cursor()

for table, sql in MIGRATIONS:
    try:
        cur.execute(sql)
        col = sql.split("ADD COLUMN")[1].strip().split()[0]
        print(f"  ✓  {table}.{col}")
    except sqlite3.OperationalError as e:
        col = sql.split("ADD COLUMN")[1].strip().split()[0]
        print(f"  –  {table}.{col}  (already exists)")

conn.commit()
conn.close()
print("\nMigration complete.")