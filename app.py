from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import sqlite3
import os
import traceback
import numpy as np
import pickle
from typing import List, Dict, Any
from difflib import SequenceMatcher
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)
app.secret_key = "steam_game_recommender_secret_key"

# Database paths
STEAM_API_DB = "./steam_api.db"  # Original database for pricing/images
RECOMMENDATIONS_DB = "./steam_recommendations.db"  # New hierarchical database
VECTORIZER_PATH = "./hierarchical_vectorizer.pkl"

class SQLiteGameSearcher:
    def __init__(self, recommendations_db=RECOMMENDATIONS_DB, steam_api_db=STEAM_API_DB):
        self.recommendations_db = recommendations_db
        self.steam_api_db = steam_api_db
        self.vectorizer = None
        self.load_vectorizer()
    
    def load_vectorizer(self):
        """Load the TF-IDF vectorizer"""
        try:
            with open(VECTORIZER_PATH, 'rb') as f:
                self.vectorizer = pickle.load(f)
            print("✅ Loaded TF-IDF vectorizer")
        except FileNotFoundError:
            print("Vectorizer not found. Run the converter first!")
            self.vectorizer = None
    
    def find_game_by_name(self, query, limit=10):
        """Find games by name using SQLite full-text search"""
        if not os.path.exists(self.recommendations_db):
            print(f"Database not found: {self.recommendations_db}")
            print(f"Current working directory: {os.getcwd()}")
            print(f"Absolute path would be: {os.path.abspath(self.recommendations_db)}")
            return []
        
        conn = sqlite3.connect(self.recommendations_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            query_lower = query.lower().strip()
            
            # Try exact match first
            cursor.execute("""
            SELECT m.steam_appid, m.game_name as name, i.genre as main_genre, '' as sub_genre, '' as sub_sub_genre
            FROM main_game m
            LEFT JOIN ign_scores i ON m.steam_appid = i.steam_appid
            WHERE LOWER(m.game_name) = ?
            LIMIT 1
            """, (query_lower,))
            
            exact_match = cursor.fetchone()
            if exact_match:
                result = self._enhance_game_with_steam_data([dict(exact_match)])[0]
                result['similarity'] = 1.0
                result['match_type'] = 'exact'
                return [result]
            
            # Fuzzy search with ranking
            search_query = """
            SELECT m.steam_appid, m.game_name as name, i.genre as main_genre, '' as sub_genre, '' as sub_sub_genre,
                   CASE 
                       WHEN LOWER(m.game_name) LIKE LOWER(? || '%') THEN 0.9
                       WHEN LOWER(m.game_name) LIKE LOWER('%' || ? || '%') THEN 0.7
                       ELSE 0.5
                   END as similarity_score
            FROM main_game m
            LEFT JOIN ign_scores i ON m.steam_appid = i.steam_appid
            WHERE LOWER(m.game_name) LIKE LOWER('%' || ? || '%')
            ORDER BY similarity_score DESC, m.game_name
            LIMIT ?
            """
            
            cursor.execute(search_query, [query_lower] * 3 + [limit])
            matches = cursor.fetchall()
            
            if matches:
                enhanced_matches = self._enhance_game_with_steam_data([dict(m) for m in matches])
                for i, match in enumerate(enhanced_matches):
                    match['similarity'] = matches[i]['similarity_score']
                    match['match_type'] = 'fuzzy'
                return enhanced_matches
            
            return []
            
        except Exception as e:
            print(f"Error searching games: {e}")
            return []
        finally:
            conn.close()
    
    def _enhance_game_with_steam_data(self, games):
        """Enhance game data with Steam API database info"""
        if not os.path.exists(self.steam_api_db):
            # Return games with default values if Steam DB not available
            for game in games:
                game.update({
                    'header_image': '/static/logo.png',
                    'pricing': 'Unknown',
                    'steam_url': f"https://store.steampowered.com/app/{game['steam_appid']}/"
                })
            return games
        
        conn = sqlite3.connect(self.steam_api_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            for game in games:
                cursor.execute("""
                SELECT a.header_image, a.pricing, a.steam_url,
                       s.positive_reviews, s.negative_reviews
                FROM steam_api a
                LEFT JOIN steam_spy s ON a.steam_appid = s.steam_appid
                WHERE a.steam_appid = ?
                """, (game['steam_appid'],))
                
                steam_data = cursor.fetchone()
                if steam_data:
                    game.update({
                        'header_image': steam_data['header_image'] or '/static/logo.png',
                        'pricing': steam_data['pricing'] or 'Unknown',
                        'steam_url': steam_data['steam_url'] or f"https://store.steampowered.com/app/{game['steam_appid']}/",
                        'positive_reviews': steam_data['positive_reviews'] or 0,
                        'negative_reviews': steam_data['negative_reviews'] or 0
                    })
                else:
                    # Default values if not found in Steam database
                    game.update({
                        'header_image': '/static/logo.png',
                        'pricing': 'Unknown',
                        'steam_url': f"https://store.steampowered.com/app/{game['steam_appid']}/",
                        'positive_reviews': 0,
                        'negative_reviews': 0
                    })
            
            return games
            
        except Exception as e:
            print(f"Error enhancing with Steam data: {e}")
            return games
        finally:
            conn.close()
    
    def get_game_details(self, steam_appid):
        """Get full game details including all tags and classifications"""
        conn = sqlite3.connect(self.recommendations_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Get main game info
            cursor.execute("""
            SELECT m.*, i.genre as main_genre, '' as sub_genre, '' as sub_sub_genre,
                   '' as art_style, '' as theme, '' as music_style
            FROM main_game m
            LEFT JOIN ign_scores i ON m.steam_appid = i.steam_appid
            WHERE m.steam_appid = ?
            """, (steam_appid,))
            
            game = cursor.fetchone()
            if not game:
                return None
            
            game_dict = dict(game)
            
            # Get all tags
            cursor.execute("""
            SELECT tag FROM ign_tags WHERE steam_appid = ? ORDER BY tag
            """, (steam_appid,))
            game_dict['steam_tags'] = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("""
            SELECT tag FROM ign_unique_tags WHERE steam_appid = ? ORDER BY tag
            """, (steam_appid,))
            game_dict['unique_tags'] = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("""
            SELECT tag FROM ign_subjective_tags WHERE steam_appid = ? ORDER BY tag
            """, (steam_appid,))
            game_dict['subjective_tags'] = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("""
            SELECT tag, ratio FROM ign_tags WHERE steam_appid = ?
            """, (steam_appid,))
            game_dict['tag_ratios'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Enhance with Steam API data
            enhanced = self._enhance_game_with_steam_data([game_dict])[0]
            return enhanced
            
        except Exception as e:
            print(f"Error getting game details: {e}")
            return None
        finally:
            conn.close()
    
    def get_available_preferences(self, steam_appid):
        """Get available preference options for a game"""
        game = self.get_game_details(steam_appid)
        if not game:
            return {}
        
        return {
            'hierarchy': {
                'main_genre': game.get('main_genre', ''),
                'sub_genre': game.get('sub_genre', ''),
                'sub_sub_genre': game.get('sub_sub_genre', '')
            },
            'aesthetics': {
                'art_style': game.get('art_style', ''),
                'theme': game.get('theme', ''),
                'music_style': game.get('music_style', '')
            },
            'unique_tags': game.get('unique_tags', []),
            'subjective_tags': game.get('subjective_tags', []),
            'steam_tags': game.get('steam_tags', []),  # Add Steam tags
            'tag_ratios': game.get('tag_ratios', {})
        }
    
    def find_similar_games(self, target_appid, user_preferences=None, limit=10):
        """Find similar games using SQLite-based hierarchical search"""
        conn = sqlite3.connect(self.recommendations_db)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            # Get target game info
            cursor.execute("""
            SELECT m.game_name as name, i.genre as main_genre, '' as sub_genre, '' as sub_sub_genre, 
                   '' as art_style, '' as theme, '' as music_style
            FROM main_game m
            LEFT JOIN ign_scores i ON m.steam_appid = i.steam_appid
            WHERE m.steam_appid = ?
            """, (target_appid,))
            
            target_game = cursor.fetchone()
            if not target_game:
                return []
            
            target_dict = dict(target_game)
            main_genre = target_dict['main_genre']
            sub_genre = target_dict['sub_genre']
            sub_sub_genre = target_dict['sub_sub_genre']
            
            print(f"Finding games similar to: {target_dict['name']}")
            print(f"Hierarchy: {main_genre} → {sub_genre} → {sub_sub_genre}")
            
            # Check if soulslike
            is_soulslike = self._is_soulslike_game_sql(target_appid, cursor)
            if is_soulslike:
                print(" Detected soulslike game - prioritizing soulslike mechanics")
            
            # Get candidates using SQL hierarchy search
            candidates = self._get_sql_candidates(target_appid, main_genre, sub_genre, sub_sub_genre, is_soulslike, cursor)
            
            if not candidates:
                return []
            
            # Calculate similarities using vectors if available
            if self.vectorizer:
                similarities = self._calculate_vector_similarities(target_appid, candidates, user_preferences, cursor)
            else:
                similarities = self._calculate_tag_similarities(target_appid, candidates, user_preferences, cursor)
            
            # Enhance with Steam API data
            enhanced_games = []
            for sim in similarities[:limit]:
                game_details = self.get_game_details(sim['steam_appid'])
                if game_details:
                    enhanced_games.append({
                        'appid': str(sim['steam_appid']),
                        'game': game_details,
                        'similarity': sim['similarity'],
                        'base_similarity': sim.get('base_similarity', sim['similarity']),
                        'hierarchy_bonus': sim.get('hierarchy_bonus', 0),
                        'preference_bonus': sim.get('preference_bonus', 0),
                        'match_type': sim['match_type']
                    })
            
            return enhanced_games
            
        except Exception as e:
            print(f"Error finding similar games: {e}")
            traceback.print_exc()
            return []
        finally:
            conn.close()
    
    def _is_soulslike_game_sql(self, steam_appid, cursor):
        """Check if game is soulslike using SQL queries"""
        # Check name
        cursor.execute("SELECT game_name FROM main_game WHERE steam_appid = ?", (steam_appid,))
        name = cursor.fetchone()
        if name and any(indicator in name[0].lower() for indicator in ['souls', 'elden ring', 'bloodborne']):
            return True
        
        # Check tags
        cursor.execute("""
        SELECT COUNT(*) FROM ign_unique_tags 
        WHERE steam_appid = ? AND (
            LOWER(tag) LIKE '%souls%' OR 
            LOWER(tag) LIKE '%soulslike%' OR 
            LOWER(tag) LIKE '%stamina%' OR
            LOWER(tag) LIKE '%challenging-but-fair%'
        )
        """, (steam_appid,))
        
        if cursor.fetchone()[0] > 0:
            return True
        
        # Check sub-sub genre (not available in current schema)
        # cursor.execute("""
        # SELECT sub_sub_genre FROM games 
        # WHERE steam_appid = ? AND LOWER(sub_sub_genre) LIKE '%souls%'
        # """, (steam_appid,))
        
        return False
    
    def _get_sql_candidates(self, target_appid, main_genre, sub_genre, sub_sub_genre, is_soulslike, cursor):
        """Get candidate games using SQL hierarchy search"""
        candidates = []
        
        # Soulslike matches (if applicable)
        if is_soulslike:
            cursor.execute("""
            SELECT DISTINCT g.steam_appid, 'soulslike' as match_type, 0.5 as hierarchy_bonus
            FROM main_game g
            LEFT JOIN ign_unique_tags ut ON g.steam_appid = ut.steam_appid
            WHERE g.steam_appid != ? AND (
                LOWER(g.game_name) LIKE '%souls%' OR
                LOWER(ut.tag) LIKE '%souls%' OR
                LOWER(ut.tag) LIKE '%soulslike%'
            )
            LIMIT 20
            """, (target_appid,))
            
            candidates.extend([(row[0], row[1], row[2]) for row in cursor.fetchall()])
        
        # Exact hierarchy matches (simplified since we don't have sub-genres in current schema)
        cursor.execute("""
        SELECT m.steam_appid, 'exact' as match_type, 0.4 as hierarchy_bonus
        FROM main_game m
        LEFT JOIN ign_scores i ON m.steam_appid = i.steam_appid
        WHERE m.steam_appid != ? AND i.genre = ?
        LIMIT 15
        """, (target_appid, main_genre))
        
        candidates.extend([(row[0], row[1], row[2]) for row in cursor.fetchall() 
                          if row[0] not in [c[0] for c in candidates]])
        
        # Similar genre matches (using random selection since we don't have fine-grained genres)
        cursor.execute("""
        SELECT m.steam_appid, 'similar' as match_type, 0.2 as hierarchy_bonus
        FROM main_game m
        LEFT JOIN ign_scores i ON m.steam_appid = i.steam_appid
        WHERE m.steam_appid != ? AND (i.genre = ? OR i.genre IS NULL)
        ORDER BY RANDOM()
        LIMIT 25
        """, (target_appid, main_genre))
        
        candidates.extend([(row[0], row[1], row[2]) for row in cursor.fetchall() 
                          if row[0] not in [c[0] for c in candidates]])
        
        print(f"Found {len(candidates)} candidates")
        return candidates[:50]  # Limit for performance
    
    def _calculate_vector_similarities(self, target_appid, candidates, user_preferences, cursor):
        """Calculate similarities using stored vectors"""
        try:
            # Get target vector
            cursor.execute("SELECT vector_data FROM game_vectors WHERE steam_appid = ?", (target_appid,))
            target_row = cursor.fetchone()
            if not target_row:
                return self._calculate_tag_similarities(target_appid, candidates, user_preferences, cursor)
            
            target_vector = np.frombuffer(target_row[0], dtype=np.float64).reshape(1, -1)
            
            similarities = []
            for candidate_appid, match_type, hierarchy_bonus in candidates:
                cursor.execute("SELECT vector_data FROM game_vectors WHERE steam_appid = ?", (candidate_appid,))
                candidate_row = cursor.fetchone()
                
                if candidate_row:
                    candidate_vector = np.frombuffer(candidate_row[0], dtype=np.float64).reshape(1, -1)
                    base_sim = cosine_similarity(target_vector, candidate_vector)[0][0]
                    
                    # Apply user preference bonus
                    preference_bonus = self._calculate_preference_bonus_sql(candidate_appid, user_preferences, cursor)
                    
                    final_score = min(1.0, base_sim + hierarchy_bonus + preference_bonus)
                    
                    similarities.append({
                        'steam_appid': candidate_appid,
                        'similarity': final_score,
                        'base_similarity': base_sim,
                        'hierarchy_bonus': hierarchy_bonus,
                        'preference_bonus': preference_bonus,
                        'match_type': match_type
                    })
            
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            return similarities
            
        except Exception as e:
            print(f"Error in vector similarity: {e}")
            return self._calculate_tag_similarities(target_appid, candidates, user_preferences, cursor)
    
    def _calculate_tag_similarities(self, target_appid, candidates, user_preferences, cursor):
        """Fallback tag-based similarity calculation"""
        # Get target game tags
        cursor.execute("""
        SELECT tag FROM ign_unique_tags WHERE steam_appid = ?
        UNION
        SELECT tag FROM ign_subjective_tags WHERE steam_appid = ?
        """, (target_appid, target_appid))
        
        target_tags = set(row[0] for row in cursor.fetchall())
        
        similarities = []
        for candidate_appid, match_type, hierarchy_bonus in candidates:
            # Get candidate tags
            cursor.execute("""
            SELECT tag FROM ign_unique_tags WHERE steam_appid = ?
            UNION
            SELECT tag FROM ign_subjective_tags WHERE steam_appid = ?
            """, (candidate_appid, candidate_appid))
            
            candidate_tags = set(row[0] for row in cursor.fetchall())
            
            # Jaccard similarity
            if len(target_tags) > 0 and len(candidate_tags) > 0:
                intersection = len(target_tags & candidate_tags)
                union = len(target_tags | candidate_tags)
                base_sim = intersection / union if union > 0 else 0
            else:
                base_sim = 0
            
            # Apply preference bonus
            preference_bonus = self._calculate_preference_bonus_sql(candidate_appid, user_preferences, cursor)
            
            final_score = min(1.0, base_sim + hierarchy_bonus + preference_bonus)
            
            similarities.append({
                'steam_appid': candidate_appid,
                'similarity': final_score,
                'base_similarity': base_sim,
                'hierarchy_bonus': hierarchy_bonus,
                'preference_bonus': preference_bonus,
                'match_type': match_type
            })
        
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities
    
    def _calculate_preference_bonus_sql(self, candidate_appid, user_preferences, cursor):
        """Calculate preference bonus using SQL queries"""
        if not user_preferences:
            return 0
        
        bonus = 0
        
        # Aesthetic preferences (not available in current schema - skipped)
        
        # Unique/subjective tag preferences
        preferred_tags = user_preferences.get('preferred_tags', [])
        if preferred_tags:
            placeholders = ','.join(['?' for _ in preferred_tags])
            cursor.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT tag FROM ign_unique_tags WHERE steam_appid = ? AND tag IN ({placeholders})
                UNION
                SELECT tag FROM ign_subjective_tags WHERE steam_appid = ? AND tag IN ({placeholders})
            )
            """, [candidate_appid] + preferred_tags + [candidate_appid] + preferred_tags)
            
            matching_count = cursor.fetchone()[0]
            if matching_count > 0:
                bonus += (matching_count / len(preferred_tags)) * 0.15
        
        # Steam tag preferences (NEW)
        preferred_steam_tags = user_preferences.get('preferred_steam_tags', [])
        if preferred_steam_tags:
            placeholders = ','.join(['?' for _ in preferred_steam_tags])
            cursor.execute(f"""
            SELECT COUNT(*) FROM ign_tags 
            WHERE steam_appid = ? AND tag IN ({placeholders})
            """, [candidate_appid] + preferred_steam_tags)
            
            matching_steam_tags = cursor.fetchone()[0]
            if matching_steam_tags > 0:
                # Steam tags get higher weight since they're more specific to what users want
                steam_tag_bonus = (matching_steam_tags / len(preferred_steam_tags)) * 0.25
                bonus += steam_tag_bonus
                
                # Extra bonus for popular combinations
                popular_combos = {
                    ('roguelike', 'procedural generation'): 0.1,
                    ('souls-like', 'difficult'): 0.1,
                    ('metroidvania', 'exploration'): 0.1,
                    ('platformer', 'pixel graphics'): 0.05,
                    ('puzzle', 'relaxing'): 0.05
                }
                
                selected_tags_lower = [tag.lower() for tag in preferred_steam_tags]
                for combo, combo_bonus in popular_combos.items():
                    if all(tag in selected_tags_lower for tag in combo):
                        # Check if candidate has this combo too
                        cursor.execute(f"""
                        SELECT COUNT(*) FROM ign_tags 
                        WHERE steam_appid = ? AND LOWER(tag) IN ({','.join(['?' for _ in combo])})
                        """, [candidate_appid] + list(combo))
                        
                        if cursor.fetchone()[0] == len(combo):
                            bonus += combo_bonus
        
        return bonus

# Initialize the search engine
game_searcher = SQLiteGameSearcher()

@app.route('/')
def index():
    session.clear()
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    search_query = request.form.get('search_query', '')
    if not search_query:
        return redirect(url_for('index'))
    
    matches = game_searcher.find_game_by_name(search_query)
    
    if not matches:
        return redirect(url_for('index'))
    
    # Take the best match
    best_match = matches[0]
    target_appid = best_match['steam_appid']
    
    # Get full game details
    reference_game = game_searcher.get_game_details(target_appid)
    if not reference_game:
        return redirect(url_for('index'))
    
    # Get available preferences
    preferences = game_searcher.get_available_preferences(target_appid)
    
    # Store in session
    session['reference_game'] = reference_game
    session['target_appid'] = target_appid
    session['available_preferences'] = preferences
    
    return render_template('preference_hierarchical.html', 
                          reference_game=reference_game,
                          preferences=preferences)

@app.route('/recommend', methods=['POST'])
def recommend():
    target_appid = session.get('target_appid')
    reference_game = session.get('reference_game', {})
    
    if not target_appid:
        return redirect(url_for('index'))
    
    # Get user preferences from form
    user_preferences = {
        'aesthetics': {},
        'preferred_tags': [],
        'preferred_steam_tags': []  # Add Steam tags
    }
    
    # Aesthetic preferences
    for aesthetic in ['art_style', 'theme', 'music_style']:
        pref_value = request.form.get(f'prefer_{aesthetic}')
        if pref_value:
            user_preferences['aesthetics'][aesthetic] = pref_value
    
    # Unique/subjective tag preferences
    preferred_tags = request.form.getlist('preferred_tags')
    user_preferences['preferred_tags'] = preferred_tags
    
    # Steam tag preferences (NEW)
    preferred_steam_tags = request.form.getlist('preferred_steam_tags')
    user_preferences['preferred_steam_tags'] = preferred_steam_tags
    
    print(f"User preferences: {user_preferences}")
    
    # Find similar games
    similar_games = game_searcher.find_similar_games(target_appid, user_preferences, limit=10)
    
    return render_template('results_hierarchical.html',
                          games=similar_games,
                          reference_game=reference_game,
                          user_preferences=user_preferences)

@app.route('/api/search', methods=['GET'])
def api_search():
    search_query = request.args.get('search_query', request.args.get('q', ''))
    
    if len(search_query) < 2:
        if request.headers.get('HX-Request'):
            return render_template('partials/search_results.html', games=[])
        return jsonify([])
    
    try:
        matches = game_searcher.find_game_by_name(search_query, limit=10)
        
        if request.headers.get('HX-Request') or 'text/html' in request.headers.get('Accept', ''):
            return render_template('partials/search_results.html', games=matches)
        
        results = []
        for match in matches:
            results.append({
                'id': match['steam_appid'],
                'name': match['name'],
                'image': match['header_image'],
                'genre': f"{match['main_genre']} → {match['sub_genre']}",
                'data_source': 'hierarchical'
            })
        
        return jsonify(results)
    except Exception as e:
        print(f"Error in API search: {str(e)}")
        traceback.print_exc()
        if request.headers.get('HX-Request'):
            return render_template('partials/search_results.html', games=[])
        return jsonify([])

@app.route('/debug/game/<int:steam_appid>')
def debug_game(steam_appid):
    """Debug endpoint to see game details"""
    game = game_searcher.get_game_details(steam_appid)
    preferences = game_searcher.get_available_preferences(steam_appid)
    
    return jsonify({
        'game': game,
        'preferences': preferences
    })

@app.route('/debug/stats')
def debug_stats():
    """Debug endpoint to see database statistics"""
    conn = sqlite3.connect(game_searcher.recommendations_db)
    cursor = conn.cursor()
    
    try:
        stats = {}
        
        # Basic counts
        cursor.execute("SELECT COUNT(*) FROM main_game")
        stats['total_games'] = cursor.fetchone()[0]
        
        # Top genres
        cursor.execute("""
        SELECT i.genre, COUNT(*) as count
        FROM main_game m
        LEFT JOIN ign_scores i ON m.steam_appid = i.steam_appid
        WHERE i.genre IS NOT NULL
        GROUP BY i.genre
        ORDER BY count DESC
        LIMIT 20
        """)
        stats['top_genres'] = cursor.fetchall()
        
        # Popular tags
        cursor.execute("""
        SELECT tag, COUNT(*) as count
        FROM ign_unique_tags
        GROUP BY tag
        ORDER BY count DESC
        LIMIT 20
        """)
        stats['popular_unique_tags'] = cursor.fetchall()
        
        return jsonify(stats)
    finally:
        conn.close()

if __name__ == '__main__':
    print("Starting Flask app with SQLite hierarchical search...")
    
    if not os.path.exists(RECOMMENDATIONS_DB):
        print(f"{RECOMMENDATIONS_DB} not found!")
        print("Please run the JSON converter first: python json_to_sqlite_converter.py")
    else:
        print(f"Found recommendations database: {RECOMMENDATIONS_DB}")
    
    if not os.path.exists(STEAM_API_DB):
        print(f" {STEAM_API_DB} not found - images and pricing will use defaults")
    else:
        print(f"Found Steam API database: {STEAM_API_DB}")
    
    app.run(debug=True)