import sqlite3
import os

def list_tables(db_path="db_builder/steam_api.db"):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        print("Tables in the database:")
        for table in tables:
            print(f"- {table[0]}")

def list_columns(db_path="db_builder/steam_api.db", table_name="main_game"):
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()

        print(f"Columns in '{table_name}':")
        for col in columns:
            print(f"- {col[1]} ({col[2]})") 


def print_unique_tags(db_path="db_builder/steam_api.db"):
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT genre FROM genres ORDER BY genre ASC")
            tags = cursor.fetchall()

            if tags:
                print("Unique Tags:")
                for tag in tags:
                    print(f"- {tag[0]}")
            else:
                print("No tags found in the database.")

    except sqlite3.Error as e:
        print("Database error:", e)

def get_db_info():
    print_unique_tags()
    list_tables()
    list_columns()

def filter_test():
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


def recommend_test(user_weights):
    try:
        db_path = os.path.join("db_builder", "steam_api.db")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT steam_appid, game_name FROM main_game")
        games_with_genres = cursor.fetchall()
        game_scores = {}
        for game in games_with_genres:
            game_id = game[0]
            game_name = game[1]
            cursor.execute("SELECT genre FROM genres WHERE steam_appid = ?", (game_id,))
            genres = cursor.fetchall()

            if game_id not in game_scores:
                game_scores[game_id] = {"name": game_name, "score": 0}

            for genre in genres:
                genre_name = genre[0] 

                if genre_name in user_weights:
                    game_scores[game_id]['score'] += user_weights[genre_name]

        sorted_games = sorted(game_scores.values(), key=lambda x: x['score'], reverse=True)[:50]

        if sorted_games:
            print(f"Recommended games based on weighted genres:")
            for game in sorted_games:
                print(f"Game Name: {game['name']}, Score: {game['score']:.2f}")
        else:
            print(f"No games found for the given genres.")

    except sqlite3.Error as e:
        print("Database error:", e)
    except ValueError as ve:
        print(ve)
    finally:
        conn.close() 



       




# Path to le database
db_path = os.path.join("db_builder", "steam_api.db")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
#filter_test()
#get_db_info()


user_weights = {
    'Casual': 0.8,
    'Adventure': 0.6,
    'Indie': 0.2
}

recommend_test(user_weights)


