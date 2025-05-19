from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import sqlite3
import os
import traceback
from typing import List, Dict, Any

app = Flask(__name__)
app.secret_key = "steam_game_recommender_secret_key"
DATABASE_PATH = "./steam_api.db"

class GameSearcher:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        
    def search_game_by_name(self, search_term: str) -> Dict[str, Any]:
        if not os.path.exists(self.db_path):
            print(f"Database not found at {self.db_path}")
            return {}
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term}%"
        
        try:
            query = """
            SELECT m.game_name as name, m.steam_appid, 
                   s.positive_reviews, s.negative_reviews, s.owners,
                   a.detail_id, a.description, a.website, a.header_image, 
                   a.background, a.screenshot, a.steam_url, a.pricing, a.achievements,
                   (IFNULL(s.positive_reviews, 0) + IFNULL(s.negative_reviews, 0)) as overall_review
            FROM main_game m
            LEFT JOIN steam_spy s ON m.steam_appid = s.steam_appid
            LEFT JOIN steam_api a ON m.steam_appid = a.steam_appid
            WHERE LOWER(m.game_name) LIKE LOWER(?)
            ORDER BY overall_review DESC
            LIMIT 1
            """
            cursor.execute(query, (search_pattern,))
            
            row = cursor.fetchone()
            if not row:
                print(f"No games found matching '{search_term}'")
                return {}
                
            game_info = dict(row)
            appid = game_info.get('steam_appid')
            
            if appid:
                # Get tags and ratios
                cursor.execute("SELECT tag, ratio FROM ign_tags WHERE steam_appid = ?", (appid,))
                tags = cursor.fetchall()
                if tags:
                    game_info['tag_ratios'] = {tag[0]: tag[1] for tag in tags}
                    print(f"RESULT: Found {len(game_info['tag_ratios'])} tags for {game_info['name']}")
                else:
                    print(f"RESULT: {game_info['name']} doesn't have tags")
                    game_info['tag_ratios'] = {}

                # Get unique tags
                cursor.execute("SELECT unique_tag FROM ign_unique_tags WHERE steam_appid = ?", (appid,))
                unique_tags = cursor.fetchall()
                if unique_tags:
                    game_info['unique_tags'] = [tag[0] for tag in unique_tags]
                else:
                    game_info['unique_tags'] = []
                
                # Get genre
                cursor.execute("SELECT score, genre FROM ign_scores WHERE steam_appid = ?", (appid,))
                ign_score = cursor.fetchone()
                if ign_score:
                    game_info['score'] = ign_score[0]
                    game_info['main_genre'] = ign_score[1]
                else:
                    game_info['main_genre'] = ""
                
                # Calculate review percentages
                positive = int(game_info.get('positive_reviews', 0) or 0)
                negative = int(game_info.get('negative_reviews', 0) or 0)
                total = positive + negative
                
                game_info['positive_reviews'] = positive 
                game_info['negative_reviews'] = negative
                game_info['overall_review'] = total
                
                if total > 0:
                    game_info['positive_percentage'] = round((positive / total) * 100)
                else:
                    game_info['positive_percentage'] = 0
                
                # Defaults for missing fields
                if 'header_image' not in game_info or not game_info['header_image']:
                    game_info['header_image'] = "/static/logo.png"
                
                # Handle pricing
                if 'pricing' in game_info and game_info['pricing']:
                    game_info['discount'] = None
                    game_info['final_price'] = game_info['pricing']
            
            return game_info
            
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
            SELECT m.game_name as name, m.steam_appid, 
                a.header_image
            FROM main_game m
            LEFT JOIN steam_spy s ON m.steam_appid = s.steam_appid
            LEFT JOIN steam_api a ON m.steam_appid = a.steam_appid
            WHERE LOWER(m.game_name) LIKE LOWER(?)
            ORDER BY (IFNULL(s.positive_reviews, 0) + IFNULL(s.negative_reviews, 0)) DESC
            """
            cursor.execute(query, (search_pattern,))
            
            games = []
            count = 0
            
            for row in cursor.fetchall():
                game_info = dict(row)
                appid = game_info.get('steam_appid')
                
                if appid:
                    cursor.execute("SELECT COUNT(*) FROM ign_tags WHERE steam_appid = ?", (appid,))
                    tag_count = cursor.fetchone()[0]
                    
                    if tag_count == 0:
                        continue
                    
                    cursor.execute("SELECT genre FROM ign_scores WHERE steam_appid = ?", (appid,))
                    ign_score = cursor.fetchone()
                    if ign_score:
                        game_info['genre'] = ign_score[0]
                    else:
                        game_info['genre'] = "Game"

                    if 'header_image' not in game_info or not game_info['header_image']:
                        game_info['header_image'] = "/static/logo.png"
                    
                    games.append(game_info)
                    count += 1
                    
                    if count >= limit:
                        break
            
            return games
            
        finally:
            conn.close()
    
    def find_similar_games(self, tag_ratios: Dict[str, int], preferred_tag: str, 
                           unique_tags: List[str], main_genre: str, limit: int = 5) -> List[Dict[str, Any]]:
        if not tag_ratios:
            print("No tag ratios provided for comparison")
            return []
            
        if not os.path.exists(self.db_path):
            return []
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Get all games with basic info - FIXED: removed release_date column
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
            reference_appid = session.get('reference_game', {}).get('steam_appid')
            
            for row in cursor.fetchall():
                game_info = dict(row)
                appid = game_info.get('steam_appid')
                
                if appid == reference_appid:
                    continue
                
                cursor.execute("SELECT tag, ratio FROM ign_tags WHERE steam_appid = ?", (appid,))
                tags = cursor.fetchall()
                if not tags:
                    # Skip games without tags
                    continue
                
                game_info['tag_ratios'] = {tag[0]: tag[1] for tag in tags}
                
                cursor.execute("SELECT score, genre FROM ign_scores WHERE steam_appid = ?", (appid,))
                ign_score = cursor.fetchone()
                if ign_score:
                    game_info['score'] = ign_score[0]
                    game_info['main_genre'] = ign_score[1]
                else:
                    game_info['main_genre'] = ""
                
                cursor.execute("SELECT unique_tag FROM ign_unique_tags WHERE steam_appid = ?", (appid,))
                unique_tags_db = cursor.fetchall()
                if unique_tags_db:
                    game_info['unique_tags'] = [tag[0] for tag in unique_tags_db]
                else:
                    game_info['unique_tags'] = []
                
                if 'header_image' not in game_info or not game_info['header_image']:
                    game_info['header_image'] = "/static/logo.png"
                
                game_info['release_date'] = "Unknown"  # Add default release_date
                
                positive = int(game_info.get('positive_reviews', 0) or 0)
                negative = int(game_info.get('negative_reviews', 0) or 0)
                total = positive + negative
                
                game_info['positive_reviews'] = positive
                game_info['negative_reviews'] = negative
                game_info['overall_review'] = total
                
                if total > 0:
                    game_info['positive_percentage'] = round((positive / total) * 100)
                else:
                    game_info['positive_percentage'] = 0
                
                if 'pricing' in game_info and game_info['pricing']:
                    game_info['discount'] = None
                    game_info['final_price'] = game_info['pricing']
                else:
                    game_info['discount'] = None
                    game_info['final_price'] = "Unknown"
                
                tag_similarity_score = 0
                common_tags = 0
                
                for tag, ratio in tag_ratios.items():
                    if tag in game_info['tag_ratios']:
                        common_tags += 1
                        tag_similarity = 100 - abs(ratio - game_info['tag_ratios'].get(tag, 0))
                        if tag == preferred_tag:
                            tag_similarity *= 1.5
                        tag_similarity_score += tag_similarity
                
                if common_tags == 0:
                    continue
                
                game_unique_tags = set(game_info['unique_tags'])
                reference_unique_tags = set(unique_tags)
                overlap_tags = game_unique_tags.intersection(reference_unique_tags)
                unique_tags_score = len(overlap_tags) * 100
                
                genre_multiplier = 1.0
                if main_genre and game_info['main_genre'] and game_info['main_genre'].lower() != main_genre.lower():
                    genre_multiplier = 0.5
                
                tag_weight = 0.8
                unique_weight = 0.2
                
                final_score = (tag_similarity_score * tag_weight + 
                              unique_tags_score * unique_weight) * genre_multiplier
                
                game_info['similarity_score'] = final_score
                all_games.append(game_info)
            
            all_games.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            
            result_games = all_games[:limit]
            print(f"Found {len(result_games)} similar games")
            
            return result_games
            
        finally:
            conn.close()

@app.route('/')
def index():
    session.clear()
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    search_query = request.form.get('search_query', '')
    if not search_query:
        return redirect(url_for('index'))
    
    searcher = GameSearcher()
    reference_game = searcher.search_game_by_name(search_query)
    
    if not reference_game:
        return redirect(url_for('index'))
    
    # store in session
    session['reference_game'] = reference_game
    session['tag_ratios'] = reference_game.get('tag_ratios', {})
    session['unique_tags'] = reference_game.get('unique_tags', [])
    session['main_genre'] = reference_game.get('main_genre', '')
    
    return render_template('preference.html', 
                      reference_game=reference_game,
                      tag_ratios=reference_game.get('tag_ratios', {}),
                      unique_tags=reference_game.get('unique_tags', []))

@app.route('/recommend', methods=['POST'])
def recommend():
    preferred_tag = request.form.get('preferred_tag', '')
    
    tag_ratios = session.get('tag_ratios', {})
    unique_tags = session.get('unique_tags', [])
    main_genre = session.get('main_genre', '')
    reference_game = session.get('reference_game', {})
    
    if not tag_ratios:
        print("No tag ratios found in session")
        return render_template('results.html', 
                          games=[], 
                          reference_game=reference_game,
                          preferred_tag="No tag data available")
    
    try:
        searcher = GameSearcher()
        similar_games = searcher.find_similar_games(
            tag_ratios=tag_ratios,
            preferred_tag=preferred_tag,
            unique_tags=unique_tags,
            main_genre=main_genre,
            limit=5
        )
        
        return render_template('results.html', 
                          games=similar_games, 
                          reference_game=reference_game,
                          preferred_tag=preferred_tag)
    except Exception as e:
        print(f"Error finding similar games: {str(e)}")
        traceback.print_exc()
        return render_template('results.html',
                          games=[],
                          reference_game=reference_game,
                          preferred_tag=preferred_tag)

@app.route('/api/search', methods=['GET'])
def api_search():
    search_query = request.args.get('q', '')
    
    if len(search_query) < 2:
        return jsonify([])
    
    searcher = GameSearcher()
    games = searcher.search_games(search_query, limit=10)
    
    results = []
    for game in games:
        results.append({
            'id': game.get('steam_appid'),
            'name': game.get('name', ''),
            'image': game.get('header_image', '/static/logo.png'),
            'genre': game.get('genre', '')
        })
    
    return jsonify(results)

if __name__ == '__main__':
    app.run(debug=True)