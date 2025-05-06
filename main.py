import sqlite3
import os 

db_path = os.path.join("db_builder", "steam_api.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()



steam_appid = "123456"
# example of pulling a genre
try:
    cursor.execute("SELECT genre FROM steam_api WHERE steam_appid = ?", (steam_appid,))
    genre = cursor.fetchone()  # Fetch a single result

    if genre:
        print(f"Genre for steam_appid {steam_appid}: {genre[0]}")
    else:
        print(f"No genre found for steam_appid {steam_appid}")
except sqlite3.Error as e:
    print("Database error:", e)
finally:
    conn.close()