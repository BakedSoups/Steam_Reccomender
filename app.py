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
                # First check if game has GameRanx tags
                cursor.execute("SELECT COUNT(*) FROM GameRanx_tags WHERE steam_appid = ?", (appid,))
                gameranx_tag_count = cursor.fetchone()[0]
                
                if gameranx_tag_count > 0:
                    # Use GameRanx data
                    game_info['data_source'] = 'gameranx'
                    
                    cursor.execute("SELECT tag, ratio FROM GameRanx_tags WHERE steam_appid = ?", (appid,))
                    tags = cursor.fetchall()
                    if tags:
                        game_info['tag_ratios'] = {tag[0]: tag[1] for tag in tags}
                        print(f"RESULT: Found {len(game_info['tag_ratios'])} GameRanx tags for {game_info['name']}")
                    else:
                        print(f"RESULT: {game_info['name']} doesn't have GameRanx tags")
                        game_info['tag_ratios'] = {}

                    cursor.execute("SELECT unique_tag FROM GameRanx_unique_tags WHERE steam_appid = ?", (appid,))
                    unique_tags = cursor.fetchall()
                    if unique_tags:
                        game_info['unique_tags'] = [tag[0] for tag in unique_tags]
                    else:
                        game_info['unique_tags'] = []
                    
                    cursor.execute("SELECT score, genre FROM GameRanx_scores WHERE steam_appid = ?", (appid,))
                    gameranx_score = cursor.fetchone()
                    if gameranx_score:
                        game_info['score'] = gameranx_score[0]
                        game_info['main_genre'] = gameranx_score[1]
                    else:
                        game_info['main_genre'] = ""
                else:
                    # Second, check if game has ACG tags
                    cursor.execute("SELECT COUNT(*) FROM ACG_tags WHERE steam_appid = ?", (appid,))
                    acg_tag_count = cursor.fetchone()[0]
                    
                    if acg_tag_count > 0:
                        # Use ACG data
                        game_info['data_source'] = 'acg'
                        
                        # Get tags and ratios from ACG
                        cursor.execute("SELECT tag, ratio FROM ACG_tags WHERE steam_appid = ?", (appid,))
                        tags = cursor.fetchall()
                        if tags:
                            game_info['tag_ratios'] = {tag[0]: tag[1] for tag in tags}
                            print(f"RESULT: Found {len(game_info['tag_ratios'])} ACG tags for {game_info['name']}")
                        else:
                            print(f"RESULT: {game_info['name']} doesn't have ACG tags")
                            game_info['tag_ratios'] = {}

                        # Get unique tags from ACG
                        cursor.execute("SELECT unique_tag FROM ACG_unique_tags WHERE steam_appid = ?", (appid,))
                        unique_tags = cursor.fetchall()
                        if unique_tags:
                            game_info['unique_tags'] = [tag[0] for tag in unique_tags]
                        else:
                            game_info['unique_tags'] = []
                        
                        # Get genre from ACG scores
                        cursor.execute("SELECT score, genre FROM ACG_scores WHERE steam_appid = ?", (appid,))
                        acg_score = cursor.fetchone()
                        if acg_score:
                            game_info['score'] = acg_score[0]
                            game_info['main_genre'] = acg_score[1]
                        else:
                            game_info['main_genre'] = ""
                    else:
                        # Lastly, check for IGN tags
                        cursor.execute("SELECT COUNT(*) FROM ign_tags WHERE steam_appid = ?", (appid,))
                        ign_tag_count = cursor.fetchone()[0]
                        
                        if ign_tag_count == 0:
                            print(f"Game {game_info.get('name')} doesn't have tags in any database")
                            return {}  # Return empty if no tags, this will redirect to index
                        
                        # Use IGN data
                        game_info['data_source'] = 'ign'
                        
                        # Get tags and ratios from IGN
                        cursor.execute("SELECT tag, ratio FROM ign_tags WHERE steam_appid = ?", (appid,))
                        tags = cursor.fetchall()
                        if tags:
                            game_info['tag_ratios'] = {tag[0]: tag[1] for tag in tags}
                            print(f"RESULT: Found {len(game_info['tag_ratios'])} IGN tags for {game_info['name']}")
                        else:
                            print(f"RESULT: {game_info['name']} doesn't have IGN tags")
                            game_info['tag_ratios'] = {}

                        # Get unique tags from IGN
                        cursor.execute("SELECT unique_tag FROM ign_unique_tags WHERE steam_appid = ?", (appid,))
                        unique_tags = cursor.fetchall()
                        if unique_tags:
                            game_info['unique_tags'] = [tag[0] for tag in unique_tags]
                        else:
                            game_info['unique_tags'] = []
                        
                        # Get genre from IGN scores
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
            # First try to get games with GameRanx tags
            gameranx_query = """
            SELECT m.game_name as name, m.steam_appid, a.header_image
            FROM main_game m
            LEFT JOIN steam_api a ON m.steam_appid = a.steam_appid
            INNER JOIN GameRanx_tags gt ON m.steam_appid = gt.steam_appid
            WHERE LOWER(m.game_name) LIKE LOWER(?)
            GROUP BY m.steam_appid
            ORDER BY COUNT(gt.tag) DESC
            LIMIT ?
            """
            
            try:
                cursor.execute(gameranx_query, (search_pattern, limit))
                gameranx_games = []
                
                for row in cursor.fetchall():
                    game_info = dict(row)
                    appid = game_info.get('steam_appid')
                    
                    if appid:
                        game_info['data_source'] = 'gameranx'
                        
                        # Get genre from GameRanx
                        cursor.execute("SELECT genre FROM GameRanx_scores WHERE steam_appid = ?", (appid,))
                        score = cursor.fetchone()
                        if score:
                            game_info['genre'] = score[0]
                        else:
                            game_info['genre'] = "Game"
                            
                        if 'header_image' not in game_info or not game_info['header_image']:
                            game_info['header_image'] = "/static/logo.png"
                        
                        gameranx_games.append(game_info)
                
                print(f"Found {len(gameranx_games)} games with GameRanx tags for '{search_term}'")
                
                # If we have enough GameRanx games, return them
                if len(gameranx_games) >= limit:
                    return gameranx_games
                
                # Otherwise, we'll add ACG games to fill up to the limit
                remaining_limit = limit - len(gameranx_games)
            except Exception as e:
                print(f"Error querying GameRanx tags: {str(e)}")
                gameranx_games = []
                remaining_limit = limit
            
            # Get ACG tagged games that aren't already in gameranx_games
            acg_query = """
            SELECT m.game_name as name, m.steam_appid, a.header_image
            FROM main_game m
            LEFT JOIN steam_api a ON m.steam_appid = a.steam_appid
            INNER JOIN ACG_tags at ON m.steam_appid = at.steam_appid
            WHERE LOWER(m.game_name) LIKE LOWER(?)
            GROUP BY m.steam_appid
            ORDER BY COUNT(at.tag) DESC
            LIMIT ?
            """
            
            existing_appids = [game.get('steam_appid') for game in gameranx_games]
            
            try:
                cursor.execute(acg_query, (search_pattern, remaining_limit * 3))  # Get more than needed to filter duplicates
                
                acg_games = []
                for row in cursor.fetchall():
                    game_info = dict(row)
                    appid = game_info.get('steam_appid')
                    
                    if appid and appid not in existing_appids:
                        game_info['data_source'] = 'acg'
                        
                        # Get genre from ACG
                        cursor.execute("SELECT genre FROM ACG_scores WHERE steam_appid = ?", (appid,))
                        score = cursor.fetchone()
                        if score:
                            game_info['genre'] = score[0]
                        else:
                            game_info['genre'] = "Game"
                            
                        if 'header_image' not in game_info or not game_info['header_image']:
                            game_info['header_image'] = "/static/logo.png"
                        
                        acg_games.append(game_info)
                        existing_appids.append(appid)
                        
                        if len(acg_games) >= remaining_limit:
                            break
                
                print(f"Found {len(acg_games)} games with ACG tags for '{search_term}'")
                
                # If we have enough games with GameRanx + ACG, return them
                if len(gameranx_games) + len(acg_games) >= limit:
                    return gameranx_games + acg_games
                
                # Otherwise, we'll add IGN games to fill up to the limit
                remaining_limit = limit - len(gameranx_games) - len(acg_games)
            except Exception as e:
                print(f"Error querying ACG tags: {str(e)}")
                acg_games = []
                remaining_limit = limit - len(gameranx_games)
            
            # Get IGN tagged games that aren't already in gameranx_games or acg_games
            ign_query = """
            SELECT m.game_name as name, m.steam_appid, a.header_image
            FROM main_game m
            LEFT JOIN steam_api a ON m.steam_appid = a.steam_appid
            INNER JOIN ign_tags it ON m.steam_appid = it.steam_appid
            WHERE LOWER(m.game_name) LIKE LOWER(?)
            GROUP BY m.steam_appid
            ORDER BY COUNT(it.tag) DESC
            LIMIT ?
            """
            
            try:
                cursor.execute(ign_query, (search_pattern, remaining_limit * 3))  # Get more than needed to filter duplicates
                
                ign_games = []
                for row in cursor.fetchall():
                    game_info = dict(row)
                    appid = game_info.get('steam_appid')
                    
                    if appid and appid not in existing_appids:
                        game_info['data_source'] = 'ign'
                        
                        # Get genre from IGN
                        cursor.execute("SELECT genre FROM ign_scores WHERE steam_appid = ?", (appid,))
                        score = cursor.fetchone()
                        if score:
                            game_info['genre'] = score[0]
                        else:
                            game_info['genre'] = "Game"
                            
                        if 'header_image' not in game_info or not game_info['header_image']:
                            game_info['header_image'] = "/static/logo.png"
                        
                        ign_games.append(game_info)
                        
                        if len(ign_games) >= remaining_limit:
                            break
                
                print(f"Found {len(ign_games)} games with IGN tags for '{search_term}'")
            except Exception as e:
                print(f"Error querying IGN tags: {str(e)}")
                ign_games = []
            
            # Combine the results, prioritizing GameRanx > ACG > IGN
            combined_games = gameranx_games + acg_games + ign_games
            print(f"Returning {len(combined_games)} total games for search '{search_term}'")
            
            return combined_games
            
        except Exception as e:
            print(f"Error in search_games: {str(e)}")
            traceback.print_exc()
            return []
        finally:
            conn.close()
    
    def find_similar_games(self, tag_ratios: Dict[str, int], preferred_tag: str, 
                           unique_tags: List[str], main_genre: str, data_source: str = 'ign', limit: int = 5) -> List[Dict[str, Any]]:
        if not tag_ratios:
            print("No tag ratios provided for comparison")
            return []
            
        if not os.path.exists(self.db_path):
            return []
            
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
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
            """
            cursor.execute(query)
            
            all_games = []
            reference_appid = session.get('reference_game', {}).get('steam_appid')
            
            # Determine which tag tables to use based on data_source
            if data_source == 'gameranx':
                tags_table = "GameRanx_tags"
                scores_table = "GameRanx_scores"
                unique_tags_table = "GameRanx_unique_tags"
            elif data_source == 'acg':
                tags_table = "ACG_tags"
                scores_table = "ACG_scores"
                unique_tags_table = "ACG_unique_tags"
            else:  # default to 'ign'
                tags_table = "ign_tags"
                scores_table = "ign_scores"
                unique_tags_table = "ign_unique_tags"
            
            for row in cursor.fetchall():
                game_info = dict(row)
                appid = game_info.get('steam_appid')
                
                if appid == reference_appid:
                    continue
                
                # Get the game's tags from the same source as the reference game
                cursor.execute(f"SELECT tag, ratio FROM {tags_table} WHERE steam_appid = ?", (appid,))
                tags = cursor.fetchall()
                if not tags:
                    # Skip games without matching tags in the same database
                    continue
                
                game_info['tag_ratios'] = {tag[0]: tag[1] for tag in tags}
                game_info['data_source'] = data_source
                
                cursor.execute(f"SELECT score, genre FROM {scores_table} WHERE steam_appid = ?", (appid,))
                score_row = cursor.fetchone()
                if score_row:
                    game_info['score'] = score_row[0]
                    game_info['main_genre'] = score_row[1]
                else:
                    game_info['main_genre'] = ""
                
                cursor.execute(f"SELECT unique_tag FROM {unique_tags_table} WHERE steam_appid = ?", (appid,))
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
            print(f"Found {len(result_games)} similar games using {data_source} data")
            
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
    session['data_source'] = reference_game.get('data_source', 'ign')  # Store the data source
    
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
    data_source = session.get('data_source', 'ign')  # Get the data source
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
            data_source=data_source,  # Pass the data source
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
    
    try:
        searcher = GameSearcher()
        games = searcher.search_games(search_query, limit=10)
        
        results = []
        for game in games:
            results.append({
                'id': game.get('steam_appid'),
                'name': game.get('name', ''),
                'image': game.get('header_image', '/static/logo.png'),
                'genre': game.get('genre', ''),
                'data_source': game.get('data_source', 'ign')  # Include data source in results
            })
        
        print(f"API search for '{search_query}' found {len(results)} results")
        
        return jsonify(results)
    except Exception as e:
        print(f"Error in API search: {str(e)}")
        traceback.print_exc()
        return jsonify([])

if __name__ == '__main__':
    app.run(debug=True)