import sqlite3
import json
import logging

class SteamGameData:
    def __init__(self, data):
        self.game_id = data.get('game_id')
        self.name = data.get('name')
        self.steam_appid = data.get('steam_appid')
        self.tag_ratios = data.get('tag_ratios', {})
        self.main_genre = data.get('main_genre', '')
        self.unique_tags = data.get('unique_tags', [])
        self.subjective_tags = data.get('subjective_tags', [])
        self.status = data.get('status', '')

def read_steam_games_data():
    with open('tag_builder/steam_games_with_tags.json', 'r') as f:
        data = json.load(f)
    return {key: SteamGameData(value) for key, value in data.items()}

def migrate_steam_review(conn):
    games_data = read_steam_games_data()
    
    count = 0
    processed = 0
    
    for key, game_data in games_data.items():
        if game_data.status != "processed":
            print(f"skipping {game_data.name} - status: {game_data.status}")
            continue
        
        processed += 1
        app_id = game_data.steam_appid
        
        cursor = conn.cursor()
        cursor.execute("SELECT EXISTS(SELECT 1 FROM main_game WHERE steam_appid = ?)", (app_id,))
        exists = cursor.fetchone()[0]
        
        if not exists:
            print(f"steam_appid {app_id} not found in main_game table, skipping {game_data.name}")
            continue
        
        count += 1
        print(f"processing {game_data.name} (appid: {app_id})")
        
        try:
            transact_steam_review_scores(conn, app_id, game_data)
            
            for tag, ratio in game_data.tag_ratios.items():
                try:
                    transact_steam_review_tag(conn, app_id, tag, ratio)
                    print(f"inserted ratio tag: {game_data.name}, {app_id}, {tag}, {ratio}")
                except Exception as e:
                    print(f"error inserting tag {tag} for {game_data.name}: {e}")
            
            for tag in game_data.unique_tags:
                try:
                    transact_steam_review_unique_tag(conn, app_id, tag)
                    print(f"inserted unique tag: {game_data.name}, {app_id}, {tag}")
                except Exception as e:
                    print(f"error inserting unique tag {tag} for {game_data.name}: {e}")
            
            for tag in game_data.subjective_tags:
                try:
                    transact_steam_review_subjective_tag(conn, app_id, tag)
                    print(f"inserted subjective tag: {game_data.name}, {app_id}, {tag}")
                except Exception as e:
                    print(f"error inserting subjective tag {tag} for {game_data.name}: {e}")
                    
        except Exception as e:
            print(f"error inserting scores for {game_data.name}: {e}")
    
    print(f"\nsteam review migration summary:")
    print(f"total games in file: {len(games_data)}")
    print(f"games with processed status: {processed}")
    print(f"games successfully migrated: {count}")

def transact_steam_review_scores(conn, app_id, game_data):
    conn.execute("""
        INSERT INTO SteamReview_scores(steam_appid, score, genre)
        VALUES(?,?,?)
    """, (app_id, 0.0, game_data.main_genre))

def transact_steam_review_tag(conn, app_id, tag, ratio):
    conn.execute("""
        INSERT INTO SteamReview_tags(steam_appid, tag, ratio)
        VALUES(?,?,?)
    """, (app_id, tag, ratio))

def transact_steam_review_unique_tag(conn, app_id, tag):
    conn.execute("""
        INSERT INTO SteamReview_unique_tags(steam_appid, unique_tag)
        VALUES(?,?)
    """, (app_id, tag))

def transact_steam_review_subjective_tag(conn, app_id, tag):
    conn.execute("""
        INSERT INTO SteamReview_subjective_tags(steam_appid, subjective_tag)
        VALUES(?,?)
    """, (app_id, tag))

def create_steam_review_table(conn):
    steam_review_key = """
    CREATE TABLE IF NOT EXISTS SteamReview_scores ( 
        game_id INTEGER PRIMARY KEY AUTOINCREMENT, 
        steam_appid INTEGER NOT NULL, 
        score REAL NOT NULL,
        genre TEXT
    );
    """
    conn.execute(steam_review_key)
    
    tag_table = """
    CREATE TABLE IF NOT EXISTS SteamReview_tags(
        game_id INTEGER PRIMARY KEY AUTOINCREMENT,
        steam_appid INTEGER NOT NULL,
        tag TEXT NOT NULL,
        ratio INTEGER NOT NULL
    );
    """
    conn.execute(tag_table)
    
    unique_tag_table = """
    CREATE TABLE IF NOT EXISTS SteamReview_unique_tags(
        game_id INTEGER PRIMARY KEY AUTOINCREMENT,
        steam_appid INTEGER NOT NULL,
        unique_tag TEXT NOT NULL
    );
    """
    conn.execute(unique_tag_table)
    
    subjective_tags_table = """
    CREATE TABLE IF NOT EXISTS SteamReview_subjective_tags(
        game_id INTEGER PRIMARY KEY AUTOINCREMENT,
        steam_appid INTEGER NOT NULL,
        subjective_tag TEXT NOT NULL
    );
    """
    conn.execute(subjective_tags_table)
    
    print("steam review tables created successfully")