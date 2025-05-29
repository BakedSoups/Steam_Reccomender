import sqlite3
import json

def extract_first_30_games():
    conn = sqlite3.connect("steam_api.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT steam_appid, game_name, positive_reviews, negative_reviews 
        FROM steam_games 
        LIMIT 30
    """)

    games = {}
    for row in cursor.fetchall():
        appid = str(row["steam_appid"])
        games[appid] = {
            "steam_appid": row["steam_appid"],
            "name": row["game_name"],
            "positive_reviews": row["positive_reviews"],
            "negative_reviews": row["negative_reviews"]
        }

    with open("steam_games_sample.json", "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2)
    print("Saved first 30 games to steam_games_sample.json")

if __name__ == "__main__":
    extract_first_30_games()
