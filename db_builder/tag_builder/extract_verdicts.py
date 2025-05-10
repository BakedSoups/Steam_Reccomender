import json
import re
from bs4 import BeautifulSoup
from openai import OpenAI
import os
from typing import List, Dict, Tuple, Set

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# Global tag context to prevent duplicates
TAG_CONTEXT = {
    'ratio_tags': set(),
    'unique_tags': set(),
    'main_genres': set()
}

def generate_game_tags_with_ratios(game_name: str, verdict: str, score: str) -> Tuple[Dict[str, int], str, List[str]]:
    """
    Use OpenAI to generate game tags with ratios based on the verdict text
    Returns: (tag_ratios, main_genre, unique_tags)
    """
    existing_ratio_tags = ', '.join(sorted(TAG_CONTEXT['ratio_tags'])) if TAG_CONTEXT['ratio_tags'] else "None yet"
    existing_unique_tags = ', '.join(sorted(TAG_CONTEXT['unique_tags'])) if TAG_CONTEXT['unique_tags'] else "None yet"
    existing_genres = ', '.join(sorted(TAG_CONTEXT['main_genres'])) if TAG_CONTEXT['main_genres'] else "None yet"
    
    system_prompt = f"""You are a game categorization expert. Based on game review verdicts, you analyze games and provide:

1. A percentage breakdown of the game's core elements (must total 100%)
2. The main genre classification
3. Unique searchable tags that distinguish this game within its genre (2-4 tags)

IMPORTANT RULES FOR CONSISTENCY:
- Always use lowercase for all tags
- Never use plurals (use "horror" not "horrors")
- If a similar tag exists, use the existing one exactly
- For common concepts, always use these canonical forms:
  * "horror" (not "scary", "frightening", "spooky")
  * "rpg" (not "role-playing", "role playing")
  * "fps" (not "first-person", "shooter")
  * "anime" (not "japanese animation")
  * "cel-shaded" (not "cell shaded")

Existing tags to reuse when appropriate:
- Ratio tags: {existing_ratio_tags}
- Unique tags: {existing_unique_tags}
- Genres: {existing_genres}

Response format:
RATIOS: element1:percentage% element2:percentage% element3:percentage%
MAIN_GENRE: [single genre classification]
UNIQUE_TAGS: tag1, tag2, tag3

Example:
RATIOS: anime:20% rpg:40% jazz:40%
MAIN_GENRE: JRPG
UNIQUE_TAGS: jazz-soundtrack, social-sim, tokyo-setting"""
    
    user_prompt = f"""Game: {game_name}
Score: {score}
Verdict: {verdict}

Analyze this game and provide:
1. A percentage breakdown of its core elements (must total 100%)
2. Its main genre classification  
3. Unique searchable tags that distinguish it within its genre (2-4 tags)"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=150
        )
        
        response_text = response.choices[0].message.content.strip()
        
        ratios_match = re.search(r'RATIOS:\s*(.+?)(?:\n|$)', response_text)
        genre_match = re.search(r'MAIN_GENRE:\s*(.+?)(?:\n|$)', response_text)
        unique_match = re.search(r'UNIQUE_TAGS:\s*(.+?)(?:\n|$)', response_text)
        
        tag_ratios = {}
        main_genre = "Unknown"
        unique_tags = []
        
        if ratios_match:
            ratios_text = ratios_match.group(1)
            # example "anime:20% rpg:40% jazz:40%"
            ratio_parts = re.findall(r'([^:]+):(\d+)%', ratios_text)
            for tag, percentage in ratio_parts:
                normalized_tag = tag.strip().lower()
                tag_ratios[normalized_tag] = int(percentage)
                TAG_CONTEXT['ratio_tags'].add(normalized_tag)
        
        if genre_match:
            main_genre = genre_match.group(1).strip()
            TAG_CONTEXT['main_genres'].add(main_genre)
        
        if unique_match:
            unique_text = unique_match.group(1)
            raw_tags = [tag.strip().lower() for tag in unique_text.split(',')]
            for tag in raw_tags:
                if tag and tag not in unique_tags:
                    unique_tags.append(tag)
                    TAG_CONTEXT['unique_tags'].add(tag)
        
        total = sum(tag_ratios.values())
        if total != 100 and total > 0:
            for tag in tag_ratios:
                tag_ratios[tag] = round(tag_ratios[tag] * 100 / total)
            
            diff = 100 - sum(tag_ratios.values())
            if diff != 0 and tag_ratios:
                largest_tag = max(tag_ratios.keys(), key=lambda k: tag_ratios[k])
                tag_ratios[largest_tag] += diff
        
        if not tag_ratios:
            print(f"Warning: Could not parse ratios for {game_name}, using fallback")
            tag_ratios = {"general": 100}
        
        return tag_ratios, main_genre, unique_tags
        
    except Exception as e:
        print(f"Error generating tags for {game_name}: {str(e)}")
        return {"error": 100}, "Unknown", ["unknown"]

def save_tag_context(filename='tag_context.json'):
    """Save the tag context to a file for future runs"""
    context_to_save = {
        'ratio_tags': list(TAG_CONTEXT['ratio_tags']),
        'unique_tags': list(TAG_CONTEXT['unique_tags']),
        'main_genres': list(TAG_CONTEXT['main_genres'])
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(context_to_save, f, ensure_ascii=False, indent=2)

def load_tag_context(filename='tag_context.json'):
    """Load the tag context from a previous run"""
    global TAG_CONTEXT
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            saved_context = json.load(f)
            TAG_CONTEXT['ratio_tags'] = set(saved_context.get('ratio_tags', []))
            TAG_CONTEXT['unique_tags'] = set(saved_context.get('unique_tags', []))
            TAG_CONTEXT['main_genres'] = set(saved_context.get('main_genres', []))
    except FileNotFoundError:
        print("No existing tag context found, starting fresh")

def process_existing_verdicts(verdicts_file='game_verdicts_complete.json', output_file='game_verdicts_with_ratio_tags.json'):
    # Load existing tag context if available
    load_tag_context()
    
    try:
        with open(verdicts_file, 'r', encoding='utf-8') as f:
            verdicts = json.load(f)
        
        print(f"\nProcessing {len(verdicts)} existing verdicts...")
        print("="*80)
        
        verdicts_with_tags = []
        
        for i, verdict_data in enumerate(verdicts, 1):
            name = verdict_data.get('name', 'Unknown')
            score = verdict_data.get('score', 'N/A')
            url = verdict_data.get('url', '')
            verdict = verdict_data.get('verdict', '')
            
            tag_ratios, main_genre, unique_tags = generate_game_tags_with_ratios(name, verdict, score)
            
            updated_data = {
                'name': name,
                'score': score,
                'url': url,
                'verdict': verdict,
                'tag_ratios': tag_ratios,
                'main_genre': main_genre,
                'unique_tags': unique_tags  # Now a list of searchable tags
            }
            
            verdicts_with_tags.append(updated_data)
            
            print(f"{i:2d}. {name} (Score: {score})")
            print(f"    Main Genre: {main_genre}")
            print(f"    Unique Tags: {', '.join(unique_tags)}")
            print(f"    Breakdown: {' '.join([f'{tag}:{percent}%' for tag, percent in tag_ratios.items()])}")
            print("-" * 80)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(verdicts_with_tags, f, ensure_ascii=False, indent=2)
        
        save_tag_context()
        
        print(f"\nSummary:")
        print(f"Total verdicts processed: {len(verdicts)}")
        print(f"Results saved to {output_file}")
        print(f"Tag context saved for consistency")

        print(f"\nTag Statistics:")
        print(f"Ratio tags: {len(TAG_CONTEXT['ratio_tags'])}")
        print(f"Unique tags: {len(TAG_CONTEXT['unique_tags'])}")
        print(f"Main genres: {len(TAG_CONTEXT['main_genres'])}")
        
        return verdicts_with_tags
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return []

def format_game_description(game_data: Dict) -> str:
    """
    Format a game's data into a readable description
    """
    name = game_data['name']
    main_genre = game_data['main_genre']
    unique_tags = game_data['unique_tags']
    ratios = game_data['tag_ratios']
    
    ratio_str = " + ".join([f"{percent}% {tag}" for tag, percent in ratios.items()])
    tags_str = ", ".join(unique_tags)
    
    return f"{name}: {main_genre} - [{tags_str}] ({ratio_str})"

if __name__ == "__main__":
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set it using: export OPENAI_API_KEY='your-api-key'")
        exit(1)
    
    verdicts = process_existing_verdicts()
    