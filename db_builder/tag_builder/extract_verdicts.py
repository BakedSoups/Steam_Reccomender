# using chat gipidy this reads game_verdicts and creates tags

import json
import re
from bs4 import BeautifulSoup
from openai import OpenAI
import os
from typing import List, Dict

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def generate_game_tags(game_name: str, verdict: str, score: str) -> List[str]:
    """
    Use OpenAI to generate game tags based on the verdict text
    """
    system_prompt = """You are a game categorization expert. Based on game review verdicts, you generate relevant tags that describe:
    - Genre (e.g., RPG, FPS, puzzle, adventure, platformer)
    - Art style (e.g., cel-shaded, pixel art, realistic, noir)
    - Mood/atmosphere (e.g., dark, cheerful, melancholic, intense)
    - Themes (e.g., fantasy, sci-fi, mystery, horror, emotional)
    - Gameplay elements (e.g., open-world, narrative-driven, combat-focused)
    
    Return only tags in parentheses format like: (tag1) (tag2) (tag3)
    Aim for 3-8 relevant tags per game. Keep tags concise (1-3 words)."""
    
    user_prompt = f"""Game: {game_name}
Score: {score}
Verdict: {verdict}

Based on this verdict, what tags best describe this game?"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=100
        )
        
        tags_text = response.choices[0].message.content.strip()
        
        tags = re.findall(r'\(([^)]+)\)', tags_text)
        
        if not tags:
            # clean up potential hallucinations
            potential_tags = re.split(r'[,\n]', tags_text)
            tags = [tag.strip().strip('()') for tag in potential_tags if tag.strip()]
        
        return tags
        
    except Exception as e:
        print(f"Error generating tags for {game_name}: {str(e)}")
        return []

def process_existing_verdicts(verdicts_file='game_verdicts_complete.json', output_file='game_verdicts_with_tags.json'):
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
            
            # tags using OpenAI
            tags = generate_game_tags(name, verdict, score)
            
            updated_data = {
                'name': name,
                'score': score,
                'url': url,
                'verdict': verdict,
                'tags': tags
            }
            
            verdicts_with_tags.append(updated_data)
            
            print(f"{i:2d}. {name} (Score: {score})")
            print(f"    Tags: {' '.join([f'({tag})' for tag in tags])}")
            print("-" * 80)
        
        # save results into json not sqlite (gasp)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(verdicts_with_tags, f, ensure_ascii=False, indent=2)
        
        print(f"\nSummary:")
        print(f"Total verdicts processed: {len(verdicts)}")
        print(f"Results saved to {output_file}")
        
        return verdicts_with_tags
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return []

if __name__ == "__main__":
    if not os.getenv('OPENAI_API_KEY'):
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Please set it using: export OPENAI_API_KEY='your-api-key'")
        exit(1)
    
    verdicts = process_existing_verdicts()
    
    if verdicts:
        print(f"\nFinal check: {len(verdicts)} verdicts processed with tags")
        
        # show some examples
        print("\nExample outputs:")
        for verdict in verdicts[:3]:
            print(f"\nGame: {verdict['name']}")
            print(f"Score: {verdict['score']}")
            print(f"Tags: {' '.join([f'({tag})' for tag in verdict['tags']])}")
            print(f"Verdict preview: {verdict['verdict'][:200]}...")