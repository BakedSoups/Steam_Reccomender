import sqlite3
import os
from typing import List, Dict, Any


# A simple version of app.py (just a test to see how to query the db)

DATABASE_PATH = "./steam_api.db"

class GameSearcher:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        if not os.path.exists(db_path):
            print(f"Error: Database file not found at {db_path}")
            self._find_database()
    
    def _find_database(self):
        db_files = [f for f in os.listdir('.') if f.endswith('.db')]
        if db_files:
            print(f"Found database files: {', '.join(db_files)}")
    
    def search_game_tags(self, steam_appid: int) -> Dict[str, int]:
        """Get all tags and their ratios for a specific game"""
        if not os.path.exists(self.db_path):
            return {}
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Direct query on ign_tags table
            query = "SELECT tag, ratio FROM ign_tags WHERE steam_appid = ?"
            cursor.execute(query, (steam_appid,))
            
            tags = cursor.fetchall()
            if not tags:
                print(f"No tags found for appid {steam_appid}")
                return {}
            
            # Convert to dictionary
            tag_ratios = {tag[0]: tag[1] for tag in tags}
            print(f"Found {len(tag_ratios)} tags for appid {steam_appid}")
            return tag_ratios
            
        finally:
            conn.close()
    
    def search_games(self, search_term: str, limit: int = 5) -> List[Dict[str, Any]]:
        if not os.path.exists(self.db_path):
            return []
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term}%"
        
        try:
            query = """
            SELECT m.game_name, m.steam_appid
            FROM main_game m
            LEFT JOIN steam_spy s ON m.steam_appid = s.steam_appid
            WHERE LOWER(m.game_name) LIKE LOWER(?)
            ORDER BY (IFNULL(s.positive_reviews, 0) + IFNULL(s.negative_reviews, 0)) DESC
            LIMIT ?
            """
            cursor.execute(query, (search_pattern, limit))
            
            games = []
            for row in cursor.fetchall():
                appid = row['steam_appid']
                game_info = {
                    'name': row['game_name'],
                    'steam_appid': appid
                }
                
                # Get tags and ratios
                game_info['tag_ratios'] = self.search_game_tags(appid)
                
                # Get game details
                cursor.execute("""
                SELECT header_image, steam_url, pricing
                FROM steam_api
                WHERE steam_appid = ?
                """, (appid,))
                details = cursor.fetchone()
                if details:
                    game_info.update(dict(details))
                
                # Get genre
                cursor.execute("SELECT genre FROM ign_scores WHERE steam_appid = ?", (appid,))
                genre = cursor.fetchone()
                if genre:
                    game_info['main_genre'] = genre[0]
                
                # Get unique tags
                cursor.execute("SELECT unique_tag FROM ign_unique_tags WHERE steam_appid = ?", (appid,))
                unique_tags = cursor.fetchall()
                if unique_tags:
                    game_info['unique_tags'] = [tag[0] for tag in unique_tags]
                
                games.append(game_info)
            
            return games
            
        finally:
            conn.close()

def main():
    search_term = input("Enter game to search: ")
    searcher = GameSearcher()
    games = searcher.search_games(search_term)
    
    if not games:
        print(f"No games found matching '{search_term}'")
        return
    
    print(f"Found {len(games)} games matching '{search_term}':\n")
    for game in games:
        print(f"Name: {game['name']} (AppID: {game['steam_appid']})")
        
        if 'tag_ratios' in game and game['tag_ratios']:
            print("Tags:")
            for tag, ratio in game['tag_ratios'].items():
                print(f"  - {tag}: {ratio}%")
        else:
            print("No tags found")
        
        if 'unique_tags' in game and game['unique_tags']:
            print("Unique tags:", ", ".join(game['unique_tags']))
        
        if 'main_genre' in game:
            print(f"Genre: {game['main_genre']}")
        
        print("-" * 50)

if __name__ == "__main__":
    main()