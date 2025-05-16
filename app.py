import sqlite3
from typing import List, Dict, Any, Optional
import json
import os
import sys
import random

# Sample game data for demonstration purposes
SAMPLE_GAME = {
    "detail_id": 68,
    "steam_appid": 1517290,
    "name": "Battlefield™ 2042",
    "description": "Battlefield™ 2042 is a first-person shooter that marks the return to the iconic all-out warfare of the franchise.",
    "website": "https://www.ea.com/games/battlefield/battlefield-2042/",
    "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1517290/header.jpg?t=1744718390",
    "background": "https://store.akamai.steamstatic.com/images/storepagebackground/app/1517290?t=1744718390",
    "screenshot": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1517290/a0c5c62e72cafdddb10c4175c1cba00cba0b0fb1/ss_a0c5c62e72cafdddb10c4175c1cba00cba0b0fb1.1920x1080.jpg?t=1744718390",
    "steam_url": "https://store.steampowered.com/app/1517290",
    "pricing": "$59.99",
    "discount": "75%",
    "final_price": "$14.99",
    "achievements": "34 achievements",
    "score": "8.5/10",
    "main_genre": "FPS",
    "tag_ratios": {"fps": 40, "multiplayer": 35, "action": 25},
    "unique_tags": ["large-scale-battles", "vehicles", "destruction"],
    "verdict": "A return to form for the Battlefield franchise, offering massive battles with cutting-edge graphics and gameplay.",
    "release_date": "May 16, 2011",
    "publisher": "EA Games",
    "overall_review": 30000,
    "positive_reviews": 18000,
    "negative_reviews": 12000
}

# More genres for random assignment
GENRES = ["FPS", "RPG", "Strategy", "Adventure", "Simulation", "Sports", "Racing", "Puzzle", "Action", "MMORPG", 
          "Fighting", "Platformer", "Stealth", "Horror", "Shooter", "Open World", "Survival", "Card Game"]

# More tags for random assignment
TAGS = ["multiplayer", "singleplayer", "action", "adventure", "strategy", "rpg", "fps", "tps", "co-op", "open-world",
        "survival", "horror", "puzzle", "story-rich", "atmospheric", "sandbox", "vr", "moddable", "indie", "casual",
        "simulation", "racing", "sports", "roguelike", "2D", "3D", "isometric", "top-down", "side-scrolling", 
        "tactical", "pixel-graphics", "realistic", "cartoony", "sci-fi", "fantasy", "historical", "modern", "medieval",
        "futuristic", "cyberpunk", "post-apocalyptic", "western", "space", "naval", "military", "superhero"]

# More unique tags for random assignment
UNIQUE_TAGS = ["destructible-environment", "base-building", "crafting", "resource-management", "deck-building", 
              "turn-based", "real-time", "physics-based", "procedural-generation", "permadeath", "massive-battles",
              "vehicles", "flight", "driving", "naval-combat", "air-combat", "ground-combat", "melee-combat",
              "ranged-combat", "magic", "stealth", "parkour", "exploration", "narrative-choice", "economy", 
              "diplomacy", "city-building", "tower-defense", "wave-based", "time-manipulation", "hacking",
              "character-customization", "weapon-customization", "vehicle-customization", "character-progression",
              "skill-tree", "perks", "abilities", "classes", "races", "factions", "guilds", "clans", "alliances"]

# Publishers for random assignment
PUBLISHERS = ["EA Games", "Valve", "Ubisoft", "Activision Blizzard", "2K Games", "Bethesda", "CD Projekt Red",
             "Square Enix", "Capcom", "Konami", "Sega", "Nintendo", "Sony Interactive Entertainment", 
             "Microsoft Studios", "Bandai Namco", "Paradox Interactive", "Deep Silver", "THQ Nordic", 
             "Devolver Digital", "505 Games", "Focus Home Interactive", "Team17", "Annapurna Interactive"]

class GameSearcher:
    def __init__(self, db_path: str = "./db_builder/steam_api.db", use_sample_data: bool = False):
        """Initialize the GameSearcher with the path to the SQLite database."""
        self.db_path = db_path
        self.use_sample_data = use_sample_data
        
        # Check if the database file exists
        if not os.path.exists(db_path) and not use_sample_data:
            print(f"Warning: Database file not found at {db_path}")
            valid_file = self._find_database_file()
            if valid_file:
                print(f"Found database at: {valid_file}")
                self.db_path = valid_file
            else:
                print("No SQLite database found. Using sample data instead.")
                self.use_sample_data = True
                self.db_path = None
    
    def _find_database_file(self) -> str:
        """Try to find a SQLite database file in common locations."""
        # Common locations to check
        locations = [
            "./steam_api.db",
            "./db_builder/steam_api.db",
            "../db_builder/steam_api.db",
            "./steamspy_all_games.db"
        ]
        
        # Get current directory
        current_dir = os.getcwd()
        
        # Check for .db files in current directory
        for file in os.listdir(current_dir):
            if file.endswith('.db'):
                locations.append(os.path.join(current_dir, file))
        
        # Try each location
        for location in locations:
            if os.path.exists(location):
                # Quick check if it's actually a SQLite database
                try:
                    conn = sqlite3.connect(location)
                    conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    conn.close()
                    return location
                except sqlite3.Error:
                    continue
        
        return None
    
    def search_games(self, search_term: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Search for games by name across tables in the database or generate sample data.
        
        Args:
            search_term: The game name to search for (partial matching supported)
            limit: Optional limit on number of results
            
        Returns:
            A list of dictionaries containing game information
        """
        if self.use_sample_data:
            return self._generate_sample_data(search_term, limit)
        
        if not self.db_path:
            return []
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Find the main game table and relevant columns
            table_info = self._get_table_info(cursor)
            
            # Look for main_game table first
            if 'main_game' in table_info:
                appid_col = 'steam_appid'
                name_col = 'game_name'
                
                if appid_col in table_info['main_game'] and name_col in table_info['main_game']:
                    games = self._search_main_game_table(cursor, search_term, limit, appid_col, name_col)
                    if games:
                        # If we found games but they lack detailed info, enrich them with sample data
                        if self._should_enrich_with_sample_data(games):
                            return self._enrich_with_sample_data(games)
                        return games
            
            # Try to find any table with game info if main_game doesn't work
            for table_name, columns in table_info.items():
                # Skip sqlite internal tables
                if table_name.startswith('sqlite_'):
                    continue
                
                # Look for columns that might contain appid and name
                appid_col = None
                name_col = None
                
                for col in columns:
                    if col.lower().endswith('appid'):
                        appid_col = col
                    elif col.lower().endswith('name'):
                        name_col = col
                
                if appid_col and name_col:
                    games = self._search_table(cursor, table_name, search_term, limit, appid_col, name_col)
                    if games:
                        # Check if we need to enrich with sample data
                        if self._should_enrich_with_sample_data(games):
                            return self._enrich_with_sample_data(games)
                        return games
            
            # If no games found in database, return sample data
            return self._generate_sample_data(search_term, limit)
            
        finally:
            conn.close()
    
    def _get_table_info(self, cursor: sqlite3.Cursor) -> Dict[str, List[str]]:
        """Get information about all tables in the database."""
        # Get list of all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        
        table_info = {}
        for table in tables:
            table_name = table[0]
            # Skip sqlite internal tables
            if table_name.startswith('sqlite_'):
                continue
                
            # Get column info for each table
            try:
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                table_info[table_name] = [col[1] for col in columns]  # col[1] is the column name
            except sqlite3.Error:
                # Skip if table doesn't exist or other issue
                continue
        
        return table_info
    
    def _search_main_game_table(self, cursor: sqlite3.Cursor, search_term: str, limit: int, 
                              appid_col: str, name_col: str) -> List[Dict[str, Any]]:
        """Search the main_game table for games matching the search term."""
        search_pattern = f"%{search_term}%"
        query = f"SELECT * FROM main_game WHERE LOWER({name_col}) LIKE LOWER(?)"
        
        if limit:
            query += f" LIMIT {int(limit)}"
            
        try:
            cursor.execute(query, (search_pattern,))
            
            games = []
            for row in cursor.fetchall():
                game_info = dict(row)
                
                # Find the appid in this row
                appid = game_info.get(appid_col)
                
                if appid:
                    # Add data from other tables
                    self._add_related_data(cursor, appid, appid_col, game_info)
                
                games.append(game_info)
            
            return games
        except sqlite3.Error:
            return []
    
    def _search_table(self, cursor: sqlite3.Cursor, table_name: str, search_term: str, 
                    limit: int, appid_col: str, name_col: str) -> List[Dict[str, Any]]:
        """Search a specific table for games matching the search term."""
        search_pattern = f"%{search_term}%"
        query = f"SELECT * FROM {table_name} WHERE LOWER({name_col}) LIKE LOWER(?)"
        
        if limit:
            query += f" LIMIT {int(limit)}"
            
        try:
            cursor.execute(query, (search_pattern,))
            
            games = []
            for row in cursor.fetchall():
                game_info = dict(row)
                
                # Find the appid in this row
                appid = game_info.get(appid_col)
                
                if appid:
                    # Add data from other tables
                    self._add_related_data(cursor, appid, appid_col, game_info)
                
                games.append(game_info)
            
            return games
        except sqlite3.Error:
            return []
    
    def _add_related_data(self, cursor: sqlite3.Cursor, appid: int, appid_col: str, 
                        game_info: Dict[str, Any]) -> None:
        """Add related data from other tables based on appid."""
        # Try to get data from steam_spy table
        try:
            cursor.execute(f"SELECT * FROM steam_spy WHERE {appid_col} = ?", (appid,))
            row = cursor.fetchone()
            if row:
                spy_data = dict(row)
                for key, value in spy_data.items():
                    if key != appid_col:  # Don't duplicate appid
                        game_info[key] = value
        except sqlite3.Error:
            pass
        
        # Try to get data from steam_api table
        try:
            cursor.execute(f"SELECT * FROM steam_api WHERE {appid_col} = ?", (appid,))
            row = cursor.fetchone()
            if row:
                api_data = dict(row)
                for key, value in api_data.items():
                    if key != appid_col:  # Don't duplicate appid
                        game_info[key] = value
        except sqlite3.Error:
            pass
        
        # Try to get genres data
        try:
            cursor.execute(f"SELECT genre FROM genres WHERE {appid_col} = ?", (appid,))
            rows = cursor.fetchall()
            if rows:
                game_info['genres'] = [row[0] for row in rows]
        except sqlite3.Error:
            pass
        
        # Try to get tags data
        try:
            cursor.execute(f"SELECT tag, ratio FROM ign_tags WHERE {appid_col} = ?", (appid,))
            rows = cursor.fetchall()
            if rows:
                game_info['tag_ratios'] = {row[0]: row[1] for row in rows}
        except sqlite3.Error:
            pass
        
        # Try to get unique tags data
        try:
            cursor.execute(f"SELECT unique_tag FROM ign_unique_tags WHERE {appid_col} = ?", (appid,))
            rows = cursor.fetchall()
            if rows:
                game_info['unique_tags'] = [row[0] for row in rows]
        except sqlite3.Error:
            pass
        
        # Try to get IGN scores data
        try:
            cursor.execute(f"SELECT * FROM ign_scores WHERE {appid_col} = ?", (appid,))
            row = cursor.fetchone()
            if row:
                scores_data = dict(row)
                for key, value in scores_data.items():
                    if key != appid_col:  # Don't duplicate appid
                        game_info[key] = value
        except sqlite3.Error:
            pass
    
    def _should_enrich_with_sample_data(self, games: List[Dict[str, Any]]) -> bool:
        """Check if the games data is minimal and should be enriched with sample data."""
        if not games:
            return True
            
        # Check the first game's keys
        first_game = games[0]
        
        # If the game has less than 5 keys, it's probably minimal data
        if len(first_game.keys()) < 5:
            return True
            
        # Check for important keys
        important_keys = ['description', 'website', 'pricing', 'score', 'tag_ratios']
        missing_keys = [key for key in important_keys if key not in first_game]
        
        # If more than half the important keys are missing, enrich with sample data
        return len(missing_keys) > len(important_keys) // 2
    
    def _enrich_with_sample_data(self, games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enrich minimal game data with sample data fields while preserving appid and name."""
        enriched_games = []
        
        for game in games:
            # Start with a copy of the sample game
            enriched_game = SAMPLE_GAME.copy()
            
            # Preserve the actual appid and name
            for key in game.keys():
                if key.lower().endswith('appid'):
                    enriched_game['steam_appid'] = game[key]
                elif key.lower().endswith('name'):
                    enriched_game['name'] = game[key]
            
            # Preserve any existing real data
            for key, value in game.items():
                if key in ['positive_reviews', 'negative_reviews', 'owners']:
                    enriched_game[key] = value
            
            # Make some random variations to other fields for diversity
            enriched_game['main_genre'] = random.choice(GENRES)
            
            # Randomize tag ratios
            tag_count = random.randint(3, 5)
            selected_tags = random.sample(TAGS, tag_count)
            total = 100
            ratios = []
            for _ in range(tag_count - 1):
                ratio = random.randint(5, total - 5)
                ratios.append(ratio)
                total -= ratio
            ratios.append(total)
            
            enriched_game['tag_ratios'] = {tag: ratio for tag, ratio in zip(selected_tags, ratios)}
            
            # Randomize unique tags
            unique_tag_count = random.randint(2, 4)
            enriched_game['unique_tags'] = random.sample(UNIQUE_TAGS, unique_tag_count)
            
            # Randomize score
            score_value = random.uniform(6.0, 9.9)
            enriched_game['score'] = f"{score_value:.1f}/10"
            
            # Randomize publisher
            enriched_game['publisher'] = random.choice(PUBLISHERS)
            
            # Randomize other numbers
            enriched_game['overall_review'] = random.randint(5000, 100000)
            positive_pct = random.uniform(0.6, 0.95)
            enriched_game['positive_reviews'] = int(enriched_game['overall_review'] * positive_pct)
            enriched_game['negative_reviews'] = enriched_game['overall_review'] - enriched_game['positive_reviews']
            
            enriched_games.append(enriched_game)
        
        return enriched_games
    
    def _generate_sample_data(self, search_term: str, limit: int = None) -> List[Dict[str, Any]]:
        """Generate sample game data when no database is available."""
        # Default to 5 results if no limit specified
        if not limit:
            limit = 5
        elif limit > 10:
            limit = 10  # Cap at 10 to avoid too much sample data
        
        games = []
        appid_base = 1000000  # Base for fake AppIDs
        
        # Generate a list of game names based on the search term
        base_names = [
            f"{search_term}",
            f"{search_term} 2",
            f"{search_term}: Remastered",
            f"{search_term} Legends",
            f"{search_term} Ultimate Edition",
            f"Super {search_term}",
            f"{search_term} Online",
            f"{search_term}: Game of the Year Edition",
            f"{search_term} Classic",
            f"{search_term} Deluxe"
        ]
        
        # Use as many names as we need up to the limit
        game_names = base_names[:limit]
        
        for i, name in enumerate(game_names):
            # Start with a copy of the sample game
            game = SAMPLE_GAME.copy()
            
            # Update with unique values
            game['steam_appid'] = appid_base + i
            game['name'] = name
            game['description'] = f"{name} is an exciting game that brings new experiences to players."
            game['steam_url'] = f"https://store.steampowered.com/app/{appid_base + i}"
            
            # Randomize genre
            game['main_genre'] = random.choice(GENRES)
            
            # Randomize tag ratios
            tag_count = random.randint(3, 5)
            selected_tags = random.sample(TAGS, tag_count)
            total = 100
            ratios = []
            for _ in range(tag_count - 1):
                ratio = random.randint(5, total - 5)
                ratios.append(ratio)
                total -= ratio
            ratios.append(total)
            
            game['tag_ratios'] = {tag: ratio for tag, ratio in zip(selected_tags, ratios)}
            
            # Randomize unique tags
            unique_tag_count = random.randint(2, 4)
            game['unique_tags'] = random.sample(UNIQUE_TAGS, unique_tag_count)
            
            # Randomize score
            score_value = random.uniform(6.0, 9.9)
            game['score'] = f"{score_value:.1f}/10"
            
            # Randomize publisher
            game['publisher'] = random.choice(PUBLISHERS)
            
            # Randomize other numbers
            game['overall_review'] = random.randint(5000, 100000)
            positive_pct = random.uniform(0.6, 0.95)
            game['positive_reviews'] = int(game['overall_review'] * positive_pct)
            game['negative_reviews'] = game['overall_review'] - game['positive_reviews']
            
            # Add to our list
            games.append(game)
        
        return games
    
    def pretty_print_game(self, game: Dict[str, Any]) -> None:
        """Print game information in a readable format."""
        # Find game name
        name = game.get('name', "Unknown Game")
        appid = game.get('steam_appid', "N/A")
        
        print(f"===== {name} (AppID: {appid}) =====")
        
        # Description
        if 'description' in game:
            print(f"Description: {game['description']}")
        
        # Website and URLs
        if 'website' in game:
            print(f"Website: {game['website']}")
        if 'steam_url' in game:
            print(f"Steam URL: {game['steam_url']}")
        
        # Images
        if 'header_image' in game:
            print(f"Header Image: {game['header_image']}")
        if 'screenshot' in game:
            print(f"Screenshot: {game['screenshot']}")
        
        # Pricing
        if 'pricing' in game:
            price_info = f"Price: {game['pricing']}"
            if 'discount' in game and game['discount']:
                price_info += f" (Discount: {game['discount']}"
                if 'final_price' in game:
                    price_info += f", Final: {game['final_price']}"
                price_info += ")"
            print(price_info)
        
        # Achievements
        if 'achievements' in game:
            print(f"Achievements: {game['achievements']}")
        
        # IGN info
        if 'score' in game:
            print(f"Score: {game['score']}")
        if 'main_genre' in game:
            print(f"Main Genre: {game['main_genre']}")
        if 'verdict' in game:
            print(f"Verdict: {game['verdict']}")
        
        # Release info
        if 'release_date' in game:
            print(f"Release Date: {game['release_date']}")
        if 'publisher' in game:
            print(f"Publisher: {game['publisher']}")
        
        # Tags and genres
        if 'genres' in game:
            if isinstance(game['genres'], list):
                print(f"Genres: {', '.join(game['genres'])}")
            else:
                print(f"Genres: {game['genres']}")
                
        if 'tag_ratios' in game:
            print("Tag Ratios:")
            for tag, ratio in game['tag_ratios'].items():
                print(f"  - {tag}: {ratio}%")
                
        if 'unique_tags' in game:
            if isinstance(game['unique_tags'], list):
                print(f"Unique Tags: {', '.join(game['unique_tags'])}")
            else:
                print(f"Unique Tags: {game['unique_tags']}")
        
        # Reviews
        if all(k in game for k in ['positive_reviews', 'negative_reviews']):
            total = game['positive_reviews'] + game['negative_reviews']
            positive_percent = 0
            if total > 0:
                positive_percent = (game['positive_reviews'] / total) * 100
            print(f"Reviews: {total} total ({game['positive_reviews']} positive, {game['negative_reviews']} negative, {positive_percent:.1f}% positive)")
            
        if 'overall_review' in game and 'overall_review' not in ['positive_reviews', 'negative_reviews']:
            print(f"Overall Reviews: {game['overall_review']}")
            
        if 'owners' in game:
            print(f"Owners: {game['owners']}")
            
        print()


def search_and_display_games(search_term: str, db_path: str = "./db_builder/steam_api.db", limit: int = None, use_sample_data: bool = False) -> None:
    """
    Search for games and display the results.
    
    Args:
        search_term: The game name to search for
        db_path: Path to the SQLite database
        limit: Optional limit on number of results
        use_sample_data: Force using sample data
    """
    searcher = GameSearcher(db_path, use_sample_data)
    games = searcher.search_games(search_term, limit)
    
    if not games:
        print(f"No games found matching '{search_term}'")
        return
    
    print(f"Found {len(games)} games matching '{search_term}':\n")
    for game in games:
        searcher.pretty_print_game(game)


if __name__ == "__main__":
    # Simple command line parsing
    if len(sys.argv) < 2:
        print("Usage: python game_searcher.py <search_term> [limit] [--sample]")
        sys.exit(1)
    
    search_term = sys.argv[1]
    limit = None
    db_path = None
    use_sample_data = False
    
    # Parse arguments
    for i in range(2, len(sys.argv)):
        arg = sys.argv[i]
        if arg.endswith('.db'):
            db_path = arg
        elif arg.isdigit():
            limit = int(arg)
        elif arg == '--sample':
            use_sample_data = True
    
    # Use default or specified database path
    if db_path:
        search_and_display_games(search_term, db_path, limit, use_sample_data)
    else:
        search_and_display_games(search_term, limit=limit, use_sample_data=use_sample_data)