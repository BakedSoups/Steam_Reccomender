import requests
import sqlite3
import json
import time
import re
from datetime import datetime
from typing import Dict, List, Optional
import random

class SteamTagsFetcher:
    def __init__(self, db_path="steam_api.db"):
        self.db_path = db_path
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
    def get_games_from_database(self) -> List[Dict]:
        """Get all games from the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT game_id, game_name, steam_appid FROM main_game ORDER BY steam_appid")
            games = cursor.fetchall()
            
            conn.close()
            
            return [{"game_id": row[0], "game_name": row[1], "steam_appid": row[2]} for row in games]
        
        except Exception as e:
            print(f"Error reading database: {e}")
            return []
    
    def fetch_steam_tags(self, appid: int, game_name: str) -> List[str]:
        """Fetch official Steam tags for a game"""
        try:
            # Method 1: Try Steam Store API first
            tags = self._fetch_from_store_api(appid)
            if tags:
                return tags
            
            # Method 2: Try Steam Store page scraping
            tags = self._fetch_from_store_page(appid)
            if tags:
                return tags
            
            print(f"No tags found for {game_name} (appid: {appid})")
            return []
            
        except Exception as e:
            print(f"Error fetching tags for {game_name} (appid: {appid}): {e}")
            return []
    
    def _fetch_from_store_api(self, appid: int) -> List[str]:
        """Fetch tags from Steam Store API"""
        try:
            url = f"https://store.steampowered.com/api/appdetails"
            params = {
                'appids': appid,
                'filters': 'categories,genres'
            }
            
            response = self.session.get(url, params=params, timeout=10)
            data = response.json()
            
            if str(appid) in data and data[str(appid)]['success']:
                app_data = data[str(appid)]['data']
                tags = []
                
                # Get genres
                if 'genres' in app_data:
                    for genre in app_data['genres']:
                        tags.append(genre['description'].lower())
                
                # Get categories (like Single-player, Multiplayer, etc.)
                if 'categories' in app_data:
                    for category in app_data['categories']:
                        tag = category['description'].lower()
                        # Filter useful categories
                        if any(keyword in tag for keyword in ['player', 'co-op', 'pvp', 'controller', 'vr', 'trading']):
                            tags.append(tag)
                
                return tags[:10]  # Limit to top 10
                
        except Exception as e:
            print(f"Store API error for appid {appid}: {e}")
            
        return []
    
    def _fetch_from_store_page(self, appid: int) -> List[str]:
        """Fetch tags by scraping Steam store page"""
        try:
            url = f"https://store.steampowered.com/app/{appid}/"
            
            response = self.session.get(url, timeout=15)
            if response.status_code != 200:
                return []
            
            html = response.text
            
            # Method 1: Look for popular tags section
            tags = self._extract_popular_tags(html)
            if tags:
                return tags
            
            # Method 2: Look for genre/category info
            tags = self._extract_genre_info(html)
            if tags:
                return tags
                
            return []
            
        except Exception as e:
            print(f"Store page scraping error for appid {appid}: {e}")
            return []
    
    def _extract_popular_tags(self, html: str) -> List[str]:
        """Extract popular user-defined tags from HTML"""
        tags = []
        
        # Pattern for popular tags section
        tag_patterns = [
            r'class="app_tag"[^>]*>([^<]+)</a>',
            r'data-tag-name="([^"]+)"',
            r'class="glance_tag popular_tags"[^>]*>([^<]+)</span>',
        ]
        
        for pattern in tag_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                tag = match.strip().lower()
                if len(tag) > 2 and len(tag) < 30 and tag not in tags:
                    tags.append(tag)
        
        return tags[:15]  # Top 15 tags
    
    def _extract_genre_info(self, html: str) -> List[str]:
        """Extract genre and category information from HTML"""
        tags = []
        
        # Look for genre information
        genre_patterns = [
            r'Genre:</b>\s*([^<]+)',
            r'genre[^>]*>([^<]+)</a>',
        ]
        
        for pattern in genre_patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)
            for match in matches:
                # Clean up and split multiple genres
                genres = re.split(r'[,\n]', match)
                for genre in genres:
                    tag = genre.strip().lower()
                    if len(tag) > 2 and tag not in tags:
                        tags.append(tag)
        
        return tags
    
    def normalize_tags(self, tags: List[str]) -> List[str]:
        """Normalize and clean up tags"""
        normalized = []
        
        # Tag normalization mapping
        tag_mapping = {
            'single-player': 'singleplayer',
            'multi-player': 'multiplayer',
            'co-op': 'cooperative',
            'role playing': 'rpg',
            'role-playing': 'rpg',
            'first-person': 'fps',
            'real-time strategy': 'rts',
            'turn-based strategy': 'turn-based',
            'action rpg': 'action-rpg',
            'japanese rpg': 'jrpg',
            'massively multiplayer': 'mmo',
            'battle royale': 'battle-royale',
            'city builder': 'city-building',
            'tower defense': 'tower-defense'
        }
        
        for tag in tags:
            # Clean the tag
            clean_tag = re.sub(r'[^\w\s-]', '', tag.lower().strip())
            clean_tag = re.sub(r'\s+', '-', clean_tag)
            
            # Apply mapping if exists
            clean_tag = tag_mapping.get(clean_tag, clean_tag)
            
            # Filter out very short or very long tags
            if 2 < len(clean_tag) < 25 and clean_tag not in normalized:
                normalized.append(clean_tag)
        
        return normalized[:10]  # Limit to top 10
    
    def save_checkpoint(self, results: Dict, filename='checkpoint_steam_tags.json'):
        """Save progress checkpoint"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"Checkpoint saved: {len(results)} games processed")
    
    def load_checkpoint(self, filename='checkpoint_steam_tags.json') -> Dict:
        """Load existing checkpoint"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def process_all_games(self):
        """Process all games and fetch their Steam tags"""
        print("🎮 Steam Official Tags Fetcher")
        print("=" * 50)
        
        # Load existing results or checkpoint
        results_file = 'steam_official_tags.json'
        results = self.load_checkpoint()
        
        if not results:
            try:
                with open(results_file, 'r', encoding='utf-8') as f:
                    results = json.load(f)
                print(f"Loaded {len(results)} existing tag records")
            except FileNotFoundError:
                results = {}
        
        games = self.get_games_from_database()
        if not games:
            print("No games found in database!")
            return
        
        print(f"Found {len(games)} games in database")
        print(f"Already processed: {len(results)} games")
        
        # Filter unprocessed games
        remaining_games = []
        for game in games:
            appid_str = str(game["steam_appid"])
            if appid_str not in results:
                remaining_games.append(game)
        
        print(f"Remaining to process: {len(remaining_games)} games")
        
        if not remaining_games:
            print("All games already processed!")
            return
        
        # Process games with rate limiting
        for i, game in enumerate(remaining_games, 1):
            appid = game["steam_appid"]
            game_name = game["game_name"]
            
            print(f"\n[{i}/{len(remaining_games)}] Processing: {game_name} (appid: {appid})")
            
            # Fetch tags
            raw_tags = self.fetch_steam_tags(appid, game_name)
            normalized_tags = self.normalize_tags(raw_tags)
            
            # Store results
            results[str(appid)] = {
                "name": game_name,
                "appid": appid,
                "tags": normalized_tags,
                "raw_tags": raw_tags,  # Keep original for reference
                "fetched_date": datetime.now().isoformat(),
                "tag_count": len(normalized_tags)
            }
            
            if normalized_tags:
                print(f"✓ Found {len(normalized_tags)} tags: {', '.join(normalized_tags[:5])}")
            else:
                print("✗ No tags found")
            
            # Rate limiting and checkpoint saving
            if i % 50 == 0:
                self.save_checkpoint(results)
                print(f"Progress: {i}/{len(remaining_games)} games processed")
                time.sleep(2)  # Brief pause every 50 games
            else:
                # Random delay between requests (1-3 seconds)
                delay = random.uniform(1.0, 3.0)
                time.sleep(delay)
        
        # Final save
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*60}")
        print(f"🎉 Steam tags fetching complete!")
        print(f"Total games processed: {len(results)}")
        print(f"Results saved to: {results_file}")
        
        # Statistics
        games_with_tags = sum(1 for data in results.values() if data.get("tag_count", 0) > 0)
        total_tags = sum(data.get("tag_count", 0) for data in results.values())
        
        print(f"\nStatistics:")
        print(f"- Games with tags: {games_with_tags}/{len(results)} ({games_with_tags/len(results)*100:.1f}%)")
        print(f"- Total tags collected: {total_tags}")
        print(f"- Average tags per game: {total_tags/len(results):.1f}")
        
        # Most common tags
        tag_frequency = {}
        for data in results.values():
            for tag in data.get("tags", []):
                tag_frequency[tag] = tag_frequency.get(tag, 0) + 1
        
        if tag_frequency:
            print(f"\nMost common tags:")
            sorted_tags = sorted(tag_frequency.items(), key=lambda x: x[1], reverse=True)
            for i, (tag, count) in enumerate(sorted_tags[:15], 1):
                print(f"{i:2d}. {tag}: {count} games")
        
        # Cleanup checkpoint
        import os
        checkpoint_file = 'checkpoint_steam_tags.json'
        if os.path.exists(checkpoint_file):
            os.remove(checkpoint_file)
            print("\nCheckpoint file removed")

def analyze_steam_tags(filename='steam_official_tags.json'):
    """Analyze the collected Steam tags"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"🔍 Steam Tags Analysis")
        print("=" * 40)
        print(f"Total games: {len(data)}")
        
        # Tag statistics
        tag_frequency = {}
        games_with_tags = 0
        total_tags = 0
        
        for appid, game_data in data.items():
            tags = game_data.get("tags", [])
            if tags:
                games_with_tags += 1
                total_tags += len(tags)
                
                for tag in tags:
                    tag_frequency[tag] = tag_frequency.get(tag, 0) + 1
        
        print(f"Games with tags: {games_with_tags} ({games_with_tags/len(data)*100:.1f}%)")
        print(f"Average tags per game: {total_tags/len(data):.1f}")
        print(f"Unique tags found: {len(tag_frequency)}")
        
        # Top tags
        print(f"\nTop 20 most common tags:")
        sorted_tags = sorted(tag_frequency.items(), key=lambda x: x[1], reverse=True)
        for i, (tag, count) in enumerate(sorted_tags[:20], 1):
            percentage = count / len(data) * 100
            print(f"{i:2d}. {tag}: {count} games ({percentage:.1f}%)")
        
        # Examples of well-tagged games
        print(f"\nExample well-tagged games:")
        well_tagged = [(appid, data) for appid, data in data.items() if len(data.get("tags", [])) >= 5]
        well_tagged.sort(key=lambda x: len(x[1].get("tags", [])), reverse=True)
        
        for i, (appid, game_data) in enumerate(well_tagged[:10], 1):
            tags = ', '.join(game_data.get("tags", [])[:6])
            print(f"{i:2d}. {game_data.get('name', 'Unknown')}: {tags}")
        
        return data
        
    except FileNotFoundError:
        print(f"File {filename} not found!")
        return None

def search_by_steam_tag(tag_name: str, filename='steam_official_tags.json', limit: int = 20):
    """Search games by Steam tag"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        matching_games = []
        tag_lower = tag_name.lower()
        
        for appid, game_data in data.items():
            tags = [t.lower() for t in game_data.get("tags", [])]
            if tag_lower in tags:
                matching_games.append({
                    "name": game_data.get("name", "Unknown"),
                    "appid": appid,
                    "tags": game_data.get("tags", []),
                    "steam_url": f"https://store.steampowered.com/app/{appid}"
                })
        
        print(f"🎮 Games tagged with '{tag_name}' ({len(matching_games)} found):")
        print("-" * 50)
        
        for i, game in enumerate(matching_games[:limit], 1):
            other_tags = [t for t in game["tags"] if t.lower() != tag_lower][:5]
            print(f"{i:2d}. {game['name']}")
            print(f"      Other tags: {', '.join(other_tags)}")
            print(f"     {game['steam_url']}")
        
        return matching_games
        
    except FileNotFoundError:
        print(f"File {filename} not found!")
        return []

if __name__ == "__main__":
    # Run the Steam tags fetcher
    fetcher = SteamTagsFetcher()
    fetcher.process_all_games()
    
    # Analyze results
    print("\n" + "="*60)
    analyze_steam_tags()
    
    # Example searches
    print("\n" + "="*60)
    print("🔍 Example tag searches:")
    search_by_steam_tag("jrpg", limit=10)
    search_by_steam_tag("souls-like", limit=10)