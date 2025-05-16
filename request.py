import sqlite3
import os
from typing import List, Dict, Any

# Configure these variables to change the default behavior
DEFAULT_SEARCH_TERM = "Battlefield"  # Change this to search for different games
DATABASE_PATH = "./steam_api.db"     # Path to your database file
RESULT_LIMIT = None                  # Set to a number to limit results, or None for all

class GameSearcher:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        
        if not os.path.exists(db_path):
            print(f"Error: Database file not found at {db_path}")
            self._find_database()
    
    def _find_database(self):
        db_files = [f for f in os.listdir('.') if f.endswith('.db')]
        
        if db_files:
            print("\nFound these database files:")
            for file in db_files:
                print(f"  - {file}")
            print("\nUpdate the DATABASE_PATH variable to use one of these files.")
    
    def search_games(self, search_term: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Search for games and combine data from all relevant tables.
        
        Args:
            search_term: The game name to search for (partial matching supported)
            limit: Optional limit on number of results
            
        Returns:
            A list of dictionaries containing game information, sorted by review count
        """
        if not os.path.exists(self.db_path):
            return []
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term}%"
        
        try:
            try:
                appid = int(search_term)
                is_appid_search = True
            except ValueError:
                is_appid_search = False
            
            games = []
            
            if is_appid_search:
                # Search by AppID
                query = """
                SELECT m.game_name, m.steam_appid, 
                       s.positive_reviews, s.negative_reviews, s.owners,
                       a.detail_id, a.description, a.website, a.header_image, 
                       a.background, a.screenshot, a.steam_url, a.pricing, a.achievements,
                       (IFNULL(s.positive_reviews, 0) + IFNULL(s.negative_reviews, 0)) as total_reviews
                FROM main_game m
                LEFT JOIN steam_spy s ON m.steam_appid = s.steam_appid
                LEFT JOIN steam_api a ON m.steam_appid = a.steam_appid
                WHERE m.steam_appid = ?
                """
                cursor.execute(query, (appid,))
            else:
                query = """
                SELECT m.game_name, m.steam_appid, 
                       s.positive_reviews, s.negative_reviews, s.owners,
                       a.detail_id, a.description, a.website, a.header_image, 
                       a.background, a.screenshot, a.steam_url, a.pricing, a.achievements,
                       (IFNULL(s.positive_reviews, 0) + IFNULL(s.negative_reviews, 0)) as total_reviews
                FROM main_game m
                LEFT JOIN steam_spy s ON m.steam_appid = s.steam_appid
                LEFT JOIN steam_api a ON m.steam_appid = a.steam_appid
                WHERE LOWER(m.game_name) LIKE LOWER(?)
                ORDER BY total_reviews DESC
                """
                
                if limit:
                    query += f" LIMIT {int(limit)}"
                    
                cursor.execute(query, (search_pattern,))
            
            for row in cursor.fetchall():
                game_info = dict(row)
                appid = game_info.get('steam_appid')
                
                if appid:
                    cursor.execute("SELECT genre FROM genres WHERE steam_appid = ?", (appid,))
                    genres = cursor.fetchall()
                    if genres:
                        game_info['genres'] = [genre[0] for genre in genres]
                    cursor.execute("SELECT score, genre FROM ign_scores WHERE steam_appid = ?", (appid,))
                    ign_score = cursor.fetchone()
                    if ign_score:
                        game_info['ign_score'] = ign_score[0]
                        game_info['ign_genre'] = ign_score[1]
                    
                    cursor.execute("SELECT tag, ratio FROM ign_tags WHERE steam_appid = ?", (appid,))
                    tags = cursor.fetchall()
                    if tags:
                        game_info['tag_ratios'] = {tag[0]: tag[1] for tag in tags}
                    
                    cursor.execute("SELECT unique_tag FROM ign_unique_tags WHERE steam_appid = ?", (appid,))
                    unique_tags = cursor.fetchall()
                    if unique_tags:
                        game_info['unique_tags'] = [tag[0] for tag in unique_tags]
                    
                    cursor.execute("SELECT subjective_tag FROM ign_subjective_tags WHERE steam_appid = ?", (appid,))
                    subjective_tags = cursor.fetchall()
                    if subjective_tags:
                        game_info['subjective_tags'] = [tag[0] for tag in subjective_tags]
                
                games.append(game_info)
            
            return games
            
        finally:
            conn.close()
    
    def pretty_print_game(self, game: Dict[str, Any]) -> None:
        name = game.get('game_name', 'Unknown Game')
        appid = game.get('steam_appid', 'N/A')
        
        positive = game.get('positive_reviews', 0) or 0
        negative = game.get('negative_reviews', 0) or 0
        total_reviews = positive + negative
        
        print(f"===== {name} (AppID: {appid}) =====")
        
        # If we have review data, show the ranking
        if total_reviews > 0:
            print(f"[Total Reviews: {total_reviews:,}]")
        
        # Basic info from steam_api
        if 'description' in game and game['description']:
            print(f"Description: {game['description']}")
        
        # Visual assets from steam_api (graphic elements)
        if 'header_image' in game and game['header_image']:
            print(f"Header Image: {game['header_image']}")
        
        if 'background' in game and game['background']:
            print(f"Background: {game['background']}")
            
        if 'screenshot' in game and game['screenshot']:
            print(f"Screenshot: {game['screenshot']}")
        
        # Other steam_api data
        if 'steam_url' in game and game['steam_url']:
            print(f"Steam URL: {game['steam_url']}")
            
        if 'website' in game and game['website']:
            print(f"Website: {game['website']}")
            
        if 'pricing' in game and game['pricing']:
            print(f"Pricing: {game['pricing']}")
            
        if 'achievements' in game and game['achievements']:
            print(f"Achievements: {game['achievements']}")
        
        # Review data from steam_spy table
        if positive > 0 or negative > 0:
            if total_reviews > 0:
                percent_positive = (positive / total_reviews) * 100
                print(f"Steam Reviews: {total_reviews:,} total")
                print(f"  • Positive: {positive:,} ({percent_positive:.1f}%)")
                print(f"  • Negative: {negative:,} ({100-percent_positive:.1f}%)")
            
        if 'owners' in game and game['owners']:
            print(f"Estimated Owners: {game['owners']}")
        
        # Tags and ratios from ign_tags
        if 'tag_ratios' in game and game['tag_ratios']:
            print("\nIGN Tag Ratios:")
            for tag, ratio in game['tag_ratios'].items():
                print(f"  • {tag}: {ratio}%")
        
        # IGN unique tags
        if 'unique_tags' in game and game['unique_tags']:
            print("\nIGN Unique Tags:")
            for tag in game['unique_tags']:
                print(f"  • {tag}")
        
        # IGN subjective tags
        if 'subjective_tags' in game and game['subjective_tags']:
            print("\nIGN Subjective Tags:")
            for tag in game['subjective_tags']:
                print(f"  • {tag}")
        
        # IGN score and genre
        if 'ign_score' in game and game['ign_score']:
            print(f"\nIGN Score: {game['ign_score']}/10")
            
        if 'ign_genre' in game and game['ign_genre']:
            print(f"IGN Main Genre: {game['ign_genre']}")
        
        # Regular genres
        if 'genres' in game and game['genres']:
            print(f"\nGenres: {', '.join(game['genres'])}")
        
        print("\n" + "=" * 50 + "\n")


def main():
    search_term = DEFAULT_SEARCH_TERM
    db_path = DATABASE_PATH
    limit = RESULT_LIMIT
    
    print(f"Searching for: '{search_term}' in database: {db_path}")
    print(f"Results sorted by most reviewed games first")
    
    searcher = GameSearcher(db_path)
    games = searcher.search_games(search_term, limit)
    
    if not games:
        print(f"No games found matching '{search_term}'")
        return
    
    print(f"Found {len(games)} games matching '{search_term}':\n")
    for game in games:
        searcher.pretty_print_game(game)


if __name__ == "__main__":
    main()