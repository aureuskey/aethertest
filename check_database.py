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

        # Check if there are any simulation runs
        cursor.execute("SELECT COUNT(*) FROM simulation_runs")
        sim_count = cursor.fetchone()[0]
        print(f"\nNumber of simulation runs: {sim_count}")

        if sim_count > 0:
            cursor.execute("SELECT id, status, total_interactions, successful_interactions, failed_interactions FROM simulation_runs LIMIT 5")
            sims = cursor.fetchall()
            print("\nRecent simulation runs:")
            for sim in sims:
                print(f"  ID: {sim[0]}, Status: {sim[1]}, Total: {sim[2]}, Success: {sim[3]}, Failed: {sim[4]}")

        # Check agent interactions
        cursor.execute("SELECT COUNT(*) FROM agent_interactions")
        interact_count = cursor.fetchone()[0]
        print(f"\nNumber of agent interactions: {interact_count}")

        conn.close()
    except Exception as e:
        print(f"Error accessing database: {e}")
else:
    print("Database file does not exist")