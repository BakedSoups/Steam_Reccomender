# this module fetches insightful steam reviews
from fetch_steam_reviews import * 

# this module fetches official tags 
from fetch_official_tags import *



import sqlite3
import json

SAMPLE_SIZE = 10

def extract_games_with_reviews():
    conn = sqlite3.connect("steam_api.db")
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    cursor.execute("""
        SELECT steam_appid, game_name
        FROM main_game
        LIMIT ?
    """,(SAMPLE_SIZE,))

    games = {}
    for row in cursor.fetchall():
        appid = row["steam_appid"]
        print(f"Fetching reviews for {row['game_name']} (AppID: {appid})")

        try:
            top_reviews = get_top_descriptive_reviews(appid)
        except Exception as e:
            print(f"Failed to fetch for {appid}: {e}")
            top_reviews = []

        games[str(appid)] = {
            "steam_appid": appid,
            "name": row["game_name"],
            "top_reviews": top_reviews
        }

    with open("steam_games_sample_with_reviews.json", "w", encoding="utf-8") as f:
        json.dump(games, f, indent=2)
    print("Saved games with reviews to steam_games_sample_with_reviews.json")

if __name__ == "__main__":
    extract_games_with_reviews()
