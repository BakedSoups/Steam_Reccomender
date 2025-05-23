from flask import Flask, render_template, request, session, redirect, url_for, jsonify
import sqlite3
import os
import traceback
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import time



import smtplib
from email.message import EmailMessage

app = Flask(__name__)
app.secret_key = "steam_game_recommender_secret_key"
DATABASE_PATH = "./steam_api.db"


class GameSearcher:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path

    def _generate_steam_url(self, steam_appid: int) -> str:
        """Generate Steam store URL from appid"""
        return f"https://store.steampowered.com/app/{steam_appid}/"
        
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
            
            # Generate steam_url if missing
            if appid:
                if not game_info.get('steam_url'):
                    game_info['steam_url'] = self._generate_steam_url(appid)
                    print(f"Generated steam_url for {game_info['name']}: {game_info['steam_url']}")
                
                cursor.execute("SELECT COUNT(*) FROM GameRanx_tags WHERE steam_appid = ?", (appid,))
                gameranx_tag_count = cursor.fetchone()[0]
                
                if gameranx_tag_count > 0:
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
                    cursor.execute("SELECT COUNT(*) FROM ACG_tags WHERE steam_appid = ?", (appid,))
                    acg_tag_count = cursor.fetchone()[0]
                    
                    if acg_tag_count > 0:
                        game_info['data_source'] = 'acg'
                        
                        cursor.execute("SELECT tag, ratio FROM ACG_tags WHERE steam_appid = ?", (appid,))
                        tags = cursor.fetchall()
                        if tags:
                            game_info['tag_ratios'] = {tag[0]: tag[1] for tag in tags}
                            print(f"RESULT: Found {len(game_info['tag_ratios'])} ACG tags for {game_info['name']}")
                        else:
                            print(f"RESULT: {game_info['name']} doesn't have ACG tags")
                            game_info['tag_ratios'] = {}

                        cursor.execute("SELECT unique_tag FROM ACG_unique_tags WHERE steam_appid = ?", (appid,))
                        unique_tags = cursor.fetchall()
                        if unique_tags:
                            game_info['unique_tags'] = [tag[0] for tag in unique_tags]
                        else:
                            game_info['unique_tags'] = []
                        
                        cursor.execute("SELECT score, genre FROM ACG_scores WHERE steam_appid = ?", (appid,))
                        acg_score = cursor.fetchone()
                        if acg_score:
                            game_info['score'] = acg_score[0]
                            game_info['main_genre'] = acg_score[1]
                        else:
                            game_info['main_genre'] = ""
                            
                    else:
                        cursor.execute("SELECT COUNT(*) FROM ign_tags WHERE steam_appid = ?", (appid,))
                        ign_tag_count = cursor.fetchone()[0]
                        
                        if ign_tag_count > 0:
                            game_info['data_source'] = 'ign'
                            
                            cursor.execute("SELECT tag, ratio FROM ign_tags WHERE steam_appid = ?", (appid,))
                            tags = cursor.fetchall()
                            if tags:
                                game_info['tag_ratios'] = {tag[0]: tag[1] for tag in tags}
                                print(f"RESULT: Found {len(game_info['tag_ratios'])} IGN tags for {game_info['name']}")
                            else:
                                print(f"RESULT: {game_info['name']} doesn't have IGN tags")
                                game_info['tag_ratios'] = {}

                            cursor.execute("SELECT unique_tag FROM ign_unique_tags WHERE steam_appid = ?", (appid,))
                            unique_tags = cursor.fetchall()
                            if unique_tags:
                                game_info['unique_tags'] = [tag[0] for tag in unique_tags]
                            else:
                                game_info['unique_tags'] = []
                            
                            cursor.execute("SELECT score, genre FROM ign_scores WHERE steam_appid = ?", (appid,))
                            ign_score = cursor.fetchone()
                            if ign_score:
                                game_info['score'] = ign_score[0]
                                game_info['main_genre'] = ign_score[1]
                            else:
                                game_info['main_genre'] = ""
                                
                        else:
                            cursor.execute("SELECT COUNT(*) FROM SteamReview_tags WHERE steam_appid = ?", (appid,))
                            steamreview_tag_count = cursor.fetchone()[0]
                            
                            if steamreview_tag_count > 0:
                                game_info['data_source'] = 'steamreview'
                                
                                cursor.execute("SELECT tag, ratio FROM SteamReview_tags WHERE steam_appid = ?", (appid,))
                                tags = cursor.fetchall()
                                if tags:
                                    game_info['tag_ratios'] = {tag[0]: tag[1] for tag in tags}
                                    print(f"RESULT: Found {len(game_info['tag_ratios'])} SteamReview tags for {game_info['name']}")
                                else:
                                    print(f"RESULT: {game_info['name']} doesn't have SteamReview tags")
                                    game_info['tag_ratios'] = {}

                                cursor.execute("SELECT unique_tag FROM SteamReview_unique_tags WHERE steam_appid = ?", (appid,))
                                unique_tags = cursor.fetchall()
                                if unique_tags:
                                    game_info['unique_tags'] = [tag[0] for tag in unique_tags]
                                else:
                                    game_info['unique_tags'] = []
                                
                                cursor.execute("SELECT score, genre FROM SteamReview_scores WHERE steam_appid = ?", (appid,))
                                steamreview_score = cursor.fetchone()
                                if steamreview_score:
                                    game_info['score'] = steamreview_score[0]
                                    game_info['main_genre'] = steamreview_score[1]
                                else:
                                    game_info['main_genre'] = ""
                            else:
                                print(f"Game {game_info.get('name')} doesn't have tags in any database")
                                return {}  # empty if no tags found anywhere
                
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
                
                if 'header_image' not in game_info or not game_info['header_image']:
                    game_info['header_image'] = "/static/logo.png"
                
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
        existing_appids = []
        all_games = []
        
        try:
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
                
                for row in cursor.fetchall():
                    game_info = dict(row)
                    appid = game_info.get('steam_appid')
                    
                    if appid:
                        game_info['data_source'] = 'gameranx'
                        existing_appids.append(appid)
                        
                        cursor.execute("SELECT genre FROM GameRanx_scores WHERE steam_appid = ?", (appid,))
                        score = cursor.fetchone()
                        if score:
                            game_info['genre'] = score[0]
                        else:
                            game_info['genre'] = "Game"
                            
                        if 'header_image' not in game_info or not game_info['header_image']:
                            game_info['header_image'] = "/static/logo.png"
                        
                        all_games.append(game_info)
                
                print(f"Found {len(all_games)} games with GameRanx tags for '{search_term}'")
            except Exception as e:
                print(f"Error querying GameRanx tags: {str(e)}")
            
            if len(all_games) < limit:
                remaining_limit = limit - len(all_games)
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
                
                try:
                    cursor.execute(acg_query, (search_pattern, remaining_limit * 3))
                    
                    for row in cursor.fetchall():
                        game_info = dict(row)
                        appid = game_info.get('steam_appid')
                        
                        if appid and appid not in existing_appids:
                            game_info['data_source'] = 'acg'
                            existing_appids.append(appid)
                            
                            cursor.execute("SELECT genre FROM ACG_scores WHERE steam_appid = ?", (appid,))
                            score = cursor.fetchone()
                            if score:
                                game_info['genre'] = score[0]
                            else:
                                game_info['genre'] = "Game"
                                
                            if 'header_image' not in game_info or not game_info['header_image']:
                                game_info['header_image'] = "/static/logo.png"
                            
                            all_games.append(game_info)
                            
                            if len(all_games) >= limit:
                                break
                    
                    print(f"Found {len(all_games)} total games after adding ACG for '{search_term}'")
                except Exception as e:
                    print(f"Error querying ACG tags: {str(e)}")
            
            # Priority 3: IGN (if we still need more games)
            if len(all_games) < limit:
                remaining_limit = limit - len(all_games)
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
                    cursor.execute(ign_query, (search_pattern, remaining_limit * 3))
                    
                    for row in cursor.fetchall():
                        game_info = dict(row)
                        appid = game_info.get('steam_appid')
                        
                        if appid and appid not in existing_appids:
                            game_info['data_source'] = 'ign'
                            existing_appids.append(appid)
                            
                            cursor.execute("SELECT genre FROM ign_scores WHERE steam_appid = ?", (appid,))
                            score = cursor.fetchone()
                            if score:
                                game_info['genre'] = score[0]
                            else:
                                game_info['genre'] = "Game"
                                
                            if 'header_image' not in game_info or not game_info['header_image']:
                                game_info['header_image'] = "/static/logo.png"
                            
                            all_games.append(game_info)
                            
                            if len(all_games) >= limit:
                                break
                    
                    print(f"Found {len(all_games)} total games after adding IGN for '{search_term}'")
                except Exception as e:
                    print(f"Error querying IGN tags: {str(e)}")
            
            # Priority 4: SteamReview (last resort if we still need more games)
            if len(all_games) < limit:
                remaining_limit = limit - len(all_games)
                steamreview_query = """
                SELECT m.game_name as name, m.steam_appid, a.header_image
                FROM main_game m
                LEFT JOIN steam_api a ON m.steam_appid = a.steam_appid
                INNER JOIN SteamReview_tags st ON m.steam_appid = st.steam_appid
                WHERE LOWER(m.game_name) LIKE LOWER(?)
                GROUP BY m.steam_appid
                ORDER BY COUNT(st.tag) DESC
                LIMIT ?
                """
                
                try:
                    cursor.execute(steamreview_query, (search_pattern, remaining_limit * 3))
                    
                    for row in cursor.fetchall():
                        game_info = dict(row)
                        appid = game_info.get('steam_appid')
                        
                        if appid and appid not in existing_appids:
                            game_info['data_source'] = 'steamreview'
                            existing_appids.append(appid)
                            
                            cursor.execute("SELECT genre FROM SteamReview_scores WHERE steam_appid = ?", (appid,))
                            score = cursor.fetchone()
                            if score:
                                game_info['genre'] = score[0]
                            else:
                                game_info['genre'] = "Game"
                                
                            if 'header_image' not in game_info or not game_info['header_image']:
                                game_info['header_image'] = "/static/logo.png"
                            
                            all_games.append(game_info)
                            
                            if len(all_games) >= limit:
                                break
                    
                    print(f"Found {len(all_games)} total games after adding SteamReview for '{search_term}'")
                except Exception as e:
                    print(f"Error querying SteamReview tags: {str(e)}")
            
            print(f"Returning {len(all_games)} total games for search '{search_term}'")
            return all_games[:limit]
            
        except Exception as e:
            print(f"Error in search_games: {str(e)}")
            traceback.print_exc()
            return []
        finally:
            conn.close()

    def find_similar_games(self, tag_ratios: Dict[str, int], preferred_tag: str, 
                           unique_tags: List[str], main_genre: str, data_source: str = 'ign', limit: int = 10) -> List[Dict[str, Any]]:
        if not tag_ratios:
            print("No tag ratios provided for comparison")
            return []
            
        if not os.path.exists(self.db_path):
            return []
            
        start_time = time.time()
        
        # Determine table names based on data source
        if data_source == 'gameranx':
            tags_table = "GameRanx_tags"
            scores_table = "GameRanx_scores"
            unique_tags_table = "GameRanx_unique_tags"
        elif data_source == 'acg':
            tags_table = "ACG_tags"
            scores_table = "ACG_scores"
            unique_tags_table = "ACG_unique_tags"
        elif data_source == 'steamreview':
            tags_table = "SteamReview_tags"
            scores_table = "SteamReview_scores"
            unique_tags_table = "SteamReview_unique_tags"
        else:
            tags_table = "ign_tags"
            scores_table = "ign_scores"
            unique_tags_table = "ign_unique_tags"
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        try:
            reference_appid = session.get('reference_game', {}).get('steam_appid')
            reference_tags = set(tag_ratios.keys())
            
            tag_placeholders = ','.join(['?' for _ in reference_tags])
            fast_query = f"""
            SELECT DISTINCT t.steam_appid, m.game_name, 
                   s.positive_reviews, s.negative_reviews,
                   a.header_image, a.pricing, a.steam_url,
                   sc.genre
            FROM {tags_table} t
            INNER JOIN main_game m ON t.steam_appid = m.steam_appid
            LEFT JOIN steam_spy s ON t.steam_appid = s.steam_appid
            LEFT JOIN steam_api a ON t.steam_appid = a.steam_appid
            LEFT JOIN {scores_table} sc ON t.steam_appid = sc.steam_appid
            WHERE t.tag IN ({tag_placeholders})
            AND t.steam_appid != ?
            ORDER BY IFNULL(s.positive_reviews, 0) DESC
            LIMIT 200
            """
            
            params = list(reference_tags) + [reference_appid or 0]
            cursor.execute(fast_query, params)
            candidate_games = cursor.fetchall()
            
            print(f"Found {len(candidate_games)} candidate games in {time.time() - start_time:.2f}s")
            
            if not candidate_games:
                return []
            
            chunk_size = 50
            good_games = []
            processed = 0
            
            for i in range(0, len(candidate_games), chunk_size):
                chunk = candidate_games[i:i + chunk_size]
                chunk_results = self._process_game_chunk(chunk, tag_ratios, preferred_tag, 
                                                       unique_tags, main_genre, data_source, 
                                                       tags_table, unique_tags_table, cursor)
                good_games.extend(chunk_results)
                processed += len(chunk)
                
                if len(good_games) >= limit * 2:  # Get a bit more for better sorting
                    print(f"Early termination: found {len(good_games)} games after processing {processed}/{len(candidate_games)}")
                    break
            
            good_games.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
            result_games = good_games[:limit]
            
            total_time = time.time() - start_time
            print(f"Fast similarity search completed in {total_time:.2f}s - returning {len(result_games)} games")
            
            return result_games
            
        finally:
            conn.close()
    
    def _process_game_chunk(self, chunk, tag_ratios, preferred_tag, unique_tags, main_genre, 
                           data_source, tags_table, unique_tags_table, cursor):
        """Process a chunk of games efficiently"""
        good_games = []
        
        chunk_appids = [game['steam_appid'] for game in chunk]
        appid_placeholders = ','.join(['?' for _ in chunk_appids])
        
        tags_query = f"SELECT steam_appid, tag, ratio FROM {tags_table} WHERE steam_appid IN ({appid_placeholders})"
        cursor.execute(tags_query, chunk_appids)
        all_tags = cursor.fetchall()
        
        unique_query = f"SELECT steam_appid, unique_tag FROM {unique_tags_table} WHERE steam_appid IN ({appid_placeholders})"
        cursor.execute(unique_query, chunk_appids)
        all_unique_tags = cursor.fetchall()
        
        tags_by_appid = {}
        unique_tags_by_appid = {}
        
        for row in all_tags:
            appid = row['steam_appid']
            if appid not in tags_by_appid:
                tags_by_appid[appid] = {}
            tags_by_appid[appid][row['tag']] = row['ratio']
        
        for row in all_unique_tags:
            appid = row['steam_appid']
            if appid not in unique_tags_by_appid:
                unique_tags_by_appid[appid] = []
            unique_tags_by_appid[appid].append(row['unique_tag'])
        
        for game_row in chunk:
            game_dict = dict(game_row)
            appid = game_dict['steam_appid']
            game_tags = tags_by_appid.get(appid, {})
            game_unique_tags = unique_tags_by_appid.get(appid, [])
            
            common_tags = set(tag_ratios.keys()).intersection(set(game_tags.keys()))
            if len(common_tags) < 2:
                continue
            
            similarity_score = self._calculate_similarity_fast(
                tag_ratios, game_tags, preferred_tag, unique_tags, game_unique_tags, 
                main_genre, game_dict.get('genre', '')
            )
            
            if similarity_score < 30:  # Adjust threshold as needed
                continue
            
            # Generate steam_url if missing - THIS WAS THE MISSING PIECE!
            steam_url = game_dict.get('steam_url')
            if not steam_url and appid:
                steam_url = self._generate_steam_url(appid)
                print(f"Generated steam_url for {game_dict['game_name']}: {steam_url}")
            
            game_info = {
                'steam_appid': appid,
                'name': game_dict['game_name'],
                'main_genre': game_dict.get('genre', ''),
                'tag_ratios': game_tags,
                'unique_tags': game_unique_tags,
                'similarity_score': similarity_score,
                'data_source': data_source,
                'header_image': game_dict.get('header_image') or "/static/logo.png",
                'release_date': "Unknown",
                'steam_url': steam_url  # Add the steam_url here!
            }
            
            positive = int(game_dict.get('positive_reviews', 0) or 0)
            negative = int(game_dict.get('negative_reviews', 0) or 0)
            total = positive + negative
            
            game_info.update({
                'positive_reviews': positive,
                'negative_reviews': negative,
                'overall_review': total,
                'positive_percentage': round((positive / total) * 100) if total > 0 else 0
            })
            
            if game_dict.get('pricing'):
                game_info['final_price'] = game_dict['pricing']
                game_info['pricing'] = game_dict['pricing']  # Also include pricing for template
                game_info['discount'] = None
            else:
                game_info['final_price'] = "Unknown"
                game_info['pricing'] = "Unknown"
                game_info['discount'] = None
            
            good_games.append(game_info)
        
        return good_games
    
    def _calculate_similarity_fast(self, ref_tags, game_tags, preferred_tag, ref_unique_tags, 
                                  game_unique_tags, ref_genre, game_genre):
        """Fast similarity calculation"""
        if not game_tags:
            return 0
        
        # Tag similarity (vectorized approach)
        tag_similarity_score = 0
        common_tags = 0
        
        for tag, ref_ratio in ref_tags.items():
            if tag in game_tags:
                common_tags += 1
                similarity = 100 - abs(ref_ratio - game_tags[tag])
                if tag == preferred_tag:
                    similarity *= 1.5  # Boost preferred tag
                tag_similarity_score += similarity
        
        if common_tags == 0:
            return 0
        
        # Average tag similarity
        avg_tag_similarity = tag_similarity_score / common_tags
        
        # Unique tags overlap (fast set operations)
        ref_unique_set = set(ref_unique_tags)
        game_unique_set = set(game_unique_tags)
        overlap_count = len(ref_unique_set.intersection(game_unique_set))
        unique_tags_score = overlap_count * 20  # Scale factor
        
        # Genre bonus
        genre_multiplier = 1.2 if (ref_genre and game_genre and 
                                  ref_genre.lower() == game_genre.lower()) else 1.0
        
        # Combined score with weights
        final_score = (avg_tag_similarity * 0.8 + unique_tags_score * 0.2) * genre_multiplier
        
        return final_score

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
    session['data_source'] = reference_game.get('data_source', 'ign')
    
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
    data_source = session.get('data_source', 'ign')
    reference_game = session.get('reference_game', {})
    
    if not tag_ratios:
        print("No tag ratios found in session")
        return render_template('results.html', 
                          games=[], 
                          reference_game=reference_game,
                          preferred_tag="No tag data available")
    
    try:
        print(f"Finding similar games for preferred tag: '{preferred_tag}' using {data_source} data")
        start_time = time.time()
        
        searcher = GameSearcher()
        similar_games = searcher.find_similar_games(
            tag_ratios=tag_ratios,
            preferred_tag=preferred_tag,
            unique_tags=unique_tags,
            main_genre=main_genre,
            data_source=data_source,
            limit=10  # Only get top 10 for speed
        )
        
        total_time = time.time() - start_time
        print(f"Recommendation completed in {total_time:.2f}s - found {len(similar_games)} games")
        
        # Debug: Check if steam_url is present
        for game in similar_games:
            if game.get('steam_url'):
                print(f"✓ {game['name']} has steam_url: {game['steam_url']}")
            else:
                print(f"✗ {game['name']} missing steam_url!")
        
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


#FEEDBACK FORM --------------------------------
def send_feedback_email(thumb, comments):
    msg = EmailMessage()
    msg['Subject'] = 'New Steam Game Feedback'
    msg['From'] = EMAIL_SENDER
    msg['To'] = EMAIL_RECEIVER

    content = f"""
    New feedback submitted:

    Thumb: {'👍' if thumb == 'up' else '👎'}
    Comments: {comments or 'No additional comments'}
    """
    msg.set_content(content)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    thumb = request.form.get('thumb')
    comments = request.form.get('comments')

    send_feedback_email(thumb, comments)

    return redirect(url_for('index'))


@app.route('/api/search', methods=['GET'])
def api_search():
    search_query = request.args.get('search_query', request.args.get('q', ''))
    print(f"Search query received: '{search_query}' - Args: {request.args}")
    
    if len(search_query) < 2:
        if request.headers.get('HX-Request'):
            return render_template('partials/search_results.html', games=[])
        return jsonify([])
    
    try:
        searcher = GameSearcher()
        games = searcher.search_games(search_query, limit=10)
        
        print(f"Game search results: {len(games)} - sample: {games[0] if games else 'No games found'}")
        
        if request.headers.get('HX-Request') or 'text/html' in request.headers.get('Accept', ''):
            print(f"HTMX search for '{search_query}' found {len(games)} results")
            return render_template('partials/search_results.html', games=games)
        
        results = []
        for game in games:
            results.append({
                'id': game.get('steam_appid'),
                'name': game.get('name', ''),
                'image': game.get('header_image', '/static/logo.png'),
                'genre': game.get('genre', ''),
                'data_source': game.get('data_source', 'ign')
            })
        
        print(f"API search for '{search_query}' found {len(results)} results")
        
        return jsonify(results)
    except Exception as e:
        print(f"Error in API search: {str(e)}")
        traceback.print_exc()
        if request.headers.get('HX-Request'):
            return render_template('partials/search_results.html', games=[])
        return jsonify([])

if __name__ == '__main__':
    app.run(debug=True)