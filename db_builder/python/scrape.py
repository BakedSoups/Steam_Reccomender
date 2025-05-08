from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import json
import re
import time
from concurrent.futures import ThreadPoolExecutor
import requests
from bs4 import BeautifulSoup

def clean_title(raw_title):
    """Extract clean game title from raw text"""
    title = ' '.join(raw_title.split())
    title = re.sub(r'^\d+\s*', '', title)
    title = re.sub(r'\s*Review.*$', '', title, flags=re.I)
    title = re.sub(r'\s*-\s*.*$', '', title)
    title = re.sub(r'[A-Z]{2,}.*$', '', title)
    return title.strip()

def fetch_article_content(url):
    """Fetch article HTML content"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
        
        content_selectors = [
            'div.article-content',
            'div.content-page',
            'article',
            'main',
            'div[class*="article"]'
        ]
        
        for selector in content_selectors:
            content = soup.select_one(selector)
            if content:
                return str(content)
        
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

def scrape_ign_all_games(url, max_scrolls=30):
    """Scrape ALL games from IGN using Selenium with infinite scrolling"""
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    driver = webdriver.Chrome(options=options)
    games = []
    seen_urls = set()
    
    try:
        driver.get(url)
        print("Page loaded. Waiting for content...")
        
        wait = WebDriverWait(driver, 10)
        time.sleep(3)
        
        scroll_count = 0
        no_new_elements_count = 0
        last_element_count = 0
        
        game_selectors = [
            "a[href*='/articles/'][href*='review']",
            ".content-item a[href*='/articles/']",
            "article a[href*='/articles/']",
            "[class*='item'] a[href*='/articles/']",
            "[class*='card'] a[href*='/articles/']",
            "div[class*='content'] a[href*='/articles/']",
            "[data-cy*='item'] a[href*='/articles/']"
        ]
        
        while scroll_count < max_scrolls and no_new_elements_count < 3:
            current_elements_found = 0
            
            for selector in game_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    for elem in elements:
                        try:
                            game_url = elem.get_attribute('href')
                            if not game_url or game_url in seen_urls:
                                continue
                            
                            if 'review' not in game_url and 'articles' not in game_url:
                                continue
                            
                            parent = elem
                            try:
                                parent = elem.find_element(By.XPATH, 
                                    "./ancestor::*[contains(@class, 'item') or contains(@class, 'card') or contains(@class, 'content')][1]")
                            except:
                                pass
                            
                            title_elem = None
                            title_selectors = ["h1", "h2", "h3", "h4", ".title", "[class*='title']"]
                            for t_selector in title_selectors:
                                try:
                                    title_elem = parent.find_element(By.CSS_SELECTOR, t_selector)
                                    if title_elem and title_elem.text.strip():
                                        break
                                except:
                                    continue
                            
                            if not title_elem:
                                continue
                            
                            raw_title = title_elem.text.strip()
                            clean_game_title = clean_title(raw_title)
                            
                            if not clean_game_title:
                                continue
                            
                            if not game_url.startswith('http'):
                                game_url = f"https://www.ign.com{game_url}"
                            
                            score = 'N/A'
                            score_selectors = [
                                "[class*='score']",
                                "[class*='rating']",
                                ".score",
                                ".rating",
                                "[data-cy*='score']"
                            ]
                            
                            for s_selector in score_selectors:
                                try:
                                    score_elem = parent.find_element(By.CSS_SELECTOR, s_selector)
                                    score_text = score_elem.text.strip()
                                    score_match = re.search(r'(\d+(?:\.\d+)?)', score_text)
                                    if score_match:
                                        score = score_match.group(1)
                                        break
                                except:
                                    continue
                            
                            
                            games.append({
                                'name': clean_game_title,
                                'game_url': game_url,
                                'score': score,
                                'html_contents': ''
                            })
                            
                            seen_urls.add(game_url)
                            current_elements_found += 1
                            print(f"Found game #{len(games)}: {clean_game_title} (Score: {score})")
                            
                        except Exception as e:
                            continue
                    
                except Exception as e:
                    continue
            
            if len(games) == last_element_count:
                no_new_elements_count += 1
                print(f"No new elements found (attempt {no_new_elements_count}/3)")
            else:
                no_new_elements_count = 0
                print(f"Total games found so far: {len(games)}")
            
            last_element_count = len(games)
            
            # scroll down in the page 
            print(f"Scrolling... (scroll {scroll_count + 1}/{max_scrolls})")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)  # Wait for content to load
            
            scroll_count += 1
            
            try:
                load_more_button = driver.find_element(By.XPATH, 
                    "//button[contains(text(), 'Load More')] | //button[contains(text(), 'Show More')] | //a[contains(text(), 'Load More')]")
                if load_more_button.is_displayed():
                    load_more_button.click()
                    print("Clicked 'Load More' button")
                    time.sleep(3)
            except:
                pass
        
        print(f"\nScrolling complete. Found {len(games)} unique games total.")
        
    except Exception as e:
        print(f"Error during Selenium scraping: {e}")
    finally:
        try:
            with open('selenium_debug.html', 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            print("Page source saved to 'selenium_debug.html'")
        except:
            pass
        driver.quit()
    
    if games:
        print(f"\nFetching article contents for {len(games)} games...")
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(fetch_article_content, game['game_url']) for game in games]
            
            for i, future in enumerate(futures):
                try:
                    games[i]['html_contents'] = future.result()
                    print(f"Fetched {i+1}/{len(games)}: {games[i]['name']}")
                except Exception as e:
                    games[i]['html_contents'] = f"Error: {str(e)}"
                    print(f"Error fetching {games[i]['name']}: {str(e)}")
    
    return games

def save_to_json(data, filename='ign_all_games.json'):
    """Save the scraped data to a JSON file"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"Data saved to {filename}")

if __name__ == "__main__":
    url = "https://www.ign.com/reviews/games/pc"
    
    print("Starting complete IGN scraper...")
    print("This will scroll through ALL available games on the page.")
    print("This may take several minutes...\n")
    
    games = scrape_ign_all_games(url, max_scrolls=30)
    
    if games:
        save_to_json(games)
        print(f"\nSuccessfully scraped {len(games)} games")
        
        print("\nSummary:")
        print(f"Total games: {len(games)}")
        print(f"Games with scores: {len([g for g in games if g['score'] != 'N/A'])}")
        print(f"Games without scores: {len([g for g in games if g['score'] == 'N/A'])}")
        
        with open('ign_scraping_summary.txt', 'w', encoding='utf-8') as f:
            f.write(f"IGN PC Games Scraping Summary\n")
            f.write(f"============================\n\n")
            f.write(f"Total games scraped: {len(games)}\n")
            f.write(f"Games with scores: {len([g for g in games if g['score'] != 'N/A'])}\n")
            f.write(f"Games without scores: {len([g for g in games if g['score'] == 'N/A'])}\n\n")
            f.write("Games list:\n")
            f.write("-----------\n")
            for i, game in enumerate(games, 1):
                f.write(f"{i}. {game['name']} (Score: {game['score']})\n")
    else:
        print("No games were scraped")
        print("Check 'selenium_debug.html' for the page structure")