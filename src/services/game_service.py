import pickle
import os
from typing import List, Dict, Any, Optional
from ..data.repositories import RecommendationsRepository, SteamApiRepository
from ..algorithms.similarity import HybridSimilarityCalculator
from ..utils.logging import get_logger

logger = get_logger(__name__)


class GameService:
    def __init__(self, recommendations_repo: RecommendationsRepository,
                 steam_api_repo: SteamApiRepository, vectorizer_path: str):
        self.recommendations_repo = recommendations_repo
        self.steam_api_repo = steam_api_repo
        self.vectorizer_path = vectorizer_path
        self.vectorizer = None
        self.similarity_calculator = HybridSimilarityCalculator(recommendations_repo)
        self._load_vectorizer()
    
    def _load_vectorizer(self):
        try:
            with open(self.vectorizer_path, 'rb') as f:
                self.vectorizer = pickle.load(f)
            logger.info("✅ Loaded TF-IDF vectorizer")
        except FileNotFoundError:
            logger.warning("Vectorizer not found. Vector-based similarity will not be available.")
            self.vectorizer = None
    
    def find_games_by_name(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        if not query or len(query.strip()) < 2:
            return []
        
        matches = self.recommendations_repo.find_games_by_name(query, limit)
        return self._enhance_games_with_steam_data(matches)
    
    def get_game_details(self, steam_appid: int) -> Optional[Dict[str, Any]]:
        game_details = self.recommendations_repo.get_game_details(steam_appid)
        if not game_details:
            return None
        
        enhanced_games = self._enhance_games_with_steam_data([game_details])
        return enhanced_games[0] if enhanced_games else None
    
    def get_available_preferences(self, steam_appid: int) -> Dict[str, Any]:
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
            'steam_tags': game.get('steam_tags', []),
            'tag_ratios': game.get('tag_ratios', {})
        }
    
    def find_similar_games(self, target_appid: int, 
                          user_preferences: Optional[Dict[str, Any]] = None, 
                          limit: int = 10) -> List[Dict[str, Any]]:
        try:
            target_game = self.recommendations_repo.get_game_details(target_appid)
            if not target_game:
                logger.error(f"Target game {target_appid} not found")
                return []
            
            main_genre = target_game['main_genre']
            sub_genre = target_game['sub_genre']
            sub_sub_genre = target_game['sub_sub_genre']
            
            logger.info(f"Finding games similar to: {target_game['name']}")
            logger.info(f"Hierarchy: {main_genre} → {sub_genre} → {sub_sub_genre}")
            
            is_soulslike = self.recommendations_repo.is_soulslike_game(target_appid)
            if is_soulslike:
                logger.info("Detected soulslike game - prioritizing soulslike mechanics")
            
            candidates = self.recommendations_repo.get_hierarchy_candidates(
                target_appid, main_genre, sub_genre, sub_sub_genre, is_soulslike
            )
            
            if not candidates:
                logger.warning("No candidates found")
                return []
            
            similarities = self.similarity_calculator.calculate_similarities(
                target_appid, candidates, user_preferences
            )
            
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
            logger.error(f"Error finding similar games: {e}")
            return []
    
    def _enhance_games_with_steam_data(self, games: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for game in games:
            steam_data = self.steam_api_repo.get_steam_data(game['steam_appid'])
            
            if steam_data:
                game.update({
                    'header_image': steam_data['header_image'] or '/static/logo.png',
                    'pricing': steam_data['pricing'] or 'Unknown',
                    'steam_url': steam_data['steam_url'] or f"https://store.steampowered.com/app/{game['steam_appid']}/",
                    'positive_reviews': steam_data['positive_reviews'],
                    'negative_reviews': steam_data['negative_reviews']
                })
            else:
                game.update({
                    'header_image': '/static/logo.png',
                    'pricing': 'Unknown',
                    'steam_url': f"https://store.steampowered.com/app/{game['steam_appid']}/",
                    'positive_reviews': 0,
                    'negative_reviews': 0
                })
        
        return games
    
    def get_database_stats(self) -> Dict[str, Any]:
        return self.recommendations_repo.get_database_stats()