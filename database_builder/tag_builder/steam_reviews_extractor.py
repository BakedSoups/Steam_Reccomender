import requests
import sqlite3
import json
import os
import time
import re
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from openai import OpenAI
from typing import Dict, List, Set, Tuple, Optional
import difflib
from collections import defaultdict

analyzer = SentimentIntensityAnalyzer()
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Context system for large-scale game database
CONTEXT_DB = "context.json"
SIMILARITY_THRESHOLD = 0.7

GAMEPLAY_KEYWORDS = {
    "vibes", "soundtrack", "music", "overall", "the good", "pros", "cons",
    "mechanics", "controls", "gameplay", "combat", "movement", "pacing",
    "shooting", "platforming", "turn based", "real time", "puzzle", "exploration",
    "stealth", "driving", "flying", "building", "crafting", "level", "missions", 
    "quests", "campaign", "objectives", "checkpoints", "difficulty", "progression", 
    "grind", "boss", "miniboss", "enemy ai", "chill", "multiplayer", "co-op", 
    "singleplayer", "team", "ranked", "competitive", "pvp", "pve", "sandbox", 
    "open world", "inventory", "skills", "abilities", "tree", "upgrade", "loadout", 
    "gear", "weapons", "armor", "stats", "classes", "perks", "mods", "economy",
    "fps", "rpg", "roguelike", "deck builder", "platformer", "shooter", "metroidvania",
    "strategy", "simulation", "management", "builder", "survival", "horror"
}

TOXICITY_PHRASES = {
    "toxic", "grief", "flamed", "slur", "racism", "sexism", "trash community",
    "abandoned", "report system", "mute button", "valve doesn't care",
    "worst community", "matchmaking is broken", "smurfs", "trolls", "chain queuing"
}

class LargeScaleContextManager:
    def __init__(self, context_file: str = CONTEXT_DB):
        self.context_file = context_file
        self.context = self.load_context()
        self.batch_updates = []
        self.batch_size = 50  # Save context every 50 games
        
    def load_context(self) -> Dict:
        """Load context database optimized for large-scale operations"""
        try:
            with open(self.context_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"loaded context db: {len(data.get('games', {}))} games, {len(data.get('genres', {}))} genres")
                return data
        except FileNotFoundError:
            print("creating new large-scale context database...")
            return {
                "games": {},  # {game_name: game_data}
                "genres": {},  # {genre: {examples: [], patterns: {}, count: 0}}
                "tags": {     # Tag frequency and co-occurrence
                    "unique_tags": {},     # {tag: count}
                    "subjective_tags": {}, # {tag: count}
                    "ratio_tags": {}       # {tag: count}
                },
                "series": {},  # {series_key: [game_names]}
                "name_patterns": {},  # {pattern: [game_names]}
                "last_updated": datetime.now().isoformat(),
                "stats": {
                    "total_games": 0,
                    "total_genres": 0,
                    "most_common_genre": "",
                    "last_batch_save": datetime.now().isoformat()
                }
            }
    
    def save_context(self, force: bool = False):
        """Save context with batch optimization"""
        if not force and len(self.batch_updates) < self.batch_size:
            return
            
        # Process batch updates
        for update in self.batch_updates:
            self._apply_update(update)
        
        # Update stats
        self.context["stats"]["total_games"] = len(self.context["games"])
        self.context["stats"]["total_genres"] = len(self.context["genres"])
        self.context["stats"]["last_batch_save"] = datetime.now().isoformat()
        self.context["last_updated"] = datetime.now().isoformat()
        
        # Find most common genre
        if self.context["genres"]:
            most_common = max(self.context["genres"].items(), key=lambda x: x[1].get("count", 0))
            self.context["stats"]["most_common_genre"] = f"{most_common[0]} ({most_common[1]['count']} games)"
        
        with open(self.context_file, 'w', encoding='utf-8') as f:
            json.dump(self.context, f, ensure_ascii=False, indent=2)
        
        print(f"context saved: {len(self.context['games'])} games, batch size: {len(self.batch_updates)}")
        self.batch_updates = []
    
    def _apply_update(self, update: Dict):
        """Apply a single update to the context"""
        game_name = update["game_name"]
        game_data = update["game_data"]
        
        # Add game to context
        self.context["games"][game_name] = {
            "main_genre": game_data.get("main_genre", "unknown"),
            "unique_tags": game_data.get("unique_tags", []),
            "subjective_tags": game_data.get("subjective_tags", []),
            "tag_ratios": game_data.get("tag_ratios", {}),
            "steam_appid": game_data.get("steam_appid"),
            "review_keywords": self._extract_keywords_from_reviews(game_data.get("reviews", [])),
            "last_updated": datetime.now().isoformat()
        }
        
        # Update genre patterns
        genre = game_data.get("main_genre", "unknown")
        if genre not in self.context["genres"]:
            self.context["genres"][genre] = {
                "examples": [],
                "common_unique_tags": defaultdict(int),
                "common_ratio_tags": defaultdict(int),
                "common_subjective_tags": defaultdict(int),
                "count": 0
            }
        
        genre_data = self.context["genres"][genre]
        genre_data["count"] += 1
        
        # Add to examples (keep most recent 10)
        if game_name not in genre_data["examples"]:
            genre_data["examples"].append(game_name)
            if len(genre_data["examples"]) > 10:
                genre_data["examples"] = genre_data["examples"][-10:]
        
        # Update tag frequencies for this genre
        for tag in game_data.get("unique_tags", []):
            genre_data["common_unique_tags"][tag] += 1
            self.context["tags"]["unique_tags"][tag] = self.context["tags"]["unique_tags"].get(tag, 0) + 1
        
        for tag in game_data.get("subjective_tags", []):
            genre_data["common_subjective_tags"][tag] += 1
            self.context["tags"]["subjective_tags"][tag] = self.context["tags"]["subjective_tags"].get(tag, 0) + 1
        
        for tag in game_data.get("tag_ratios", {}).keys():
            genre_data["common_ratio_tags"][tag] += 1
            self.context["tags"]["ratio_tags"][tag] = self.context["tags"]["ratio_tags"].get(tag, 0) + 1
        
        # Update series tracking
        series_key = self._extract_series_key(game_name)
        if series_key:
            if series_key not in self.context["series"]:
                self.context["series"][series_key] = []
            if game_name not in self.context["series"][series_key]:
                self.context["series"][series_key].append(game_name)
    
    def _extract_keywords_from_reviews(self, reviews: List[Dict]) -> List[str]:
        """Extract meaningful keywords from reviews for similarity matching"""
        all_text = " ".join([r.get("review", "") for r in reviews])
        words = re.findall(r'\b\w{4,}\b', all_text.lower())  # Words 4+ chars
        
        # Filter to meaningful gaming keywords
        gaming_keywords = []
        for word in words:
            if word in GAMEPLAY_KEYWORDS or any(kw in word for kw in ["game", "play", "level", "boss", "quest"]):
                gaming_keywords.append(word)
        
        # Return top 20 most frequent
        from collections import Counter
        return [word for word, count in Counter(gaming_keywords).most_common(20)]
    
    def _extract_series_key(self, game_name: str) -> Optional[str]:
        """Extract series identifier from game name"""
        name_lower = game_name.lower()
        
        # Common series patterns
        patterns = [
            r'^(.+?)\s+\d+$',  # "Game Name 2"
            r'^(.+?)\s+(ii|iii|iv|v)$',  # "Game Name II"
            r'^(.+?)\s+(classic|remastered|definitive|enhanced)$',  # "Game Name Classic"
            r'^(.+?):\s+.+$',  # "Series: Subtitle"
        ]
        
        for pattern in patterns:
            match = re.match(pattern, name_lower)
            if match:
                return match.group(1).strip()
        
        return None
    
    def add_game(self, game_name: str, game_data: Dict):
        """Add game to context (batched)"""
        self.batch_updates.append({
            "game_name": game_name,
            "game_data": game_data
        })
        
        # Auto-save when batch is full
        if len(self.batch_updates) >= self.batch_size:
            self.save_context()
    
    def find_similar_games(self, game_name: str, reviews_text: str, limit: int = 5) -> List[Dict]:
        """Find similar games using efficient lookups"""
        similar_games = []
        
        # 1. Check for series matches first (highest priority)
        series_key = self._extract_series_key(game_name)
        if series_key and series_key in self.context["series"]:
            for series_game in self.context["series"][series_key]:
                if series_game.lower() != game_name.lower() and series_game in self.context["games"]:
                    similar_games.append({
                        "name": series_game,
                        "similarity": 0.95,  # Very high for series matches
                        "data": self.context["games"][series_game],
                        "match_type": "series"
                    })
        
        # 2. Look for direct game mentions in reviews
        mentioned_games = self._extract_game_mentions(reviews_text)
        for mentioned in mentioned_games:
            if mentioned in self.context["games"]:
                similar_games.append({
                    "name": mentioned,
                    "similarity": 0.9,
                    "data": self.context["games"][mentioned],
                    "match_type": "mentioned"
                })
        
        # 3. Keyword-based similarity (limit to top genres for efficiency)
        if len(similar_games) < limit:
            review_keywords = set(self._extract_keywords_from_reviews([{"review": reviews_text}]))
            
            # Only check top 5 most common genres to keep it fast
            top_genres = sorted(self.context["genres"].items(), 
                              key=lambda x: x[1].get("count", 0), reverse=True)[:5]
            
            for genre_name, genre_data in top_genres:
                if len(similar_games) >= limit:
                    break
                    
                for example_game in genre_data["examples"][-5:]:  # Check recent examples
                    if example_game in self.context["games"]:
                        game_data = self.context["games"][example_game]
                        game_keywords = set(game_data.get("review_keywords", []))
                        
                        if len(review_keywords | game_keywords) > 0:
                            similarity = len(review_keywords & game_keywords) / len(review_keywords | game_keywords)
                            
                            if similarity > SIMILARITY_THRESHOLD:
                                similar_games.append({
                                    "name": example_game,
                                    "similarity": similarity,
                                    "data": game_data,
                                    "match_type": "keyword"
                                })
        
        # Sort by similarity and return top matches
        similar_games.sort(key=lambda x: x["similarity"], reverse=True)
        return similar_games[:limit]
    
    def _extract_game_mentions(self, text: str) -> List[str]:
        """Extract game mentions from review text"""
        text_lower = text.lower()
        mentioned_games = []
        
        # Check against known games in context (efficient subset check)
        for game_name in self.context["games"].keys():
            if len(game_name) > 4 and game_name.lower() in text_lower:
                mentioned_games.append(game_name)
        
        return mentioned_games[:5]  # Limit to prevent noise
    
    def get_genre_context(self, potential_genre: str) -> Dict:
        """Get context for a specific genre"""
        if potential_genre not in self.context["genres"]:
            return {}
        
        genre_data = self.context["genres"][potential_genre]
        
        # Get most common tags for this genre
        common_unique = sorted(genre_data["common_unique_tags"].items(), 
                             key=lambda x: x[1], reverse=True)[:5]
        common_ratio = sorted(genre_data["common_ratio_tags"].items(), 
                            key=lambda x: x[1], reverse=True)[:5]
        common_subjective = sorted(genre_data["common_subjective_tags"].items(), 
                                 key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "count": genre_data["count"],
            "examples": genre_data["examples"][-3:],  # Recent examples
            "common_unique_tags": [tag for tag, count in common_unique],
            "common_ratio_tags": [tag for tag, count in common_ratio],
            "common_subjective_tags": [tag for tag, count in common_subjective]
        }
    
    def build_contextual_prompt(self, game_name: str, reviews_text: str) -> str:
        """Build efficient contextual prompt for large-scale database"""
        context_sections = []
        
        # 1. Similar games context
        similar_games = self.find_similar_games(game_name, reviews_text, limit=3)
        if similar_games:
            context_sections.append("SIMILAR GAMES FOUND:")
            for similar in similar_games:
                game_data = similar["data"]
                context_sections.append(f"• {similar['name']} ({similar['similarity']:.2f} {similar['match_type']}):")
                context_sections.append(f"  - Genre: {game_data.get('main_genre', 'unknown')}")
                context_sections.append(f"  - Unique tags: {', '.join(game_data.get('unique_tags', [])[:3])}")
                context_sections.append(f"  - Ratios: {', '.join([f'{k}:{v}%' for k,v in list(game_data.get('tag_ratios', {}).items())[:3]])}")
        
        # 2. Genre pattern context (identify likely genre)
        potential_genres = self._identify_potential_genres(reviews_text)
        if potential_genres:
            context_sections.append("\nGENRE PATTERNS:")
            for genre, confidence in potential_genres[:2]:
                genre_context = self.get_genre_context(genre)
                if genre_context:
                    context_sections.append(f"• {genre} ({confidence:.2f} confidence, {genre_context['count']} games):")
                    context_sections.append(f"  - Common unique tags: {', '.join(genre_context['common_unique_tags'])}")
                    context_sections.append(f"  - Common ratio tags: {', '.join(genre_context['common_ratio_tags'])}")
                    context_sections.append(f"  - Examples: {', '.join(genre_context['examples'])}")
        
        # 3. Series context
        series_key = self._extract_series_key(game_name)
        if series_key and series_key in self.context["series"]:
            series_games = self.context["series"][series_key]
            context_sections.append(f"\nSERIES CONTEXT:")
            context_sections.append(f"• Part of '{series_key}' series with: {', '.join(series_games[:3])}")
            
            # Show genre consistency in series
            series_genres = set()
            for series_game in series_games:
                if series_game in self.context["games"]:
                    series_genres.add(self.context["games"][series_game].get("main_genre", "unknown"))
            
            if len(series_genres) == 1:
                context_sections.append(f"  - Series genre: {list(series_genres)[0]}")
        
        return "\n".join(context_sections) if context_sections else ""
    
    def _identify_potential_genres(self, reviews_text: str) -> List[Tuple[str, float]]:
        """Identify potential genres efficiently"""
        text_lower = reviews_text.lower()
        genre_scores = {}
        
        # Score genres based on keyword matches
        for genre, genre_data in self.context["genres"].items():
            if genre == "unknown":
                continue
                
            score = 0
            total_possible = 0
            
            # Check unique tags
            for tag, count in genre_data["common_unique_tags"].items():
                total_possible += 1
                if tag in text_lower:
                    score += min(count / genre_data["count"], 1.0)  # Normalize by genre frequency
            
            # Check ratio tags
            for tag, count in genre_data["common_ratio_tags"].items():
                total_possible += 1
                if tag in text_lower:
                    score += min(count / genre_data["count"], 1.0)
            
            if total_possible > 0:
                genre_scores[genre] = score / total_possible
        
        return sorted(genre_scores.items(), key=lambda x: x[1], reverse=True)[:3]
    
    def get_tag_vocabulary(self) -> Dict[str, List[str]]:
        """Get current tag vocabulary for consistency"""
        return {
            "unique_tags": sorted(list(self.context["tags"]["unique_tags"].keys())[:50]),  # Top 50
            "subjective_tags": sorted(list(self.context["tags"]["subjective_tags"].keys())[:50]),
            "ratio_tags": sorted(list(self.context["tags"]["ratio_tags"].keys())[:30]),
            "genres": sorted(list(self.context["genres"].keys())[:20])
        }

def get_games_from_database(db_path="steam_api.db"):
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT game_id, game_name, steam_appid FROM main_game")
        games = cursor.fetchall()
        
        conn.close()
        
        return [{"game_id": row[0], "game_name": row[1], "steam_appid": row[2]} for row in games]
    
    except Exception as e:
        print(f"error reading database: {e}")
        return []

def mentions_toxicity(text: str, phrases=TOXICITY_PHRASES) -> bool:
    lower = text.lower()
    return any(p in lower for p in phrases)

def gameplay_keyword_stats(text: str, keywords=GAMEPLAY_KEYWORDS) -> dict:
    lower_text = text.lower()
    keyword_hits = {kw: lower_text.count(kw) for kw in keywords if kw in lower_text}
    total_hits = sum(keyword_hits.values())
    return {"total": total_hits, "matched_keywords": keyword_hits}

def is_comprehensible(text: str) -> bool:
    unique_chars = set(c.lower() for c in text if c.isalpha())
    if len(unique_chars) < 10:
        return False
    if re.search(r'(.)\1{30,}', text):
        return False
    return True

def is_complaint(text: str) -> bool:
    sentiment = analyzer.polarity_scores(text)
    return sentiment['compound'] < -0.5

def gather_steam_reviews(appid: int, count: int = 100) -> list:
    url = f"https://store.steampowered.com/appreviews/{appid}"
    params = {
        "json": 1,
        "num_per_page": count,
        "filter": "recent",
        "language": "english"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()

        if "reviews" not in data:
            return []
            
        reviews = []
        for review in data["reviews"]:
            reviews.append({
                "author_id": review["author"]["steamid"],
                "review": review["review"],
                "voted_up": review["voted_up"],
                "playtime_hours": round(review["author"]["playtime_forever"] / 60, 1),
                "date": datetime.fromtimestamp(review["timestamp_created"]).isoformat()
            })
        return reviews
    
    except Exception as e:
        print(f"error fetching reviews for appid {appid}: {e}")
        return []

def generate_contextual_game_tags(game_name: str, reviews_text: list, context_manager: LargeScaleContextManager, retry_count: int = 0):
    """Generate tags with large-scale contextual awareness"""
    
    combined_text = " ".join(reviews_text)
    if len(combined_text) > 2000:
        combined_text = combined_text[:2000] + "..."
    
    # Get contextual knowledge
    contextual_knowledge = context_manager.build_contextual_prompt(game_name, combined_text)
    
    # Get current tag vocabulary for consistency
    tag_vocab = context_manager.get_tag_vocabulary()
    
    vocab_context = ""
    if tag_vocab["genres"]:
        vocab_context = f"""
ESTABLISHED VOCABULARY (reuse when appropriate):
- Main genres ({len(context_manager.context['genres'])} total): {', '.join(tag_vocab['genres'])}
- Unique tags ({len(tag_vocab['unique_tags'])} most common): {', '.join(tag_vocab['unique_tags'][:20])}
- Subjective tags ({len(tag_vocab['subjective_tags'])} most common): {', '.join(tag_vocab['subjective_tags'][:20])}
- Ratio tags ({len(tag_vocab['ratio_tags'])} most common): {', '.join(tag_vocab['ratio_tags'][:15])}
"""
    
    system_prompt = f"""You are an expert game analyst with access to a large-scale database of {context_manager.context['stats']['total_games']} games. Your task is to create contextually-aware tags that maintain consistency across the database.

CORE PRINCIPLES:
1. REUSE established genres when games clearly fit existing patterns
2. REUSE established tags when they apply to maintain consistency
3. Create specific sub-genres rather than broad categories
4. Focus on what makes this game distinctive within its established category

CONSISTENCY RULES:
- If this game fits an existing genre pattern, USE THAT EXACT GENRE NAME
- If games are in the same series, they should share genre unless fundamentally different
- Prefer established tag vocabulary over creating new tags
- Only create new tags when existing ones don't capture unique aspects

{vocab_context}

{contextual_knowledge}

Response format:
RATIOS: element1:percentage% element2:percentage% element3:percentage%
MAIN_GENRE: [specific sub-genre - reuse existing if it fits]
UNIQUE_TAGS: tag1, tag2, tag3
SUBJECTIVE_TAGS: tag1, tag2, tag3"""
    
    user_prompt = f"""GAME: {game_name}

STEAM REVIEWS:
{combined_text}

Analyze this game and provide tags that:
1. Are consistent with the established {context_manager.context['stats']['total_games']}-game database
2. Reuse existing genres/tags when this game clearly fits established patterns
3. Highlight what makes this game unique within its category
4. Maintain the database's tagging consistency

IMPORTANT: Prioritize consistency with existing patterns while capturing distinctive elements."""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1,  # Very low for consistency
            max_tokens=200
        )
        
        response_text = response.choices[0].message.content.strip()
        
        # Parse response
        ratios_match = re.search(r'RATIOS:\s*(.+?)(?:\n|$)', response_text)
        genre_match = re.search(r'MAIN_GENRE:\s*(.+?)(?:\n|$)', response_text)
        unique_match = re.search(r'UNIQUE_TAGS:\s*(.+?)(?:\n|$)', response_text)
        subjective_match = re.search(r'SUBJECTIVE_TAGS:\s*(.+?)(?:\n|$)', response_text)
        
        tag_ratios = {}
        main_genre = "unknown"
        unique_tags = []
        subjective_tags = []
        
        if ratios_match:
            ratios_text = ratios_match.group(1)
            ratio_parts = re.findall(r'([^:]+):(\d+)%', ratios_text)
            for tag, percentage in ratio_parts:
                normalized_tag = tag.strip().lower()
                tag_ratios[normalized_tag] = int(percentage)
        
        if genre_match:
            main_genre = genre_match.group(1).strip().lower()
        
        if unique_match:
            unique_text = unique_match.group(1)
            raw_tags = [tag.strip().lower() for tag in unique_text.split(',')]
            unique_tags = [tag for tag in raw_tags if tag]
        
        if subjective_match:
            subjective_text = subjective_match.group(1)
            raw_tags = [tag.strip().lower() for tag in subjective_text.split(',')]
            subjective_tags = [tag for tag in raw_tags if tag]
        
        # Normalize ratios to 100%
        total = sum(tag_ratios.values())
        if total != 100 and total > 0:
            for tag in tag_ratios:
                tag_ratios[tag] = round(tag_ratios[tag] * 100 / total)
            
            diff = 100 - sum(tag_ratios.values())
            if diff != 0 and tag_ratios:
                largest_tag = max(tag_ratios.keys(), key=lambda k: tag_ratios[k])
                tag_ratios[largest_tag] += diff
        
        if not tag_ratios:
            tag_ratios = {"general": 100}
        
        return tag_ratios, main_genre, unique_tags, subjective_tags
        
    except Exception as e:
        error_str = str(e)
        
        if "insufficient_quota" in error_str:
            print(f"API quota exceeded for {game_name}. Skipping...")
            return {"skipped": 100}, "skipped", ["api-limit-reached"], ["skipped"]
        
        elif "rate_limit_exceeded" in error_str:
            if retry_count < 3:
                wait_time = 5 + (retry_count * 2)
                print(f"Rate limit hit for {game_name}. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                return generate_contextual_game_tags(game_name, reviews_text, context_manager, retry_count + 1)
            else:
                print(f"Rate limit persists for {game_name} after 3 retries.")
                return {"rate-limited": 100}, "rate_limited", ["rate-limit-exceeded"], ["rate-limited"]
        
        else:
            print(f"Error generating tags for {game_name}: {error_str}")
            return {"error": 100}, "error", ["unknown-error"], ["error"]

def save_checkpoint(results, filename='checkpoint_large_scale_analysis.json'):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"checkpoint saved: {len(results)} games processed")

def load_checkpoint(filename='checkpoint_large_scale_analysis.json'):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def main():
    if not os.getenv('OPENAI_API_KEY'):
        print("error: openai_api_key environment variable not set")
        return
    
    # Initialize large-scale context manager
    context_manager = LargeScaleContextManager()
    
    # Load existing results or checkpoint
    results_file = 'steam_games_large_scale_tags.json'
    results = load_checkpoint()
    
    if not results:
        try:
            with open(results_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            print(f"loaded {len(results)} existing game analyses")
        except FileNotFoundError:
            results = {}
    
    processed_appids = set(results.keys())
    
    games = get_games_from_database()
    if not games:
        print("no games found in database!")
        return
    
    print(f"found {len(games)} games in database")
    print(f"already processed: {len(processed_appids)} games")
    print(f"context database: {len(context_manager.context['games'])} games, {len(context_manager.context['genres'])} genres")
    
    remaining_games = [g for g in games if str(g["steam_appid"]) not in processed_appids]
    print(f"remaining to process: {len(remaining_games)} games")
    
    if not remaining_games:
        print("all games processed!")
        return
    
    for i, game in enumerate(remaining_games, 1):
        appid = game["steam_appid"]
        game_name = game["game_name"]
        
        print(f"\n=== processing {i}/{len(remaining_games)}: {game_name} (appid: {appid}) ===")
        
        raw_reviews = gather_steam_reviews(appid, 200)
        if not raw_reviews:
            print(f"no reviews found for {game_name}")
            results[str(appid)] = {
                "game_id": game["game_id"],
                "name": game_name,
                "steam_appid": appid,
                "reviews": [],
                "tag_ratios": {},
                "main_genre": "unknown",
                "unique_tags": [],
                "subjective_tags": [],
                "processing_date": datetime.now().isoformat(),
                "status": "no_reviews"
            }
            continue
        
        raw_reviews.sort(key=lambda r: r["playtime_hours"], reverse=True)
        
        filtered_reviews = []
        fallback_candidates = []
        
        for r in raw_reviews:
            text = r['review']
            if len(text) < 200 or r["playtime_hours"] < 1:
                continue
            if not is_comprehensible(text):
                continue

            stats = gameplay_keyword_stats(text)
            r["keyword_stats"] = stats

            if stats["total"] < 1:
                continue

            fallback_candidates.append(r)

            if stats["total"] < 6:
                continue
            if is_complaint(text) and mentions_toxicity(text):
                continue

            filtered_reviews.append(r)

        if not filtered_reviews and fallback_candidates:
            best_fallback = sorted(
                fallback_candidates,
                key=lambda r: (r["voted_up"], r["keyword_stats"]["total"]),
                reverse=True
            )[0]
            filtered_reviews.append(best_fallback)

        top_reviews = filtered_reviews[:3]
        
        tag_ratios = {}
        main_genre = "unknown"
        unique_tags = []
        subjective_tags = []
        
        if top_reviews:
            review_texts = [r["review"] for r in top_reviews]
            
            # Generate contextual tags using large-scale system
            tag_ratios, main_genre, unique_tags, subjective_tags = generate_contextual_game_tags(
                game_name, review_texts, context_manager
            )
            
            print(f"main genre: {main_genre}")
            print(f"unique tags: {', '.join(unique_tags)}")
            print(f"subjective tags: {', '.join(subjective_tags)}")
            print(f"breakdown: {' '.join([f'{tag}:{percent}%' for tag, percent in tag_ratios.items()])}")
        
        # Store results
        game_data = {
            "game_id": game["game_id"],
            "name": game_name,
            "steam_appid": appid,
            "reviews": top_reviews,
            "tag_ratios": tag_ratios,
            "main_genre": main_genre,
            "unique_tags": unique_tags,
            "subjective_tags": subjective_tags,
            "processing_date": datetime.now().isoformat(),
            "status": "processed"
        }
        
        results[str(appid)] = game_data
        
        # Add to context database (batched for efficiency)
        if tag_ratios and main_genre != "unknown":
            context_manager.add_game(game_name, game_data)
        
        # Show context stats periodically
        if i % 100 == 0:
            print(f"context stats: {len(context_manager.context['games'])} games, {len(context_manager.context['genres'])} genres")
            if context_manager.context["stats"]["most_common_genre"]:
                print(f"most common genre: {context_manager.context['stats']['most_common_genre']}")
        
        print(f"found {len(top_reviews)} quality reviews")
        
        # Save progress every 25 games for large-scale processing
        if i % 25 == 0:
            save_checkpoint(results)
            context_manager.save_context()
            print(f"progress saved: {i}/{len(remaining_games)} games processed")
            time.sleep(1)  # Brief pause to avoid overwhelming the API
    
    # Final save
    with open(results_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Force save context
    context_manager.save_context(force=True)
    
    print(f"\n{'='*80}")
    print(f"large-scale contextual analysis complete!")
    print(f"total games processed: {len(results)}")
    print(f"results saved to: {results_file}")
    
    print(f"\ncontext database statistics:")
    print(f"games in context: {len(context_manager.context['games'])}")
    print(f"genres identified: {len(context_manager.context['genres'])}")
    print(f"series tracked: {len(context_manager.context['series'])}")
    print(f"unique tags: {len(context_manager.context['tags']['unique_tags'])}")
    print(f"most common genre: {context_manager.context['stats']['most_common_genre']}")
    
    # Show top genres
    if context_manager.context['genres']:
        print(f"\ntop 10 genres by frequency:")
        sorted_genres = sorted(context_manager.context['genres'].items(), 
                             key=lambda x: x[1].get('count', 0), reverse=True)
        for i, (genre, data) in enumerate(sorted_genres[:10], 1):
            print(f"{i:2d}. {genre}: {data['count']} games")
    
    # Show sample series
    if context_manager.context['series']:
        print(f"\nsample game series detected:")
        for i, (series, games) in enumerate(list(context_manager.context['series'].items())[:5], 1):
            print(f"{i}. {series}: {', '.join(games[:3])}")
    
    print(f"\nfiles created/updated:")
    print(f"- {results_file}: main results with contextual tags")
    print(f"- {CONTEXT_DB}: large-scale context database ({os.path.getsize(CONTEXT_DB) // 1024}KB)")
    
    # Cleanup checkpoint
    checkpoint_file = 'checkpoint_large_scale_analysis.json'
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
        print("checkpoint file removed")

# Utility functions for analyzing the large-scale context database

def analyze_context_database(context_file: str = CONTEXT_DB):
    """Analyze the large-scale context database"""
    try:
        with open(context_file, 'r', encoding='utf-8') as f:
            context = json.load(f)
        
        print(f"=== LARGE-SCALE CONTEXT DATABASE ANALYSIS ===")
        print(f"total games: {len(context['games'])}")
        print(f"total genres: {len(context['genres'])}")
        print(f"total series: {len(context['series'])}")
        
        # Genre distribution
        print(f"\ngenre distribution:")
        sorted_genres = sorted(context['genres'].items(), key=lambda x: x[1].get('count', 0), reverse=True)
        for i, (genre, data) in enumerate(sorted_genres[:15], 1):
            examples = ', '.join(data['examples'][-3:])  # Last 3 examples
            print(f"{i:2d}. {genre}: {data['count']} games (e.g., {examples})")
        
        # Most common tags across all games
        print(f"\nmost reused unique tags:")
        sorted_unique = sorted(context['tags']['unique_tags'].items(), key=lambda x: x[1], reverse=True)
        for i, (tag, count) in enumerate(sorted_unique[:20], 1):
            print(f"{i:2d}. {tag}: {count} games")
        
        # Series analysis
        print(f"\nlargest game series:")
        sorted_series = sorted(context['series'].items(), key=lambda x: len(x[1]), reverse=True)
        for i, (series, games) in enumerate(sorted_series[:10], 1):
            print(f"{i:2d}. {series}: {len(games)} games ({', '.join(games[:3])})")
        
        return context
        
    except FileNotFoundError:
        print(f"context database {context_file} not found")
        return None

def search_games_by_tags(context_file: str = CONTEXT_DB, genre: str = None, 
                        has_tags: List[str] = None, exclude_tags: List[str] = None):
    """Search games in context database by criteria"""
    try:
        with open(context_file, 'r', encoding='utf-8') as f:
            context = json.load(f)
        
        matching_games = []
        
        for game_name, game_data in context['games'].items():
            # Genre filter
            if genre and game_data.get('main_genre', '').lower() != genre.lower():
                continue
            
            # Required tags filter
            if has_tags:
                game_tags = set(game_data.get('unique_tags', []) + game_data.get('subjective_tags', []))
                if not all(tag.lower() in [t.lower() for t in game_tags] for tag in has_tags):
                    continue
            
            # Excluded tags filter
            if exclude_tags:
                game_tags = set(game_data.get('unique_tags', []) + game_data.get('subjective_tags', []))
                if any(tag.lower() in [t.lower() for t in game_tags] for tag in exclude_tags):
                    continue
            
            matching_games.append({
                'name': game_name,
                'genre': game_data.get('main_genre'),
                'unique_tags': game_data.get('unique_tags', []),
                'subjective_tags': game_data.get('subjective_tags', []),
                'appid': game_data.get('steam_appid')
            })
        
        print(f"found {len(matching_games)} matching games:")
        for game in matching_games[:20]:  # Show first 20
            print(f"- {game['name']} ({game['genre']}): {', '.join(game['unique_tags'][:3])}")
        
        return matching_games
        
    except FileNotFoundError:
        print(f"context database {context_file} not found")
        return []

def get_genre_recommendations(context_file: str = CONTEXT_DB, target_genre: str = None):
    """Get game recommendations within a specific genre"""
    try:
        with open(context_file, 'r', encoding='utf-8') as f:
            context = json.load(f)
        
        if target_genre not in context['genres']:
            print(f"genre '{target_genre}' not found")
            available = list(context['genres'].keys())[:10]
            print(f"available genres: {', '.join(available)}")
            return []
        
        genre_data = context['genres'][target_genre]
        print(f"\n=== {target_genre.upper()} RECOMMENDATIONS ===")
        print(f"total games in genre: {genre_data['count']}")
        
        # Show common patterns
        common_unique = sorted(genre_data['common_unique_tags'].items(), key=lambda x: x[1], reverse=True)[:5]
        common_subjective = sorted(genre_data['common_subjective_tags'].items(), key=lambda x: x[1], reverse=True)[:5]
        
        print(f"common features: {', '.join([tag for tag, count in common_unique])}")
        print(f"common qualities: {', '.join([tag for tag, count in common_subjective])}")
        
        print(f"\nrecent examples:")
        for game in genre_data['examples']:
            if game in context['games']:
                game_data = context['games'][game]
                tags = ', '.join(game_data.get('unique_tags', [])[:3])
                print(f"- {game}: {tags}")
        
        return genre_data['examples']
        
    except FileNotFoundError:
        print(f"context database {context_file} not found")
        return []

if __name__ == "__main__":
    main()