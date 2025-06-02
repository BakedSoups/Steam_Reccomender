import sqlite3
import requests
import json
import time
import logging

class SteamSpy:
    def __init__(self, data):
        self.app_id = data.get('appid')
        self.name = data.get('name', '')
        self.developer = data.get('developer', '')
        self.publisher = data.get('publisher', '')
        self.score_rank = str(data.get('score_rank', ''))
        self.positive = data.get('positive', 0)
        self.negative = data.get('negative', 0)
        self.owners = data.get('owners', '')
        self.average_forever = data.get('average_forever', 0)

def create_steam_spy():
    conn = sqlite3.connect('./steamspy_all_games.db')
    
    conn.execute("""
        CREATE TABLE IF NOT EXISTS all_games (
            appid INTEGER PRIMARY KEY,
            name TEXT,
            developer TEXT,
            publisher TEXT,
            score_rank TEXT,
            positive INTEGER,
            negative INTEGER,
            owners TEXT,
            average_forever INTEGER
        )
    """)
    
    total_saved = 0
    page = 0
    max_games = 20000
    
    print(f"Fetching games from SteamSpy (target: {max_games} games)...")
    
    while total_saved < max_games:
        url = f"https://steamspy.com/api.php?request=all&page={page}"
        print(f"Fetching page {page}...")
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            game_map = response.json()
        except Exception as e:
            logging.error(f"Error fetching page {page}: {e}")
            break
        
        if not game_map:
            print(f"No more games on page {page}")
            break
        
        print(f"Retrieved {len(game_map)} games from page {page}")
        
        conn.execute("BEGIN TRANSACTION")
        
        count = 0
        for key, game_data in game_map.items():
            if total_saved >= max_games:
                break
            
            game = SteamSpy(game_data)
            
            try:
                conn.execute("""
                    INSERT OR REPLACE INTO all_games (
                        appid, name, developer, publisher, score_rank, positive, negative, owners, average_forever
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (game.app_id, game.name, game.developer, game.publisher, 
                      game.score_rank, game.positive, game.negative, game.owners, game.average_forever))
                
                count += 1
                total_saved += 1
            except Exception as e:
                logging.error(f"Error inserting game {game.name}: {e}")
        
        conn.commit()
        
        print(f"Saved {count} games from page {page} (total: {total_saved})")
        
        page += 1
        time.sleep(1)
    
    print(f"\nSummary:")
    print(f"Total games saved: {total_saved}")
    conn.close()