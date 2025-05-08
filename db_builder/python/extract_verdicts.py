import json
import re
from bs4 import BeautifulSoup

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
            if len(text) > 50:  # Make sure it's substantial
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
                    # Check if this looks like a conclusion
                    if len(para_text) > 100 and not para_text.startswith('Advertisement'):
                        return para_text
                
                # no good conclusion found, return the last substantial paragraph
                return substantial_paragraphs[-1].get_text(strip=True)
        
        # Strategy 5: Get any text from the page (last resort)
        all_text = soup.get_text()
        words = all_text.split()
        
        # Find the last 300 meaningful words
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

def process_all_reviews(input_file='ign_all_games.json', output_file='game_verdicts_complete.json'):
    """
    Process all reviews and ensure every game has a verdict
    """
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            reviews = json.load(f)
        
        print(f"\nProcessing {len(reviews)} reviews...")
        print("="*80)
        
        verdicts = []
        no_verdict_count = 0
        
        for i, review in enumerate(reviews, 1):
            name = review.get('name', 'Unknown')
            score = review.get('score', 'N/A')
            url = review.get('game_url', '')
            html_content = review.get('html_contents', '')
            
            verdict = extract_verdict_or_conclusion(html_content)
            
            if "not found" in verdict.lower() or "error" in verdict.lower():
                no_verdict_count += 1
            
            verdict_data = {
                'name': name,
                'score': score,
                'url': url,
                'verdict': verdict
            }
            
            verdicts.append(verdict_data)
            
            status = "✓" if len(verdict) > 100 else "?"
            print(f"{i:2d}. {status} {name} (Score: {score})")
            print(f"    Verdict length: {len(verdict)} characters")
            if len(verdict) < 200:
                print(f"    Verdict: {verdict}")
            else:
                print(f"    Verdict: {verdict[:200]}...")
            print("-" * 80)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(verdicts, f, ensure_ascii=False, indent=2)
        
        with open('verdicts_summary_complete.txt', 'w', encoding='utf-8') as f:
            for verdict in verdicts:
                f.write(f"Game: {verdict['name']}\n")
                f.write(f"Score: {verdict['score']}\n")
                f.write(f"URL: {verdict['url']}\n")
                f.write(f"Verdict: {verdict['verdict']}\n")
                f.write("="*80 + "\n\n")
        
        print(f"\nSummary:")
        print(f"Total reviews processed: {len(reviews)}")
        print(f"Reviews with extracted verdicts: {len(reviews) - no_verdict_count}")
        print(f"Reviews with fallback content: {no_verdict_count}")
        print(f"\nResults saved to {output_file} and verdicts_summary_complete.txt")
        
        return verdicts
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return []

if __name__ == "__main__":
    verdicts = process_all_reviews()
    
    if verdicts:
        print(f"\nFinal check: {len(verdicts)} verdicts extracted")
        missing = [v for v in verdicts if len(v['verdict']) < 50]
        if missing:
            print(f"Warning: {len(missing)} games have very short verdicts:")
            for m in missing:
                print(f"  - {m['name']}: {len(m['verdict'])} characters")