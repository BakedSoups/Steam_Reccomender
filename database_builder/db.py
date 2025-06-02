import sqlite3
import os
import time
import logging

def init_db():
    if os.path.exists('./steam_api.db'):
        os.remove('./steam_api.db')
    
    conn = sqlite3.connect('./steam_api.db')
    conn.execute("PRAGMA foreign_keys = ON;")
    
    create_db(conn)
    migrate_top50_to_steam_api(conn)
    
    processed_file = './processed_apps.txt'
    processed_apps = load_processed_apps(processed_file)
    
    cursor = conn.cursor()
    cursor.execute("SELECT steam_appid FROM main_game ORDER BY steam_appid")
    all_app_ids = [row[0] for row in cursor.fetchall()]
    
    app_ids = [app_id for app_id in all_app_ids if app_id not in processed_apps]
    
    logging.info(f"Found {len(app_ids)} apps to process")
    
    batch_size = 25
    save_every = 100
    processed_count = 0
    
    for i in range(0, len(app_ids), batch_size):
        end = min(i + batch_size, len(app_ids))
        batch = app_ids[i:end]
        
        logging.info(f"Processing batch {i+1}-{end} of {len(app_ids)}")
        
        conn.execute("BEGIN TRANSACTION")
        
        for app_id in batch:
            try:
                add_steam_api(app_id, conn)
                save_processed_app(processed_file, app_id)
                processed_count += 1
            except Exception as e:
                logging.error(f"Insert failed for appID {app_id}: {e}")
            
            time.sleep(1.5)
        
        conn.commit()
        
        if processed_count > 0 and processed_count % save_every == 0:
            progress = (processed_count / len(app_ids)) * 100
            logging.info(f"Progress: {processed_count}/{len(app_ids)} apps processed ({progress:.1f}%)")
        
        if i + batch_size < len(app_ids):
            logging.info("Batch complete. Waiting 10 seconds before next batch...")
            time.sleep(10)
    
    logging.info(f"All apps processed successfully! Total: {processed_count}")
    conn.close()

def create_db(conn):
    create_key = """
    CREATE TABLE IF NOT EXISTS main_game (
        game_id INTEGER PRIMARY KEY AUTOINCREMENT,
        game_name TEXT,
        steam_appid INTEGER NOT NULL UNIQUE
    );
    """
    conn.execute(create_key)
    
    create_steamspy = """
    CREATE TABLE IF NOT EXISTS steam_spy (
        game_id INTEGER PRIMARY KEY AUTOINCREMENT,
        steam_appid INTEGER NOT NULL,
        positive_reviews INTEGER,
        negative_reviews INTEGER,
        owners INTEGER,
        FOREIGN KEY(steam_appid) REFERENCES main_game(steam_appid) ON DELETE CASCADE
    );
    """
    conn.execute(create_steamspy)
    
    create_genres = """
    CREATE TABLE IF NOT EXISTS genres (
        steam_appid INTEGER NOT NULL,
        genre TEXT NOT NULL,
        PRIMARY KEY (steam_appid, genre),
        FOREIGN KEY(steam_appid) REFERENCES main_game(steam_appid) ON DELETE CASCADE
    );
    """
    conn.execute(create_genres)
    
    create_steamapi = """
    CREATE TABLE IF NOT EXISTS steam_api (
        detail_id INTEGER PRIMARY KEY AUTOINCREMENT,
        steam_appid INTEGER NOT NULL,
        description TEXT,
        website TEXT,
        header_image TEXT,
        background TEXT,
        screenshot TEXT,
        steam_url TEXT,
        pricing TEXT,
        achievements TEXT,
        FOREIGN KEY(steam_appid) REFERENCES main_game(steam_appid) ON DELETE CASCADE
    );
    """
    conn.execute(create_steamapi)

def migrate_top50_to_steam_api(dst_conn):
    src_conn = sqlite3.connect('./steamspy_all_games.db')
    cursor = src_conn.cursor()
    cursor.execute("SELECT appid, name, positive, negative, owners FROM all_games")
    
    for row in cursor.fetchall():
        app_id, name, positive, negative, owners = row
        
        try:
            dst_conn.execute("INSERT OR IGNORE INTO main_game (game_name, steam_appid) VALUES (?, ?)", (name, app_id))
            dst_conn.execute("""
                INSERT OR REPLACE INTO steam_spy (steam_appid, positive_reviews, negative_reviews, owners)
                VALUES (?, ?, ?, ?)
            """, (app_id, positive, negative, owners))
        except Exception as e:
            logging.error(f"Migration failed for app {app_id}: {e}")
    
    src_conn.close()
    print("Migration from steamspy_all_games.db to steam_api.db completed.")

def add_steam_api(app_id, conn):
    from dag_steamapi import steam_api_pull
    
    genre, description, website, header_image, background, screenshot, steam_url, pricing, achievements = steam_api_pull(app_id)
    
    if not any([genre, description, website]):
        raise Exception(f"No data retrieved for app {app_id}")
    
    conn.execute("""
        INSERT INTO steam_api (
            steam_appid, description, website, header_image, background, 
            screenshot, steam_url, pricing, achievements
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (app_id, description, website, header_image, background, screenshot, steam_url, pricing, achievements))
    
    if genre:
        genre_list = [g.strip() for g in genre.split(", ") if g.strip()]
        for g in genre_list:
            conn.execute("INSERT OR REPLACE INTO genres (steam_appid, genre) VALUES (?, ?)", (app_id, g))

def load_processed_apps(filename):
    processed = set()
    try:
        with open(filename, 'r') as f:
            for line in f:
                try:
                    processed.add(int(line.strip()))
                except ValueError:
                    continue
    except FileNotFoundError:
        pass
    return processed

def save_processed_app(filename, app_id):
    with open(filename, 'a') as f:
        f.write(f"{app_id}\n")