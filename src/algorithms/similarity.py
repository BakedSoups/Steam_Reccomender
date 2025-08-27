import numpy as np
from typing import List, Dict, Any, Optional
from sklearn.metrics.pairwise import cosine_similarity
from abc import ABC, abstractmethod


class SimilarityCalculator(ABC):
    @abstractmethod
    def calculate_similarity(self, target_appid: int, candidate_appid: int, 
                           hierarchy_bonus: float = 0) -> float:
        pass


class VectorSimilarityCalculator(SimilarityCalculator):
    def __init__(self, recommendations_repo):
        self.recommendations_repo = recommendations_repo
    
    def calculate_similarity(self, target_appid: int, candidate_appid: int, 
                           hierarchy_bonus: float = 0) -> Optional[float]:
        target_vector_data = self.recommendations_repo.get_game_vector(target_appid)
        candidate_vector_data = self.recommendations_repo.get_game_vector(candidate_appid)
        
        if not target_vector_data or not candidate_vector_data:
            return None
        
        target_vector = np.frombuffer(target_vector_data, dtype=np.float64).reshape(1, -1)
        candidate_vector = np.frombuffer(candidate_vector_data, dtype=np.float64).reshape(1, -1)
        
        base_similarity = cosine_similarity(target_vector, candidate_vector)[0][0]
        return base_similarity


class TagBasedSimilarityCalculator(SimilarityCalculator):
    def __init__(self, recommendations_repo):
        self.recommendations_repo = recommendations_repo
    
    def calculate_similarity(self, target_appid: int, candidate_appid: int, 
                           hierarchy_bonus: float = 0) -> float:
        target_tags, _ = self.recommendations_repo.get_game_tags(target_appid)
        candidate_tags, _ = self.recommendations_repo.get_game_tags(candidate_appid)
        
        if len(target_tags) > 0 and len(candidate_tags) > 0:
            intersection = len(target_tags & candidate_tags)
            union = len(target_tags | candidate_tags)
            jaccard_similarity = intersection / union if union > 0 else 0
        else:
            jaccard_similarity = 0
        
        return jaccard_similarity


class PreferenceCalculator:
    def __init__(self, recommendations_repo):
        self.recommendations_repo = recommendations_repo
    
    def calculate_preference_bonus(self, candidate_appid: int, 
                                 user_preferences: Optional[Dict[str, Any]]) -> float:
        if not user_preferences:
            return 0
        
        bonus = 0
        
        bonus += self._calculate_aesthetic_bonus(candidate_appid, user_preferences)
        bonus += self._calculate_tag_bonus(candidate_appid, user_preferences)
        bonus += self._calculate_steam_tag_bonus(candidate_appid, user_preferences)
        
        return bonus
    
    def _calculate_aesthetic_bonus(self, candidate_appid: int, 
                                 user_preferences: Dict[str, Any]) -> float:
        aesthetics = user_preferences.get('aesthetics', {})
        if not aesthetics:
            return 0
        
        game_aesthetics = self.recommendations_repo.get_game_aesthetics(candidate_appid)
        if not game_aesthetics:
            return 0
        
        bonus = 0
        for pref_type, pref_value in aesthetics.items():
            if pref_value and game_aesthetics.get(pref_type) == pref_value:
                bonus += 0.1
        
        return bonus
    
    def _calculate_tag_bonus(self, candidate_appid: int, 
                           user_preferences: Dict[str, Any]) -> float:
        preferred_tags = user_preferences.get('preferred_tags', [])
        if not preferred_tags:
            return 0
        
        matching_count = self.recommendations_repo.get_matching_tags_count(
            candidate_appid, preferred_tags
        )
        
        if matching_count > 0:
            return (matching_count / len(preferred_tags)) * 0.15
        
        return 0
    
    def _calculate_steam_tag_bonus(self, candidate_appid: int, 
                                 user_preferences: Dict[str, Any]) -> float:
        preferred_steam_tags = user_preferences.get('preferred_steam_tags', [])
        if not preferred_steam_tags:
            return 0
        
        matching_steam_tags = self.recommendations_repo.get_matching_steam_tags_count(
            candidate_appid, preferred_steam_tags
        )
        
        if matching_steam_tags == 0:
            return 0
        
        steam_tag_bonus = (matching_steam_tags / len(preferred_steam_tags)) * 0.25
        combo_bonus = self._calculate_combo_bonus(candidate_appid, preferred_steam_tags)
        
        return steam_tag_bonus + combo_bonus
    
    def _calculate_combo_bonus(self, candidate_appid: int, 
                             preferred_steam_tags: List[str]) -> float:
        popular_combos = {
            ('roguelike', 'procedural generation'): 0.1,
            ('souls-like', 'difficult'): 0.1,
            ('metroidvania', 'exploration'): 0.1,
            ('platformer', 'pixel graphics'): 0.05,
            ('puzzle', 'relaxing'): 0.05
        }
        
        selected_tags_lower = [tag.lower() for tag in preferred_steam_tags]
        bonus = 0
        
        for combo, combo_bonus in popular_combos.items():
            if all(tag in selected_tags_lower for tag in combo):
                candidate_matching = self.recommendations_repo.get_matching_steam_tags_count(
                    candidate_appid, list(combo)
                )
                if candidate_matching == len(combo):
                    bonus += combo_bonus
        
        return bonus


class HybridSimilarityCalculator:
    def __init__(self, recommendations_repo):
        self.recommendations_repo = recommendations_repo
        self.vector_calculator = VectorSimilarityCalculator(recommendations_repo)
        self.tag_calculator = TagBasedSimilarityCalculator(recommendations_repo)
        self.preference_calculator = PreferenceCalculator(recommendations_repo)
    
    def calculate_similarities(self, target_appid: int, 
                             candidates: List[tuple], 
                             user_preferences: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        similarities = []
        
        for candidate_appid, match_type, hierarchy_bonus in candidates:
            base_similarity = self.vector_calculator.calculate_similarity(
                target_appid, candidate_appid, hierarchy_bonus
            )
            
            if base_similarity is None:
                base_similarity = self.tag_calculator.calculate_similarity(
                    target_appid, candidate_appid, hierarchy_bonus
                )
            
            preference_bonus = self.preference_calculator.calculate_preference_bonus(
                candidate_appid, user_preferences
            )
            
            final_score = min(1.0, base_similarity + hierarchy_bonus + preference_bonus)
            
            similarities.append({
                'steam_appid': candidate_appid,
                'similarity': final_score,
                'base_similarity': base_similarity,
                'hierarchy_bonus': hierarchy_bonus,
                'preference_bonus': preference_bonus,
                'match_type': match_type
            })
        
        similarities.sort(key=lambda x: x['similarity'], reverse=True)
        return similarities