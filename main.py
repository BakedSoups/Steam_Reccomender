import sqlite3
import os

# Path to le database
db_path = os.path.join("db_builder", "steam_api.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

#filter by
genre_filter = "Adventure"

# query to select 5 games tagged with the genre "Adventure"
try:
    cursor.execute("""
        SELECT mg.game_name, mg.steam_appid
        FROM main_game mg
        JOIN genres g ON mg.steam_appid = g.steam_appid
        WHERE g.genre = ?
        LIMIT 50
    """, (genre_filter,))

    result = cursor.fetchall()

except sqlite3.Error as e:
    print("Database error:", e)
finally:
    conn.close()

#the result
if result:
    print("Games tagged with Adventure:")
    for game in result:
        print(f"Game Name: {game[0]}, Steam AppID: {game[1]}")
else:
    print("No games found for this genre.")
