import sqlite3
import os
from typing import List, Dict, Any, Optional, Tuple
from contextlib import contextmanager
from abc import ABC, abstractmethod


class DatabaseRepository(ABC):
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def exists(self) -> bool:
        return os.path.exists(self.db_path)


class RecommendationsRepository(DatabaseRepository):
    def find_games_by_name(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        if not self.exists():
            return []
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            query_lower = query.lower().strip()
            
            cursor.execute("""
            SELECT steam_appid, name, main_genre, sub_genre, sub_sub_genre
            FROM games 
            WHERE LOWER(name) = ?
            LIMIT 1
            """, (query_lower,))
            
            exact_match = cursor.fetchone()
            if exact_match:
                result = dict(exact_match)
                result['similarity'] = 1.0
                result['match_type'] = 'exact'
                return [result]
            
            search_query = """
            SELECT steam_appid, name, main_genre, sub_genre, sub_sub_genre,
                   CASE 
                       WHEN LOWER(name) LIKE LOWER(? || '%') THEN 0.9
                       WHEN LOWER(name) LIKE LOWER('%' || ? || '%') THEN 0.7
                       ELSE 0.5
                   END as similarity_score
            FROM games 
            WHERE LOWER(name) LIKE LOWER('%' || ? || '%')
            ORDER BY similarity_score DESC, name
            LIMIT ?
            """
            
            cursor.execute(search_query, [query_lower] * 3 + [limit])
            matches = cursor.fetchall()
            
            if matches:
                results = []
                for match in matches:
                    result = dict(match)
                    result['similarity'] = match['similarity_score']
                    result['match_type'] = 'fuzzy'
                    results.append(result)
                return results
            
            return []
    
    def get_game_details(self, steam_appid: int) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM games WHERE steam_appid = ?", (steam_appid,))
            game = cursor.fetchone()
            if not game:
                return None
            
            game_dict = dict(game)
            
            cursor.execute("""
            SELECT tag FROM steam_tags WHERE steam_appid = ? ORDER BY tag_order
            """, (steam_appid,))
            game_dict['steam_tags'] = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("""
            SELECT tag FROM unique_tags WHERE steam_appid = ? ORDER BY tag_order
            """, (steam_appid,))
            game_dict['unique_tags'] = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("""
            SELECT tag FROM subjective_tags WHERE steam_appid = ? ORDER BY tag_order
            """, (steam_appid,))
            game_dict['subjective_tags'] = [row[0] for row in cursor.fetchall()]
            
            cursor.execute("""
            SELECT tag, ratio FROM tag_ratios WHERE steam_appid = ?
            """, (steam_appid,))
            game_dict['tag_ratios'] = {row[0]: row[1] for row in cursor.fetchall()}
            
            return game_dict
    
    def get_game_vector(self, steam_appid: int) -> Optional[bytes]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT vector_data FROM game_vectors WHERE steam_appid = ?", (steam_appid,))
            result = cursor.fetchone()
            return result[0] if result else None
    
    def get_game_tags(self, steam_appid: int) -> Tuple[set, set]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
            SELECT tag FROM unique_tags WHERE steam_appid = ?
            UNION
            SELECT tag FROM subjective_tags WHERE steam_appid = ?
            """, (steam_appid, steam_appid))
            
            tags = set(row[0] for row in cursor.fetchall())
            return tags, set()
    
    def get_hierarchy_candidates(self, target_appid: int, main_genre: str, 
                                sub_genre: str, sub_sub_genre: str, 
                                is_soulslike: bool = False) -> List[Tuple[int, str, float]]:
        candidates = []
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if is_soulslike:
                cursor.execute("""
                SELECT DISTINCT g.steam_appid, 'soulslike' as match_type, 0.5 as hierarchy_bonus
                FROM games g
                LEFT JOIN unique_tags ut ON g.steam_appid = ut.steam_appid
                WHERE g.steam_appid != ? AND (
                    LOWER(g.name) LIKE '%souls%' OR
                    LOWER(g.sub_sub_genre) LIKE '%souls%' OR
                    LOWER(ut.tag) LIKE '%souls%' OR
                    LOWER(ut.tag) LIKE '%soulslike%'
                )
                LIMIT 20
                """, (target_appid,))
                
                candidates.extend([(row[0], row[1], row[2]) for row in cursor.fetchall()])
            
            cursor.execute("""
            SELECT steam_appid, 'exact' as match_type, 0.4 as hierarchy_bonus
            FROM games 
            WHERE steam_appid != ? AND main_genre = ? AND sub_genre = ? AND sub_sub_genre = ?
            LIMIT 15
            """, (target_appid, main_genre, sub_genre, sub_sub_genre))
            
            candidates.extend([(row[0], row[1], row[2]) for row in cursor.fetchall() 
                              if row[0] not in [c[0] for c in candidates]])
            
            cursor.execute("""
            SELECT steam_appid, 'sub' as match_type, 0.25 as hierarchy_bonus
            FROM games 
            WHERE steam_appid != ? AND main_genre = ? AND sub_genre = ? AND sub_sub_genre != ?
            LIMIT 15
            """, (target_appid, main_genre, sub_genre, sub_sub_genre))
            
            candidates.extend([(row[0], row[1], row[2]) for row in cursor.fetchall() 
                              if row[0] not in [c[0] for c in candidates]])
            
            cursor.execute("""
            SELECT steam_appid, 'main' as match_type, 0.15 as hierarchy_bonus
            FROM games 
            WHERE steam_appid != ? AND main_genre = ? AND sub_genre != ?
            LIMIT 10
            """, (target_appid, main_genre, sub_genre))
            
            candidates.extend([(row[0], row[1], row[2]) for row in cursor.fetchall() 
                              if row[0] not in [c[0] for c in candidates]])
        
        return candidates[:50]
    
    def is_soulslike_game(self, steam_appid: int) -> bool:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("SELECT name FROM games WHERE steam_appid = ?", (steam_appid,))
            name = cursor.fetchone()
            if name and any(indicator in name[0].lower() for indicator in ['souls', 'elden ring', 'bloodborne']):
                return True
            
            cursor.execute("""
            SELECT COUNT(*) FROM unique_tags 
            WHERE steam_appid = ? AND (
                LOWER(tag) LIKE '%souls%' OR 
                LOWER(tag) LIKE '%soulslike%' OR 
                LOWER(tag) LIKE '%stamina%' OR
                LOWER(tag) LIKE '%challenging-but-fair%'
            )
            """, (steam_appid,))
            
            if cursor.fetchone()[0] > 0:
                return True
            
            cursor.execute("""
            SELECT sub_sub_genre FROM games 
            WHERE steam_appid = ? AND LOWER(sub_sub_genre) LIKE '%souls%'
            """, (steam_appid,))
            
            return cursor.fetchone() is not None
    
    def get_matching_tags_count(self, steam_appid: int, preferred_tags: List[str]) -> int:
        if not preferred_tags:
            return 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in preferred_tags])
            cursor.execute(f"""
            SELECT COUNT(*) FROM (
                SELECT tag FROM unique_tags WHERE steam_appid = ? AND tag IN ({placeholders})
                UNION
                SELECT tag FROM subjective_tags WHERE steam_appid = ? AND tag IN ({placeholders})
            )
            """, [steam_appid] + preferred_tags + [steam_appid] + preferred_tags)
            
            return cursor.fetchone()[0]
    
    def get_matching_steam_tags_count(self, steam_appid: int, preferred_steam_tags: List[str]) -> int:
        if not preferred_steam_tags:
            return 0
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            placeholders = ','.join(['?' for _ in preferred_steam_tags])
            cursor.execute(f"""
            SELECT COUNT(*) FROM steam_tags 
            WHERE steam_appid = ? AND tag IN ({placeholders})
            """, [steam_appid] + preferred_steam_tags)
            
            return cursor.fetchone()[0]
    
    def get_game_aesthetics(self, steam_appid: int) -> Optional[Dict[str, str]]:
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT art_style, theme, music_style FROM games WHERE steam_appid = ?
            """, (steam_appid,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'art_style': result['art_style'],
                    'theme': result['theme'],
                    'music_style': result['music_style']
                }
            return None
    
    def get_database_stats(self) -> Dict[str, Any]:
        if not self.exists():
            return {}
        
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT COUNT(*) FROM games")
                total_games = cursor.fetchone()[0]
                
                cursor.execute("""
                SELECT main_genre, sub_genre, sub_sub_genre, COUNT(*) as count
                FROM games 
                GROUP BY main_genre, sub_genre, sub_sub_genre
                ORDER BY count DESC
                LIMIT 20
                """)
                top_hierarchies = cursor.fetchall()
                
                cursor.execute("""
                SELECT tag, COUNT(*) as count
                FROM unique_tags
                GROUP BY tag
                ORDER BY count DESC
                LIMIT 20
                """)
                popular_tags = cursor.fetchall()
                
                return {
                    'total_games': total_games,
                    'top_hierarchies': top_hierarchies,
                    'popular_unique_tags': popular_tags
                }
        except Exception:
            return {}


class SteamApiRepository(DatabaseRepository):
    def get_steam_data(self, steam_appid: int) -> Optional[Dict[str, Any]]:
        if not self.exists():
            return None
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT a.header_image, a.pricing, a.steam_url,
                   s.positive_reviews, s.negative_reviews
            FROM steam_api a
            LEFT JOIN steam_spy s ON a.steam_appid = s.steam_appid
            WHERE a.steam_appid = ?
            """, (steam_appid,))
            
            result = cursor.fetchone()
            if result:
                return {
                    'header_image': result['header_image'],
                    'pricing': result['pricing'],
                    'steam_url': result['steam_url'],
                    'positive_reviews': result['positive_reviews'] or 0,
                    'negative_reviews': result['negative_reviews'] or 0
                }
            return None