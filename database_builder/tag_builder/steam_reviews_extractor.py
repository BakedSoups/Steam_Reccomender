import requests
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import re

analyzer = SentimentIntensityAnalyzer()

GAMEPLAY_KEYWORDS = {
    # Moods
    "vibes", "soundtrack", "music",

    #insightful review keywords
    "overall", "the good", "pros", "cons"
    # Mechanics
    "mechanics", "controls", "gameplay", "combat", "movement", "pacing",
    "shooting", "platforming", "turn based", "real time", "puzzle", "exploration",
    "stealth", "driving", "flying", "building", "crafting",

    # Structure
    "level", "missions", "quests", "campaign", "objectives", "checkpoints",
    "difficulty", "progression", "grind", "boss", "miniboss", "enemy ai", 
    "chill",

    # Multiplayer/Interaction
    "multiplayer", "co-op", "singleplayer", "team",
    "ranked", "competitive", "pvp", "pve", "sandbox", "open world",

    # Customization/Systems
    "inventory", "skills", "abilities", "tree", "upgrade", "loadout", "gear",
    "weapons", "armor", "stats", "classes", "perks", "mods", "economy",

    # Genre hooks
    "fps", "rpg", "roguelike", "deck builder", "platformer", "shooter", "metroidvania",
    "strategy", "simulation", "management", "builder", "survival", "horror"
}

TOXICITY_PHRASES = {
    "toxic", "grief", "flamed", "slur", "racism", "sexism", "trash community",
    "abandoned", "report system", "mute button", "valve doesn't care",
    "worst community", "matchmaking is broken", "smurfs", "trolls", "chain queuing"
}

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
    if re.search(r'(.)\1{30,}', text):  # spam bomb filter
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
    response = requests.get(url, params=params)
    data = response.json()

    if "reviews" not in data:
        raise Exception("No reviews in this game")
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

if __name__ == "__main__":
    appids = [570, 730, 271590, 578080, 1174180]  # Dota 2, CS:GO, GTA V, PUBG, RDR2
    results = {}

    for appid in appids:
        raw_reviews = gather_steam_reviews(appid, 200)
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
                continue  # don’t even count as fallback if no keywords

            fallback_candidates.append(r)

            if stats["total"] < 6:
                continue
            if is_complaint(text) and mentions_toxicity(text):
                continue

            filtered_reviews.append(r)

        # === Fallback if none pass filter ===
        if not filtered_reviews and fallback_candidates:
            best_fallback = sorted(
                fallback_candidates,
                key=lambda r: (r["voted_up"], r["keyword_stats"]["total"]),
                reverse=True
            )[0]
            filtered_reviews.append(best_fallback)

        results[appid] = filtered_reviews[:3]

    # === OUTPUT ===
    for appid, reviews in results.items():
        print(f"\n=== Top reviews for AppID: {appid} ===\n")
        for i, r in enumerate(reviews, 1):
            print(f"{i}. ({r['date']}) upvoted: {r['voted_up']} | {r['playtime_hours']} hrs")
            print(r['review'])
            print(f"\nGameplay keyword count: {r['keyword_stats']['total']}")
            print(f"Keywords matched: {r['keyword_stats']['matched_keywords']}\n{'-'*80}\n")