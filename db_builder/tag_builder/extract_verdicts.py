# this is a all in one tag creator for any yt channel

import json
import re
from bs4 import BeautifulSoup
from openai import OpenAI
import os
from typing import List, Dict, Tuple, Set
import time

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

TAG_CONTEXT = {
    'ratio_tags': set(),
    'unique_tags': set(),
    'subjective_tags': set(),
    'main_genres': set()
}

def extract_score(score_str: str) -> float:
    """Extract numeric score from various formats"""
    if not score_str or score_str == 'N/A':
        return None
    
    numbers = re.findall(r'(\d+(?:\.\d+)?)', score_str)
    if numbers:
        score = float(numbers[0])
        if score > 10:
            score = score / 10
        return score
    return None

def generate_game_tags_with_ratios(game_name: str, verdict: str, score: str, retry_count: int = 0) -> Tuple[Dict[str, int], str, List[str], List[str]]:
    """
    Use OpenAI to generate game tags with ratios based on the verdict text
    Returns: (tag_ratios, main_genre, unique_tags, subjective_tags)
    """
    existing_ratio_tags = ', '.join(sorted(TAG_CONTEXT['ratio_tags'])) if TAG_CONTEXT['ratio_tags'] else "None yet"
    existing_unique_tags = ', '.join(sorted(TAG_CONTEXT['unique_tags'])) if TAG_CONTEXT['unique_tags'] else "None yet"
    existing_subjective_tags = ', '.join(sorted(TAG_CONTEXT['subjective_tags'])) if TAG_CONTEXT['subjective_tags'] else "None yet"
    existing_genres = ', '.join(sorted(TAG_CONTEXT['main_genres'])) if TAG_CONTEXT['main_genres'] else "None yet"
    
    system_prompt = f"""You are a game categorization expert. Based on game review verdicts, you analyze games and provide:

1. A percentage breakdown of the game's core elements (must total 100%)
2. The main genre classification
3. Unique searchable tags that distinguish this game within its genre (2-4 tags)
4. Subjective tags that capture the reviewer's opinion (2-4 tags)

IMPORTANT RULES FOR CONSISTENCY:
- Always use lowercase for all tags
- Never use plurals (use "horror" not "horrors")
- If a similar tag exists, use the existing one exactly
- For objective tags, use neutral descriptive terms only
- For subjective tags, capture the reviewer's opinion (can include quality assessments)

For common concepts, always use these canonical forms:
  * "horror" (not "scary", "frightening", "spooky")
  * "rpg" (not "role-playing", "role playing")
  * "fps" (not "first-person", "shooter")
  * "anime" (not "japanese animation")
  * "cel-shaded" (not "cell shaded")

Existing tags to reuse when appropriate:
- Ratio tags: {existing_ratio_tags}
- Unique tags: {existing_unique_tags}
- Subjective tags: {existing_subjective_tags}
- Genres: {existing_genres}

Response format:
RATIOS: element1:percentage% element2:percentage% element3:percentage%
MAIN_GENRE: [single genre classification]
UNIQUE_TAGS: tag1, tag2, tag3
SUBJECTIVE_TAGS: tag1, tag2, tag3

Example:
RATIOS: anime:20% rpg:40% jazz:40%
MAIN_GENRE: JRPG
UNIQUE_TAGS: jazz-soundtrack, social-sim, tokyo-setting
SUBJECTIVE_TAGS: addictive-gameplay, emotional-story, stylish-presentation"""
    
    max_verdict_length = 500
    if len(verdict) > max_verdict_length:
        verdict = verdict[:max_verdict_length] + "..."
    
    user_prompt = f"""Game: {game_name}
Score: {score}
Verdict: {verdict}

Analyze this game and provide:
1. A percentage breakdown of its core elements (must total 100%)
2. Its main genre classification  
3. Unique searchable tags that distinguish it within its genre (2-4 tags, objective only)
4. Subjective tags that capture the reviewer's opinion (2-4 tags, can include quality assessments)"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=120  # Increased slightly for subjective tags
        )
        
        response_text = response.choices[0].message.content.strip()
        
        ratios_match = re.search(r'RATIOS:\s*(.+?)(?:\n|$)', response_text)
        genre_match = re.search(r'MAIN_GENRE:\s*(.+?)(?:\n|$)', response_text)
        unique_match = re.search(r'UNIQUE_TAGS:\s*(.+?)(?:\n|$)', response_text)
        subjective_match = re.search(r'SUBJECTIVE_TAGS:\s*(.+?)(?:\n|$)', response_text)
        
        tag_ratios = {}
        main_genre = "Unknown"
        unique_tags = []
        subjective_tags = []
        
        if ratios_match:
            ratios_text = ratios_match.group(1)
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
        
        if subjective_match:
            subjective_text = subjective_match.group(1)
            raw_tags = [tag.strip().lower() for tag in subjective_text.split(',')]
            for tag in raw_tags:
                if tag and tag not in subjective_tags:
                    subjective_tags.append(tag)
                    TAG_CONTEXT['subjective_tags'].add(tag)
        
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
        
        return tag_ratios, main_genre, unique_tags, subjective_tags
        
    except Exception as e:
        error_str = str(e)
        
        if "insufficient_quota" in error_str:
            print(f"API quota exceeded for {game_name}. Skipping...")
            return {"skipped": 100}, "SKIPPED", ["api-limit-reached"], ["skipped"]
        
        elif "rate_limit_exceeded" in error_str:
            wait_time = 1  
            if "Please try again in" in error_str:
                try:
                    wait_match = re.search(r'Please try again in (\d+)ms', error_str)
                    if wait_match:
                        wait_time = int(wait_match.group(1)) / 1000  
                    else:
                        wait_time = 5
                except:
                    wait_time = 5
            
            if retry_count < 3:  
                print(f"Rate limit hit for {game_name}. Waiting {wait_time} seconds before retry {retry_count + 1}/3...")
                time.sleep(wait_time + 0.5)  
                return generate_game_tags_with_ratios(game_name, verdict, score, retry_count + 1)
            else:
                print(f"Rate limit persists for {game_name} after 3 retries. Marking as rate-limited.")
                return {"rate-limited": 100}, "RATE_LIMITED", ["rate-limit-exceeded"], ["rate-limited"]
        
        else:
            print(f"Error generating tags for {game_name}: {error_str}")
            return {"error": 100}, "ERROR", ["unknown-error"], ["error"]

def save_tag_context(filename='tag_context.json'):
    """Save the tag context to a file for future runs"""
    context_to_save = {
        'ratio_tags': list(TAG_CONTEXT['ratio_tags']),
        'unique_tags': list(TAG_CONTEXT['unique_tags']),
        'subjective_tags': list(TAG_CONTEXT['subjective_tags']),
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
            TAG_CONTEXT['subjective_tags'] = set(saved_context.get('subjective_tags', []))
            TAG_CONTEXT['main_genres'] = set(saved_context.get('main_genres', []))
    except FileNotFoundError:
        print("No existing tag context found, starting fresh")

def save_checkpoint(verdicts, filename='checkpoint_game_verdicts.json'):
    """Save current progress to a checkpoint file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(verdicts, f, ensure_ascii=False, indent=2)
    print(f"Checkpoint saved: {len(verdicts)} games processed")

def load_checkpoint(filename='checkpoint_game_verdicts.json'):
    """Load from checkpoint if it exists"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def process_existing_verdicts(verdicts_file='game_verdicts_complete.json', 
                            output_file='game_verdicts_with_ratio_tags.json',
                            chunk_size=50):
    """Process verdicts with chunking - no concurrency"""
    load_tag_context()
    
    processed_verdicts = load_checkpoint()
    processed_names = {v['name'] for v in processed_verdicts}
    
    try:
        with open(verdicts_file, 'r', encoding='utf-8') as f:
            all_verdicts = json.load(f)
        
        remaining_verdicts = [v for v in all_verdicts if v.get('name') not in processed_names]
        
        print(f"\nTotal verdicts: {len(all_verdicts)}")
        print(f"Already processed: {len(processed_verdicts)}")
        print(f"Remaining to process: {len(remaining_verdicts)}")
        print("="*80)
        
        # Process one by one
        for i, verdict_data in enumerate(remaining_verdicts, 1):
            name = verdict_data.get('name', 'Unknown')
            original_score = verdict_data.get('score', 'N/A')
            url = verdict_data.get('url', '')
            verdict = verdict_data.get('verdict', '')
            
            print(f"\nProcessing {i}/{len(remaining_verdicts)}: {name}")
            
            tag_ratios, main_genre, unique_tags, subjective_tags = generate_game_tags_with_ratios(name, verdict, original_score)
            
            numeric_score = extract_score(original_score)
            
            updated_data = {
                'name': name,
                'score': original_score,  # Keep original score string
                'numeric_score': numeric_score,  # Add numeric score for sorting/filtering
                'url': url,
                'verdict': verdict,
                'tag_ratios': tag_ratios,
                'main_genre': main_genre,
                'unique_tags': unique_tags,
                'subjective_tags': subjective_tags  # Add subjective tags
            }
            
            processed_verdicts.append(updated_data)
            
            print(f"    Score: {original_score} (numeric: {numeric_score})")
            print(f"    Main Genre: {main_genre}")
            print(f"    Unique Tags: {', '.join(unique_tags)}")
            print(f"    Subjective Tags: {', '.join(subjective_tags)}")
            print(f"    Breakdown: {' '.join([f'{tag}:{percent}%' for tag, percent in tag_ratios.items()])}")
            
            if i % chunk_size == 0:
                save_checkpoint(processed_verdicts)
                save_tag_context()
                print(f"\nReached checkpoint at {i} games")
                time.sleep(2)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_verdicts, f, ensure_ascii=False, indent=2)
        
        print(f"\n{'='*80}")
        print(f"Summary:")
        print(f"Total verdicts processed: {len(processed_verdicts)}")
        print(f"Results saved to {output_file}")
        print(f"Tag context saved for consistency")

        print(f"\nTag Statistics:")
        print(f"Ratio tags: {len(TAG_CONTEXT['ratio_tags'])}")
        print(f"Unique tags: {len(TAG_CONTEXT['unique_tags'])}")
        print(f"Subjective tags: {len(TAG_CONTEXT['subjective_tags'])}")
        print(f"Main genres: {len(TAG_CONTEXT['main_genres'])}")
        
        if os.path.exists('checkpoint_game_verdicts.json'):
            os.remove('checkpoint_game_verdicts.json')
            print("Checkpoint file removed after successful completion")
        
        return processed_verdicts
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return processed_verdicts  

if __name__ == "__main__":
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set it using: export OPENAI_API_KEY='your-api-key'")
        exit(1)
    
    verdicts = process_existing_verdicts(chunk_size=50)