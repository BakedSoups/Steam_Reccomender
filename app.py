from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import sqlite3
import os
from typing import List, Dict, Any

app = Flask(__name__)
app.secret_key = "steam_game_recommender_secret_key"  # Used for session

# Database path - update this to match your database location
DATABASE_PATH = "./steam_api.db"

class GameSearcher:
    def __init__(self, db_path: str = DATABASE_PATH):
        """Initialize with the path to the SQLite database."""
        self.db_path = db_path
    
    def search_game_by_name(self, search_term: str) -> Dict[str, Any]:
        """
        Search for a specific game by name to use as a reference.
        Returns the first match or sample data if none found.
        """
        if not os.path.exists(self.db_path):
            return self.get_sample_game(search_term)
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term}%"
        
        try:
            # Search by game name
            query = """
            SELECT m.game_name as name, m.steam_appid, 
                   s.positive_reviews, s.negative_reviews, s.owners,
                   a.detail_id, a.description, a.website, a.header_image, 
                   a.background, a.screenshot, a.steam_url, a.pricing, a.achievements
            FROM main_game m
            LEFT JOIN steam_spy s ON m.steam_appid = s.steam_appid
            LEFT JOIN steam_api a ON m.steam_appid = a.steam_appid
            WHERE LOWER(m.game_name) LIKE LOWER(?)
            LIMIT 1
            """
            cursor.execute(query, (search_pattern,))
            
            row = cursor.fetchone()
            if not row:
                return self.get_sample_game(search_term)
                
            game_info = dict(row)
            appid = game_info.get('steam_appid')
            
            if appid:
                # Add IGN scores and genre
                cursor.execute("SELECT score, genre FROM ign_scores WHERE steam_appid = ?", (appid,))
                ign_score = cursor.fetchone()
                if ign_score:
                    game_info['score'] = ign_score[0]
                    game_info['main_genre'] = ign_score[1]
                else:
                    game_info['score'] = "8.0/10"
                    game_info['main_genre'] = "Action"

                # Add IGN tags with ratios
                cursor.execute("SELECT tag, ratio FROM ign_tags WHERE steam_appid = ?", (appid,))
                tags = cursor.fetchall()
                if tags:
                    game_info['tag_ratios'] = {tag[0]: tag[1] for tag in tags}
                else:
                    game_info['tag_ratios'] = {"fps": 40, "action": 30, "rpg": 30}

                # Add IGN unique tags
                cursor.execute("SELECT unique_tag FROM ign_unique_tags WHERE steam_appid = ?", (appid,))
                unique_tags = cursor.fetchall()
                if unique_tags:
                    game_info['unique_tags'] = [tag[0] for tag in unique_tags]
                else:
                    game_info['unique_tags'] = ["popular", "multiplayer"]

                # Ensure header_image is set
                if 'header_image' not in game_info or not game_info['header_image']:
                    game_info['header_image'] = "/static/logo.png"
            
            return game_info
            
        finally:
            conn.close()
    
    def search_games(self, search_term: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for games by name for the live search feature.
        Returns a list of matching games with basic info.
        """
        if not os.path.exists(self.db_path):
            return self.get_sample_data(search_term)
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term}%"
        
        try:
            # Search by game name with limit
            query = """
            SELECT m.game_name, m.steam_appid, 
                   a.header_image,
                   (IFNULL(s.positive_reviews, 0) + IFNULL(s.negative_reviews, 0)) as total_reviews
            FROM main_game m
            LEFT JOIN steam_spy s ON m.steam_appid = s.steam_appid
            LEFT JOIN steam_api a ON m.steam_appid = a.steam_appid
            WHERE LOWER(m.game_name) LIKE LOWER(?)
            ORDER BY total_reviews DESC
            LIMIT ?
            """
            cursor.execute(query, (search_pattern, limit))
            
            games = []
            for row in cursor.fetchall():
                game_info = dict(row)
                appid = game_info.get('steam_appid')
                
                if appid:
                    # Add IGN genre
                    cursor.execute("SELECT genre FROM ign_scores WHERE steam_appid = ?", (appid,))
                    ign_score = cursor.fetchone()
                    if ign_score:
                        game_info['genre'] = ign_score[0]
                    else:
                        game_info['genre'] = "Game"

                    # Ensure header_image is set
                    if 'header_image' not in game_info or not game_info['header_image']:
                        game_info['header_image'] = "/static/logo.png"
                
                games.append(game_info)
            
            return games
            
        finally:
            conn.close()
    
    def find_similar_games(self, tag_ratios: Dict[str, int], preferred_tag: str, 
                           unique_tags: List[str], limit: int = 10) -> List[Dict[str, Any]]:
        """
        Find games similar to the given tag ratios and unique tags,
        with emphasis on the preferred tag.
        """
        if not os.path.exists(self.db_path):
            return self.get_sample_data(preferred_tag)
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Get all games with their tags
            query = """
            SELECT m.game_name as name, m.steam_appid, 
                   s.positive_reviews, s.negative_reviews, s.owners,
                   a.detail_id, a.description, a.website, a.header_image, 
                   a.background, a.screenshot, a.steam_url, a.pricing, a.achievements,
                   (IFNULL(s.positive_reviews, 0) + IFNULL(s.negative_reviews, 0)) as overall_review
            FROM main_game m
            LEFT JOIN steam_spy s ON m.steam_appid = s.steam_appid
            LEFT JOIN steam_api a ON m.steam_appid = a.steam_appid
            """
            cursor.execute(query)
            
            all_games = []
            for row in cursor.fetchall():
                game_info = dict(row)
                appid = game_info.get('steam_appid')
                
                if appid:
                    # Calculate review percentages
                    positive = game_info.get('positive_reviews', 0) or 0
                    negative = game_info.get('negative_reviews', 0) or 0
                    total = positive + negative
                    
                    if total > 0:
                        game_info['positive_percentage'] = round((positive / total) * 100)
                    else:
                        game_info['positive_percentage'] = 0
                        
                    # Set default values for reviews if not present
                    if 'overall_review' not in game_info or not game_info['overall_review']:
                        game_info['overall_review'] = total
                    
                    if 'positive_reviews' not in game_info or game_info['positive_reviews'] is None:
                        game_info['positive_reviews'] = 0
                        
                    if 'negative_reviews' not in game_info or game_info['negative_reviews'] is None:
                        game_info['negative_reviews'] = 0
                    
                    # Add release date if missing
                    if 'release_date' not in game_info or not game_info.get('release_date'):
                        game_info['release_date'] = "2023"
                    
                    # Add IGN scores and genre
                    cursor.execute("SELECT score, genre FROM ign_scores WHERE steam_appid = ?", (appid,))
                    ign_score = cursor.fetchone()
                    if ign_score:
                        game_info['score'] = ign_score[0]
                        game_info['main_genre'] = ign_score[1]
                    else:
                        game_info['main_genre'] = "Action"
                    
                    # Add IGN tags with ratios
                    cursor.execute("SELECT tag, ratio FROM ign_tags WHERE steam_appid = ?", (appid,))
                    tags = cursor.fetchall()
                    if tags:
                        game_info['tag_ratios'] = {tag[0]: tag[1] for tag in tags}
                    else:
                        game_info['tag_ratios'] = {"action": 40, "adventure": 30, "rpg": 30}
                    
                    # Add IGN unique tags
                    cursor.execute("SELECT unique_tag FROM ign_unique_tags WHERE steam_appid = ?", (appid,))
                    unique_tags_db = cursor.fetchall()
                    if unique_tags_db:
                        game_info['unique_tags'] = [tag[0] for tag in unique_tags_db]
                    else:
                        game_info['unique_tags'] = ["popular", "multiplayer"]

                    # Ensure header_image is set
                    if 'header_image' not in game_info or not game_info['header_image']:
                        game_info['header_image'] = "/static/logo.png"

                    # Parse pricing info
                    if 'pricing' in game_info and game_info['pricing']:
                        pricing = game_info['pricing']
                        if 'discount' not in game_info and 'final_price' not in game_info:
                            game_info['discount'] = None
                            game_info['final_price'] = pricing
                    
                    # Calculate similarity score
                    similarity_score = 0
                    
                    # Tag ratio similarity
                    for tag, ratio in tag_ratios.items():
                        if tag in game_info['tag_ratios']:
                            # Calculate how close the ratios are (100 - absolute difference)
                            tag_similarity = 100 - abs(ratio - game_info['tag_ratios'].get(tag, 0))
                            # Weight the preferred tag more heavily
                            if tag == preferred_tag:
                                tag_similarity *= 2
                            similarity_score += tag_similarity
                    
                    # Unique tags overlap
                    game_unique_tags = set(game_info['unique_tags'])
                    reference_unique_tags = set(unique_tags)
                    overlap_tags = game_unique_tags.intersection(reference_unique_tags)
                    similarity_score += len(overlap_tags) * 100  # Each matching unique tag adds 100 points
                    
                    # Add score to game info
                    game_info['similarity_score'] = similarity_score
                    
                    all_games.append(game_info)
            
            # Sort by similarity score
            all_games.sort(key=lambda x: x['similarity_score'], reverse=True)
            
            # Return top N games
            result_games = all_games[:limit]
            
            # If no games found, return sample data
            if not result_games:
                return self.get_sample_data(preferred_tag)
                
            return result_games
            
        finally:
            conn.close()
    
    def get_sample_game(self, search_term: str = "") -> Dict[str, Any]:
        """Return a sample game if database search fails."""
        return {
            "detail_id": 68,
            "steam_appid": 1517290,
            "name": f"{'Sample: ' + search_term.title() if search_term else 'Battlefield™ 2042'}",
            "description": "Battlefield™ 2042 is a first-person shooter that marks the return to the iconic all-out warfare of the franchise.",
            "website": "https://www.ea.com/games/battlefield/battlefield-2042/",
            "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1517290/header.jpg?t=1744718390",
            "background": "https://store.akamai.steamstatic.com/images/storepagebackground/app/1517290?t=1744718390",
            "screenshot": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1517290/a0c5c62e72cafdddb10c4175c1cba00cba0b0fb1/ss_a0c5c62e72cafdddb10c4175c1cba00cba0b0fb1.1920x1080.jpg?t=1744718390",
            "steam_url": "https://store.steampowered.com/app/1517290",
            "pricing": "$59.99",
            "discount": "75%",
            "final_price": "$14.99",
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
    
    def get_sample_data(self, preferred_tag: str = "") -> List[Dict[str, Any]]:
        """Return sample data if database search fails or no results found."""
        base_game = self.get_sample_game()
        games = []
        
        # Create 5 sample games with variations focused on the preferred tag
        for i in range(5):
            game = base_game.copy()
            game["name"] = f"Sample Game {i+1}: {preferred_tag.title()} Adventure"
            game["steam_appid"] = base_game["steam_appid"] + i
            game["game_name"] = game["name"]  # Add game_name for consistency with search_games
            game["genre"] = preferred_tag.title() if preferred_tag else "Action"  # Add genre for live search
            
            # Adjust the tag ratios to emphasize the preferred tag
            tag_ratios = {"fps": 20, "multiplayer": 20, "action": 20, "adventure": 20, "rpg": 20}
            if preferred_tag in tag_ratios:
                tag_ratios[preferred_tag] = 40
                # Redistribute the remaining 60% among other tags
                other_tags = [tag for tag in tag_ratios if tag != preferred_tag]
                for tag in other_tags:
                    tag_ratios[tag] = 60 // len(other_tags)
            game["tag_ratios"] = tag_ratios
            
            # Vary the unique tags but include some related to the preferred tag
            unique_tags_options = [
                ["popular", "multiplayer", "competitive"],
                ["story-rich", "atmospheric", "open-world"],
                ["difficult", "roguelike", "replay-value"],
                ["strategy", "tactical", "turn-based"],
                ["relaxing", "casual", "family-friendly"]
            ]
            game["unique_tags"] = unique_tags_options[i % len(unique_tags_options)]
            
            # Add the preferred tag as a unique tag if not already present
            if preferred_tag not in game["unique_tags"]:
                game["unique_tags"].append(preferred_tag)
                
            # Vary other attributes slightly for diversity
            game["overall_review"] = base_game["overall_review"] + (i * 1000)
            game["positive_reviews"] = int(game["overall_review"] * 0.6)
            game["negative_reviews"] = game["overall_review"] - game["positive_reviews"]
            
            games.append(game)
        
        return games


@app.route('/')
def index():
    # Clear any existing session data
    session.clear()
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    # First step: User enters a reference game
    search_query = request.form.get('search_query', '')
    
    # Find this specific game
    searcher = GameSearcher(DATABASE_PATH)
    reference_game = searcher.search_game_by_name(search_query)
    
    # Store reference game info in session
    session['reference_game'] = reference_game
    
    # Extract the tag ratios to show to the user
    tag_ratios = reference_game.get('tag_ratios', {})
    unique_tags = reference_game.get('unique_tags', [])
    
    # Store in session
    session['tag_ratios'] = tag_ratios
    session['unique_tags'] = unique_tags
    
    return render_template('preference.html', 
                          reference_game=reference_game,
                          tag_ratios=tag_ratios,
                          unique_tags=unique_tags)

@app.route('/recommend', methods=['POST'])
def recommend():
    # Get the user's preferred tag from the form
    preferred_tag = request.form.get('preferred_tag', '')
    
    # Retrieve stored tag ratios and unique tags from session
    tag_ratios = session.get('tag_ratios', {})
    unique_tags = session.get('unique_tags', [])
    reference_game = session.get('reference_game', {})
    
    # If no stored data, redirect to index
    if not tag_ratios or not unique_tags:
        return redirect(url_for('index'))
    
    # Find similar games based on the reference game and preferred tag
    searcher = GameSearcher(DATABASE_PATH)
    similar_games = searcher.find_similar_games(
        tag_ratios=tag_ratios,
        preferred_tag=preferred_tag,
        unique_tags=unique_tags,
        limit=5
    )
    
    # Update the user profile section in the results template
    return render_template('results.html', 
                          games=similar_games, 
                          reference_game=reference_game,
                          preferred_tag=preferred_tag)

# New route for live search API
@app.route('/api/search', methods=['GET'])
def api_search():
    search_query = request.args.get('q', '')
    
    # Return empty list if query is too short
    if len(search_query) < 2:
        return jsonify([])
    
    # Use the GameSearcher to find matching games
    searcher = GameSearcher(DATABASE_PATH)
    games = searcher.search_games(search_query, limit=5)
    
    # Format the results for the frontend
    results = []
    for game in games:
        results.append({
            'id': game.get('steam_appid'),
            'name': game.get('game_name', game.get('name', 'Unknown Game')),
            'image': game.get('header_image', '/static/logo.png'),
            'genre': game.get('genre', game.get('main_genre', 'Game'))
        })
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)