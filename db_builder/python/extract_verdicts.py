import json
import re
from bs4 import BeautifulSoup
from openai import OpenAI
import os
from typing import List, Dict

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def extract_verdict_or_conclusion(html_content):
    """
    Extract the verdict section or conclusion from the HTML content
    Always returns something - never returns "not found"
    """
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        verdict_section = soup.find('div', {'data-cy': 'verdict'})
        if verdict_section:
            verdict_para = verdict_section.find('p', {'data-cy': 'article-verdict-paragraph'})
            if verdict_para:
                return verdict_para.get_text(strip=True)
        
        verdict_elem = soup.find(['div', 'section', 'p'], class_=re.compile('verdict', re.I))
        if verdict_elem:
            text = verdict_elem.get_text(strip=True)
            if len(text) > 50:  # make sure sure it didn't get limited
                return text
        
        verdict_heading = soup.find(['h1', 'h2', 'h3', 'h4'], string=re.compile('verdict', re.I))
        if verdict_heading:
            next_elem = verdict_heading.find_next_sibling(['p', 'div'])
            if next_elem:
                return next_elem.get_text(strip=True)
        
        article_content = soup.find('div', class_='article-content')
        if not article_content:
            article_content = soup.find('article')
            if not article_content:
                article_content = soup.find('div', class_=re.compile('content', re.I))
        
        if article_content:
            paragraphs = article_content.find_all('p')
            
            # filter out empty paragraphs and those with less than 50 characters
            substantial_paragraphs = [p for p in paragraphs if len(p.get_text(strip=True)) > 50]
            
            if substantial_paragraphs:
                # find the last substantial paragraph before any polls/ads
                for i in range(len(substantial_paragraphs) - 1, -1, -1):
                    para_text = substantial_paragraphs[i].get_text(strip=True)
                    if len(para_text) > 100 and not para_text.startswith('Advertisement'):
                        return para_text
                
                # no good conclusion found, return the last substantial paragraph
                return substantial_paragraphs[-1].get_text(strip=True)
        all_text = soup.get_text()
        words = all_text.split()
        
        # if there is not (verdict) then just extract the last 300 meaningful words
        meaningful_words = []
        for word in reversed(words):
            if len(word) > 2:  # Skip very short words
                meaningful_words.insert(0, word)
                if len(meaningful_words) >= 300:
                    break
        
        if meaningful_words:
            return "...[extracted conclusion] " + ' '.join(meaningful_words)
        
        return "Unable to extract verdict - content parsing failed"
        
    except Exception as e:
        return f"Error extracting content: {str(e)}"

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
    
    # process all reviews from scratch
    # verdicts = process_all_reviews()
    
    # Or process an existing verdicts file
    verdicts = process_existing_verdicts()
    
    if verdicts:
        print(f"\nFinal check: {len(verdicts)} verdicts processed with tags")
        
        # Show some examples
        print("\nExample outputs:")
        for verdict in verdicts[:3]:
            print(f"\nGame: {verdict['name']}")
            print(f"Score: {verdict['score']}")
            print(f"Tags: {' '.join([f'({tag})' for tag in verdict['tags']])}")
            print(f"Verdict preview: {verdict['verdict'][:200]}...")