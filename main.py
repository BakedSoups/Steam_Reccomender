import sqlite3
import os

db_path = os.path.join("db_builder", "steam_api.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

genre_filter = "Adventure"

try:
    cursor.execute("""
        SELECT steam_api.*
        FROM steam_api
        JOIN genres g ON steam_api.steam_appid = g.steam_appid
        WHERE g.genre = ?
        LIMIT 50
    """, (genre_filter,))
    
    result = cursor.fetchall()

    columns = [desc[0] for desc in cursor.description]

except sqlite3.Error as e:
    print("Database error:", e)
    result = []

finally:
    conn.close()

if result:
    print(f"Games tagged with '{genre_filter}':\n")
    for row in result:
        for col_name, value in zip(columns, row):
            print(f"{col_name}: {value}")
        print("-" * 40)
else:
    print("No games found for this genre.")
