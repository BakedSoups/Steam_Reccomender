import sqlite3
import os 

db_path = os.path.join("db_builder", "steam_api.db")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()


# in production this will be an actual appid


# list_results= ["123213", "12312312", "13213123"]

steam_appid = "220" 
# example of pulling a genre
try:
    cursor.execute("SELECT * FROM steam_api WHERE steam_appid = ?", (steam_appid,))
    result = cursor.fetchall() 
except sqlite3.Error as e:
    print("Database error:", e)
finally:
    conn.close()

print(result)