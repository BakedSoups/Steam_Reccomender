import json
import math
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
import re

class GameSimilaritySearcher:
    def __init__(self, context_file: str = "context.json", results_file: str = "steam_games_large_scale_tags.json"):
        self.context_file = context_file
        self.results_file = results_file
        self.context = self.load_context()
        self.results = self.load_results()
        
    def load_context(self) -> Dict:
        """Load the contextual database"""
        try:
            with open(self.context_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Context file {self.context_file} not found!")
            return {"games": {}, "genres": {}, "tags": {}, "series": {}}
    
    def load_results(self) -> Dict:
        """Load the main results database"""
        try:
            with open(self.results_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Results file {self.results_file} not found!")
            return {}
    
    def find_game(self, game_name: str) -> Optional[Dict]:
        """Find a game by name (fuzzy matching)"""
        game_name_lower = game_name.lower()
        
        # Direct match in context
        if game_name in self.context["games"]:
            return self._get_full_game_data(game_name)
        
        # Fuzzy match in context
        for ctx_game in self.context["games"].keys():
            if game_name_lower in ctx_game.lower() or ctx_game.lower() in game_name_lower:
                return self._get_full_game_data(ctx_game)
        
        # Fuzzy match in results
        for app_id, game_data in self.results.items():
            game_title = game_data.get("name", "").lower()
            if game_name_lower in game_title or game_title in game_name_lower:
                return game_data
        
        return None
    
    def _get_full_game_data(self, game_name: str) -> Dict:
        """Get complete game data from both context and results"""
        ctx_data = self.context["games"].get(game_name, {})
        
        # Find in results by appid
        appid = ctx_data.get("steam_appid")
        if appid:
            for app_id, game_data in self.results.items():
                if game_data.get("steam_appid") == appid:
                    return game_data
        
        # Fallback to context data
        return {
            "name": game_name,
            "main_genre": ctx_data.get("main_genre", "unknown"),
            "unique_tags": ctx_data.get("unique_tags", []),
            "subjective_tags": ctx_data.get("subjective_tags", []),
            "tag_ratios": ctx_data.get("tag_ratios", {}),
            "steam_appid": ctx_data.get("steam_appid")
        }
    
    def find_similar_games(self, target_game_name: str, 
                          similarity_types: List[str] = ["genre", "mechanics", "experience", "series"],
                          limit: int = 20) -> Dict[str, List[Dict]]:
        """
        Find similar games using multiple similarity algorithms
        
        similarity_types:
        - "genre": Same genre + similar mechanics
        - "mechanics": Similar gameplay ratios regardless of genre  
        - "experience": Similar player experience (subjective tags)
        - "series": Games in same series/franchise
        - "hybrid": Weighted combination of all factors
        """
        
        target_game = self.find_game(target_game_name)
        if not target_game:
            return {"error": [f"Game '{target_game_name}' not found"]}
        
        print(f"🎮 Finding games similar to: {target_game.get('name', target_game_name)}")
        print(f"📊 Target genre: {target_game.get('main_genre', 'unknown')}")
        print(f"🏷️  Target tags: {', '.join(target_game.get('unique_tags', [])[:5])}")
        print(f"⚡ Target ratios: {', '.join([f'{k}:{v}%' for k,v in list(target_game.get('tag_ratios', {}).items())[:4]])}")
        
        results = {}
        
        if "genre" in similarity_types:
            results["genre_similar"] = self._find_genre_similar(target_game, limit)
        
        if "mechanics" in similarity_types:
            results["mechanics_similar"] = self._find_mechanics_similar(target_game, limit)
        
        if "experience" in similarity_types:
            results["experience_similar"] = self._find_experience_similar(target_game, limit)
        
        if "series" in similarity_types:
            results["series_similar"] = self._find_series_similar(target_game, limit)
        
        if "hybrid" in similarity_types:
            results["hybrid_similar"] = self._find_hybrid_similar(target_game, limit)
        
        return results
    
    def _find_genre_similar(self, target_game: Dict, limit: int) -> List[Dict]:
        """Find games with same genre and similar unique tags"""
        target_genre = target_game.get("main_genre", "unknown")
        target_unique = set(target_game.get("unique_tags", []))
        
        if target_genre == "unknown" or target_genre not in self.context["genres"]:
            return []
        
        similar_games = []
        genre_data = self.context["genres"][target_genre]
        
        # Check all games in the same genre
        for game_name in genre_data.get("examples", []):
            if game_name.lower() == target_game.get("name", "").lower():
                continue
                
            game_data = self._get_full_game_data(game_name)
            game_unique = set(game_data.get("unique_tags", []))
            
            # Calculate tag overlap
            if len(target_unique | game_unique) > 0:
                tag_similarity = len(target_unique & game_unique) / len(target_unique | game_unique)
                
                similar_games.append({
                    "name": game_data.get("name", game_name),
                    "similarity_score": tag_similarity,
                    "match_reason": f"Same genre ({target_genre}), {len(target_unique & game_unique)} shared tags",
                    "shared_tags": list(target_unique & game_unique),
                    "unique_tags": game_data.get("unique_tags", []),
                    "subjective_tags": game_data.get("subjective_tags", []),
                    "steam_appid": game_data.get("steam_appid"),
                    "tag_ratios": game_data.get("tag_ratios", {})
                })
        
        return sorted(similar_games, key=lambda x: x["similarity_score"], reverse=True)[:limit]
    
    def _find_mechanics_similar(self, target_game: Dict, limit: int) -> List[Dict]:
        """Find games with similar gameplay ratios (cross-genre)"""
        target_ratios = target_game.get("tag_ratios", {})
        if not target_ratios:
            return []
        
        similar_games = []
        
        # Check all games in context
        for game_name, game_data in self.context["games"].items():
            if game_name.lower() == target_game.get("name", "").lower():
                continue
            
            game_ratios = game_data.get("tag_ratios", {})
            if not game_ratios:
                continue
            
            # Calculate ratio similarity using cosine similarity
            similarity = self._calculate_ratio_similarity(target_ratios, game_ratios)
            
            if similarity > 0.3:  # Minimum threshold
                full_game_data = self._get_full_game_data(game_name)
                
                similar_games.append({
                    "name": game_name,
                    "similarity_score": similarity,
                    "match_reason": f"Similar gameplay ratios (cross-genre match)",
                    "target_ratios": target_ratios,
                    "game_ratios": game_ratios,
                    "main_genre": game_data.get("main_genre", "unknown"),
                    "unique_tags": full_game_data.get("unique_tags", []),
                    "subjective_tags": full_game_data.get("subjective_tags", []),
                    "steam_appid": game_data.get("steam_appid")
                })
        
        return sorted(similar_games, key=lambda x: x["similarity_score"], reverse=True)[:limit]
    
    def _find_experience_similar(self, target_game: Dict, limit: int) -> List[Dict]:
        """Find games with similar player experience (subjective tags)"""
        target_subjective = set(target_game.get("subjective_tags", []))
        if not target_subjective:
            return []
        
        similar_games = []
        
        # Check all games in context
        for game_name, game_data in self.context["games"].items():
            if game_name.lower() == target_game.get("name", "").lower():
                continue
            
            game_subjective = set(game_data.get("subjective_tags", []))
            if not game_subjective:
                continue
            
            # Calculate subjective tag overlap
            if len(target_subjective | game_subjective) > 0:
                experience_similarity = len(target_subjective & game_subjective) / len(target_subjective | game_subjective)
                
                if experience_similarity > 0.2:  # Minimum threshold
                    full_game_data = self._get_full_game_data(game_name)
                    
                    similar_games.append({
                        "name": game_name,
                        "similarity_score": experience_similarity,
                        "match_reason": f"Similar player experience, {len(target_subjective & game_subjective)} shared qualities",
                        "shared_experience": list(target_subjective & game_subjective),
                        "main_genre": game_data.get("main_genre", "unknown"),
                        "unique_tags": full_game_data.get("unique_tags", []),
                        "subjective_tags": game_data.get("subjective_tags", []),
                        "steam_appid": game_data.get("steam_appid")
                    })
        
        return sorted(similar_games, key=lambda x: x["similarity_score"], reverse=True)[:limit]
    
    def _find_series_similar(self, target_game: Dict, limit: int) -> List[Dict]:
        """Find games in the same series/franchise"""
        target_name = target_game.get("name", "")
        
        # Find which series this game belongs to
        target_series = None
        for series_key, series_games in self.context.get("series", {}).items():
            if target_name in series_games:
                target_series = series_key
                break
        
        if not target_series:
            return []
        
        similar_games = []
        series_games = self.context["series"][target_series]
        
        for game_name in series_games:
            if game_name.lower() == target_name.lower():
                continue
            
            game_data = self._get_full_game_data(game_name)
            
            similar_games.append({
                "name": game_name,
                "similarity_score": 0.95,  # High similarity for series matches
                "match_reason": f"Same series: {target_series}",
                "series": target_series,
                "main_genre": game_data.get("main_genre", "unknown"),
                "unique_tags": game_data.get("unique_tags", []),
                "subjective_tags": game_data.get("subjective_tags", []),
                "steam_appid": game_data.get("steam_appid"),
                "tag_ratios": game_data.get("tag_ratios", {})
            })
        
        return similar_games[:limit]
    
    def _find_hybrid_similar(self, target_game: Dict, limit: int) -> List[Dict]:
        """Find similar games using weighted combination of all factors"""
        target_genre = target_game.get("main_genre", "unknown")
        target_unique = set(target_game.get("unique_tags", []))
        target_subjective = set(target_game.get("subjective_tags", []))
        target_ratios = target_game.get("tag_ratios", {})
        
        similar_games = []
        
        # Check all games in context
        for game_name, game_data in self.context["games"].items():
            if game_name.lower() == target_game.get("name", "").lower():
                continue
            
            # Calculate individual similarity components
            genre_score = 1.0 if game_data.get("main_genre") == target_genre else 0.2
            
            # Tag similarity
            game_unique = set(game_data.get("unique_tags", []))
            unique_score = 0
            if len(target_unique | game_unique) > 0:
                unique_score = len(target_unique & game_unique) / len(target_unique | game_unique)
            
            # Experience similarity
            game_subjective = set(game_data.get("subjective_tags", []))
            subjective_score = 0
            if len(target_subjective | game_subjective) > 0:
                subjective_score = len(target_subjective & game_subjective) / len(target_subjective | game_subjective)
            
            # Ratio similarity
            game_ratios = game_data.get("tag_ratios", {})
            ratio_score = 0
            if target_ratios and game_ratios:
                ratio_score = self._calculate_ratio_similarity(target_ratios, game_ratios)
            
            # Series bonus
            series_bonus = self._check_series_bonus(target_game.get("name", ""), game_name)
            
            # Weighted hybrid score
            hybrid_score = (
                genre_score * 0.25 +
                unique_score * 0.30 +
                subjective_score * 0.20 +
                ratio_score * 0.20 +
                series_bonus * 0.05
            )
            
            if hybrid_score > 0.3:  # Minimum threshold
                full_game_data = self._get_full_game_data(game_name)
                
                similar_games.append({
                    "name": game_name,
                    "similarity_score": hybrid_score,
                    "match_reason": f"Hybrid match (G:{genre_score:.2f} U:{unique_score:.2f} E:{subjective_score:.2f} R:{ratio_score:.2f})",
                    "genre_score": genre_score,
                    "unique_score": unique_score,
                    "experience_score": subjective_score,
                    "ratio_score": ratio_score,
                    "main_genre": game_data.get("main_genre", "unknown"),
                    "unique_tags": full_game_data.get("unique_tags", []),
                    "subjective_tags": full_game_data.get("subjective_tags", []),
                    "steam_appid": game_data.get("steam_appid"),
                    "tag_ratios": game_data.get("tag_ratios", {})
                })
        
        return sorted(similar_games, key=lambda x: x["similarity_score"], reverse=True)[:limit]
    
    def _calculate_ratio_similarity(self, ratios1: Dict, ratios2: Dict) -> float:
        """Calculate cosine similarity between two ratio dictionaries"""
        if not ratios1 or not ratios2:
            return 0.0
        
        # Get all unique keys
        all_keys = set(ratios1.keys()) | set(ratios2.keys())
        
        # Create vectors
        vec1 = [ratios1.get(key, 0) for key in all_keys]
        vec2 = [ratios2.get(key, 0) for key in all_keys]
        
        # Calculate cosine similarity
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = math.sqrt(sum(a * a for a in vec1))
        magnitude2 = math.sqrt(sum(b * b for b in vec2))
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def _check_series_bonus(self, target_name: str, game_name: str) -> float:
        """Check if games are in the same series"""
        for series_games in self.context.get("series", {}).values():
            if target_name in series_games and game_name in series_games:
                return 1.0
        return 0.0
    
    def search_and_display(self, game_name: str, max_results: int = 10):
        """Search for similar games and display results in a nice format"""
        results = self.find_similar_games(game_name, 
                                        similarity_types=["hybrid", "genre", "mechanics", "series"],
                                        limit=max_results)
        
        if "error" in results:
            print(f"❌ {results['error'][0]}")
            return
        
        print(f"\n{'='*80}")
        print(f"🎮 GAMES SIMILAR TO: {game_name.upper()}")
        print(f"{'='*80}")
        
        # Display each similarity type
        for similarity_type, games in results.items():
            if not games:
                continue
                
            print(f"\n🔍 {similarity_type.upper().replace('_', ' ')} MATCHES:")
            print("-" * 50)
            
            for i, game in enumerate(games[:max_results], 1):
                print(f"{i:2d}. {game['name']}")
                print(f"    📊 Genre: {game.get('main_genre', 'unknown')}")
                print(f"    🏷️  Tags: {', '.join(game.get('unique_tags', [])[:4])}")
                print(f"    ⭐ Quality: {', '.join(game.get('subjective_tags', [])[:3])}")
                print(f"    🎯 Score: {game['similarity_score']:.3f}")
                print(f"    💡 Reason: {game['match_reason']}")
                if game.get('steam_appid'):
                    print(f"    🔗 Steam: https://store.steampowered.com/app/{game['steam_appid']}")
                print()

# Convenience functions for easy searching
def search_similar_games(game_name: str, max_results: int = 10):
    """Quick search function"""
    searcher = GameSimilaritySearcher()
    searcher.search_and_display(game_name, max_results)

def find_by_genre(genre: str, limit: int = 15):
    """Find games by genre"""
    searcher = GameSimilaritySearcher()
    
    if genre not in searcher.context["genres"]:
        print(f"❌ Genre '{genre}' not found")
        available = list(searcher.context["genres"].keys())[:20]
        print(f"Available genres: {', '.join(available)}")
        return
    
    genre_data = searcher.context["genres"][genre]
    print(f"\n🎮 {genre.upper()} GAMES ({genre_data['count']} total):")
    print("-" * 50)
    
    for i, game_name in enumerate(genre_data["examples"][:limit], 1):
        game_data = searcher._get_full_game_data(game_name)
        print(f"{i:2d}. {game_name}")
        print(f"    🏷️  Tags: {', '.join(game_data.get('unique_tags', [])[:4])}")
        print(f"    ⭐ Quality: {', '.join(game_data.get('subjective_tags', [])[:3])}")
        if game_data.get('steam_appid'):
            print(f"    🔗 Steam: https://store.steampowered.com/app/{game_data['steam_appid']}")
        print()

def find_by_tags(required_tags: List[str], exclude_tags: List[str] = None, limit: int = 15):
    """Find games that have specific tags"""
    searcher = GameSimilaritySearcher()
    exclude_tags = exclude_tags or []
    
    matching_games = []
    
    for game_name, game_data in searcher.context["games"].items():
        all_tags = set(game_data.get("unique_tags", []) + game_data.get("subjective_tags", []))
        all_tags_lower = {tag.lower() for tag in all_tags}
        
        # Check required tags
        required_match = all(req_tag.lower() in all_tags_lower for req_tag in required_tags)
        
        # Check excluded tags
        excluded_match = any(exc_tag.lower() in all_tags_lower for exc_tag in exclude_tags)
        
        if required_match and not excluded_match:
            full_data = searcher._get_full_game_data(game_name)
            matching_games.append({
                "name": game_name,
                "genre": game_data.get("main_genre", "unknown"),
                "unique_tags": full_data.get("unique_tags", []),
                "subjective_tags": full_data.get("subjective_tags", []),
                "steam_appid": game_data.get("steam_appid")
            })
    
    print(f"\n🎮 GAMES WITH TAGS: {', '.join(required_tags)}")
    if exclude_tags:
        print(f"🚫 EXCLUDING: {', '.join(exclude_tags)}")
    print(f"Found {len(matching_games)} matches:")
    print("-" * 50)
    
    for i, game in enumerate(matching_games[:limit], 1):
        print(f"{i:2d}. {game['name']} ({game['genre']})")
        print(f"    🏷️  Tags: {', '.join(game['unique_tags'][:4])}")
        print(f"    ⭐ Quality: {', '.join(game['subjective_tags'][:3])}")
        if game.get('steam_appid'):
            print(f"    🔗 Steam: https://store.steampowered.com/app/{game['steam_appid']}")
        print()

# Example usage
if __name__ == "__main__":
    # Example searches
    print("🔍 EXAMPLE SEARCHES:")
    print("=" * 50)
    
    # Search for games similar to Dark Souls 3
    search_similar_games("call of duty", max_results=8)
    
    # Find all souls-like games
    find_by_genre("souls-like", limit=10)
    
    # Find challenging single-player games
    find_by_tags(["challenging", "single-player"], exclude_tags=["multiplayer-focused"], limit=10)