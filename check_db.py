import sqlite3
import os

db_path = "aethertest.db"
print(f"Checking database at: {db_path}")
print(f"File exists: {os.path.exists(db_path)}")

if os.path.exists(db_path):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        print("Tables in database:")
        for table in tables:
            print(f"  {table[0]}")
        conn.close()
    except Exception as e:
        print(f"Error accessing database: {e}")
else:
    print("Database file does not exist")