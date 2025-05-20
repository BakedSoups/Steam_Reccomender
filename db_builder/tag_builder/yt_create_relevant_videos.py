#!/usr/bin/env python3
# ACGTagGenerator v1.0.1
# Fetches ACG reviews and generates gameplay tags and ratios for game recommendation

import os
import json
import re
import time
import logging
from typing import List, Dict, Tuple, Set, Any
from dotenv import load_dotenv
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled
from openai import OpenAI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("acg_tagger.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("ACGTagger")

client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

TAG_CONTEXT = {
    'ratio_tags': set(),
    'unique_tags': set(),
    'subjective_tags': set(),
    'main_genres': set()
}

def get_channel_info(service, channel_handle: str) -> Dict[str, str]:
    response = service.channels().list(
        part='id,contentDetails',
        forHandle=channel_handle
    ).execute()
    
    if 'items' in response and len(response['items']) > 0:
        channel_id = response['items'][0]['id']
        uploads_playlist_id = response['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        return {'channel_id': channel_id, 'uploads_playlist_id': uploads_playlist_id}
    else:
        raise ValueError(f"Channel with handle {channel_handle} not found")

def get_all_videos(service, uploads_playlist_id: str, search_term: str = None, max_results: int = None) -> List[Dict[str, Any]]:
    """
    Get all videos from a channel's uploads playlist, optionally filtering by a search term in the title.
    
    Args:
        service: YouTube API service object
        uploads_playlist_id: The ID of the channel's uploads playlist
        search_term: Optional term to filter video titles (case-insensitive)
        max_results: Maximum number of videos to return (None for all)
    
    Returns:
        List of video information dictionaries
    """
    videos = []
    next_page_token = None
    results_per_page = 50  # Maximum allowed by the API
    total_fetched = 0
    page_count = 0
    max_pages = 100  # Set a higher limit since we're looking for all videos
    
    logger.info("Fetching videos from channel's uploads, this may take a while...")
    
    while True:
        page_count += 1
        logger.info(f"Fetching page {page_count}...")
        
        try:
            request = service.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=uploads_playlist_id,
                maxResults=results_per_page,
                pageToken=next_page_token
            )
            response = request.execute()
            
            items_count = len(response.get('items', []))
            total_fetched += items_count
            logger.info(f"Got {items_count} videos")
            
            for item in response.get('items', []):
                title = item['snippet']['title']
                
                if search_term is None or search_term.lower() in title.lower():
                    video_info = {
                        'title': title,
                        'video_id': item['contentDetails']['videoId'],
                        'url': f"https://www.youtube.com/watch?v={item['contentDetails']['videoId']}",
                        'published_at': item['snippet']['publishedAt'],
                        'description': item['snippet']['description'],
                        'thumbnail': item['snippet']['thumbnails']['high']['url'] if 'thumbnails' in item['snippet'] else None
                    }
                    videos.append(video_info)
                    
                    if len(videos) % 10 == 0:
                        logger.info(f"Found {len(videos)} matching videos so far...")
            
            next_page_token = response.get('nextPageToken')
            
            if not next_page_token:
                logger.info("No more pages available.")
                break
                
            if max_results and len(videos) >= max_results:
                logger.info(f"Reached requested maximum of {max_results} matching videos.")
                break
                
            if page_count >= max_pages:
                logger.info(f"Reached maximum page limit of {max_pages}.")
                break
                
            time.sleep(0.3)
            
        except Exception as e:
            logger.error(f"Error fetching page {page_count}: {e}")
            break
    
    if max_results and len(videos) > max_results:
        videos = videos[:max_results]
        
    logger.info(f"Total: Fetched {total_fetched} videos across {page_count} pages, found {len(videos)} matching videos")
    return videos

def extract_game_name_from_title(title: str) -> str:
    """Extract the game name from ACG Review video title."""
    patterns = [
        r'(.*?)\s+Review\s+\"Buy,\s+Wait',  # Matches "Game Name Review "Buy, Wait
        r'(.*?)\s+Review:',                 # Matches "Game Name Review:"
        r'(.*?)\s+Review\s+\-',             # Matches "Game Name Review -"
        r'(.*?)\s+Review\s+\|',             # Matches "Game Name Review |"
        r'(.*?)\s+Review$',                 # Matches "Game Name Review" at end of string
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            game_name = match.group(1).strip()
            game_name = re.sub(r'^\[.*?\]\s*', '', game_name)  # Remove [tags]
            game_name = re.sub(r'\s*\(.*?\)$', '', game_name)  # Remove (notes) at end
            return game_name.strip()
    
    cleaned_title = re.sub(r'review|\"buy|wait for sale|never touch', '', title, flags=re.IGNORECASE)
    return cleaned_title.strip()

def extract_rating_from_title(title: str) -> str:
    """Extract ACG's rating from the video title."""
    rating_patterns = [
        r'\"(Buy)(?:,|\.|\?|\")',
        r'\"(Wait for Sale)(?:,|\.|\?|\")',
        r'\"(Deep Sale)(?:,|\.|\?|\")',
        r'\"(Never Touch)(?:,|\.|\?|\")'
    ]
    
    for pattern in rating_patterns:
        match = re.search(pattern, title, re.IGNORECASE)
        if match:
            return match.group(1)
    
    full_pattern = r'\"(Buy,\s+Wait for Sale,\s+Deep Sale,\s+Never Touch\??)'
    match = re.search(full_pattern, title, re.IGNORECASE)
    if match:
        if '"Buy' in title:
            return "Buy"
        elif '"Wait for Sale' in title:
            return "Wait for Sale"
        elif '"Deep Sale' in title:
            return "Deep Sale"
        elif '"Never Touch' in title:
            return "Never Touch"
    
    return "Unknown"

def get_transcript(video_id: str, max_retries: int = 3) -> str:
    retries = 0
    while retries <= max_retries:
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            return "".join(line['text'] + " " for line in transcript_list)
        except (NoTranscriptFound, TranscriptsDisabled) as e:
            logger.warning(f"No transcript available for {video_id}: {e}")
            return ""
        except Exception as e:
            error_message = str(e).lower()
            if "quota" in error_message or "rate limit" in error_message or "403" in error_message or "unable to respond" in error_message:
                retries += 1
                wait_time = 10  # Wait 10 seconds before retrying
                logger.warning(f"YouTube API limiting detected. Waiting {wait_time} seconds before retry... (Attempt {retries}/{max_retries})")
                time.sleep(wait_time)
            else:
                logger.error(f"Error getting transcript for {video_id}: {e}")
                return ""
    
    logger.error(f"Max retries reached for transcript {video_id}")
    return ""

def save_videos_to_json(videos: List[Dict[str, Any]], filename: str):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)
    logger.info(f"Saved {len(videos)} videos to {filename}")

def generate_game_tags_with_ratios(game_name: str, transcript: str, retry_count: int = 0) -> Tuple[Dict[str, int], str, List[str], List[str]]:
    existing_ratio_tags = ', '.join(sorted(TAG_CONTEXT['ratio_tags'])) if TAG_CONTEXT['ratio_tags'] else "None yet"
    existing_unique_tags = ', '.join(sorted(TAG_CONTEXT['unique_tags'])) if TAG_CONTEXT['unique_tags'] else "None yet"
    existing_subjective_tags = ', '.join(sorted(TAG_CONTEXT['subjective_tags'])) if TAG_CONTEXT['subjective_tags'] else "None yet"
    existing_genres = ', '.join(sorted(TAG_CONTEXT['main_genres'])) if TAG_CONTEXT['main_genres'] else "None yet"
    
    system_prompt = f"""You are a game categorization expert. Based on game review transcripts, you analyze games and provide:

1. A percentage breakdown of the game's core OBJECTIVE elements/mechanics (must total 100%)
2. The main genre classification
3. Unique searchable tags that distinguish this game within its genre (2-4 tags)
4. Subjective tags that capture the reviewer's opinion (2-4 tags)

IMPORTANT RULES FOR CREATING RATIO TAGS (element percentages):
- Focus on actual gameplay elements and mechanics (combat:40%, exploration:30%, puzzle-solving:30%)
- Use descriptive mechanics rather than generic categories (use "deck-building:20%" rather than "cards:20%")
- Capture the game's core systems, not qualities (use "stealth:40%" not "difficulty:40%")
- Ratios should help people find similar games by mechanics, not by quality
- If a negative element is an INTENTIONAL part of the game design (not a flaw), include it (e.g., "permadeath:20%")

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
  * "roguelike" (not "rogue-like" or "rogue-lite")
  * "deck-building" (not "card-building")
  * "base-building" (not "construction")

EXAMPLE RATIO TAGS FOR DIFFERENT GAMES:
- For an action RPG: combat:40% exploration:30% character-progression:30%
- For a puzzle game: puzzle-solving:70% story:20% exploration:10%
- For a survival game: resource-management:40% crafting:30% combat:20% exploration:10%
- For a strategy game: tactical-combat:50% resource-management:30% diplomacy:20%
- For a racing game: racing:70% vehicle-customization:20% progression:10%

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
RATIOS: turn-based-combat:40% social-sim:40% exploration:20%
MAIN_GENRE: JRPG
UNIQUE_TAGS: jazz-soundtrack, calendar-system, persona-fusion
SUBJECTIVE_TAGS: stylish-presentation, addictive-gameplay, deep-story"""
    
    max_transcript_length = 1500
    if len(transcript) > max_transcript_length:
        transcript = transcript[:max_transcript_length] + "..."
    
    user_prompt = f"""Game: {game_name}
Transcript from ACG review video:

{transcript}

Analyze this game and provide:
1. A percentage breakdown of its core OBJECTIVE gameplay elements and mechanics (must total 100%)
2. Its main genre classification  
3. Unique searchable tags that distinguish it within its genre (2-4 tags, objective only)
4. Subjective tags that capture the reviewer's opinion (2-4 tags, can include quality assessments)

IMPORTANT: For ratio tags, focus on actual gameplay mechanics and systems that would help people find similar games."""
    
    try:
        logger.info(f"Generating tags for: {game_name}")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3,
            max_tokens=200
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
            TAG_CONTEXT['main_genres'].add(main_genre.lower())
        
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
            logger.warning(f"Could not parse ratios for {game_name}, using fallback")
            tag_ratios = {"general": 100}
        
        logger.info(f"Successfully generated tags for: {game_name}")
        return tag_ratios, main_genre, unique_tags, subjective_tags
        
    except Exception as e:
        error_str = str(e)
        
        if "insufficient_quota" in error_str:
            logger.error(f"API quota exceeded for {game_name}")
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
                logger.warning(f"Rate limit hit for {game_name}. Waiting {wait_time} seconds before retry {retry_count + 1}/3")
                time.sleep(wait_time + 0.5)  
                return generate_game_tags_with_ratios(game_name, transcript, retry_count + 1)
            else:
                logger.error(f"Rate limit persists for {game_name} after 3 retries")
                return {"rate-limited": 100}, "RATE_LIMITED", ["rate-limit-exceeded"], ["rate-limited"]
        
        else:
            logger.error(f"Error generating tags for {game_name}: {error_str}")
            return {"error": 100}, "ERROR", ["unknown-error"], ["error"]

def save_tag_context(filename='acg_tag_context.json'):
    context_to_save = {
        'ratio_tags': list(TAG_CONTEXT['ratio_tags']),
        'unique_tags': list(TAG_CONTEXT['unique_tags']),
        'subjective_tags': list(TAG_CONTEXT['subjective_tags']),
        'main_genres': list(TAG_CONTEXT['main_genres'])
    }
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(context_to_save, f, ensure_ascii=False, indent=2)
    logger.info(f"Tag context saved to {filename}")

def load_tag_context(filename='acg_tag_context.json'):
    global TAG_CONTEXT
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            saved_context = json.load(f)
            TAG_CONTEXT['ratio_tags'] = set(saved_context.get('ratio_tags', []))
            TAG_CONTEXT['unique_tags'] = set(saved_context.get('unique_tags', []))
            TAG_CONTEXT['subjective_tags'] = set(saved_context.get('subjective_tags', []))
            TAG_CONTEXT['main_genres'] = set(saved_context.get('main_genres', []))
        logger.info(f"Loaded tag context from {filename}")
    except FileNotFoundError:
        logger.info("No existing tag context found, starting fresh")

def save_checkpoint(processed_games, filename='acg_checkpoint.json'):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(processed_games, f, ensure_ascii=False, indent=2)
    logger.info(f"Checkpoint saved: {len(processed_games)} games processed")

def load_checkpoint(filename='acg_checkpoint.json'):
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            checkpoint_data = json.load(f)
        logger.info(f"Loaded checkpoint with {len(checkpoint_data)} previously processed games")
        return checkpoint_data
    except FileNotFoundError:
        logger.info("No checkpoint found, starting from scratch")
        return []

def process_with_transcripts(videos, youtube, chunk_size=10):
    load_tag_context()
    processed_games = load_checkpoint()
    processed_names = {g['name'].lower() for g in processed_games}
    
    logger.info(f"Starting to process {len(videos)} videos...")
    
    remaining_videos = []
    for video in videos:
        game_name = extract_game_name_from_title(video['title'])
        if game_name.lower() not in processed_names:
            remaining_videos.append(video)
    
    logger.info(f"Already processed: {len(processed_games)}")
    logger.info(f"Remaining to process: {len(remaining_videos)}")
    
    for i, video in enumerate(remaining_videos, 1):
        video_id = video['video_id']
        title = video['title']
        game_name = extract_game_name_from_title(title)
        
        logger.info(f"Processing {i}/{len(remaining_videos)}: {game_name}")
        
        acg_rating = extract_rating_from_title(title)
        
        logger.info(f"  Fetching transcript for {video_id}...")
        transcript = get_transcript(video_id)
        
        if not transcript or len(transcript) < 100:
            logger.warning(f"  No/insufficient transcript for {game_name}")
            continue
            
        logger.info(f"  Got transcript: {len(transcript)} characters")
        
        tag_ratios, main_genre, unique_tags, subjective_tags = generate_game_tags_with_ratios(game_name, transcript)
        
        game_data = {
            'name': game_name,
            'video_title': title,
            'url': video['url'],
            'acg_rating': acg_rating,
            'published_at': video['published_at'],
            'tag_ratios': tag_ratios,
            'main_genre': main_genre,
            'unique_tags': unique_tags,
            'subjective_tags': subjective_tags
        }
        
        processed_games.append(game_data)
        
        logger.info(f"  ACG Rating: {acg_rating}")
        logger.info(f"  Main Genre: {main_genre}")
        logger.info(f"  Unique Tags: {', '.join(unique_tags)}")
        logger.info(f"  Subjective Tags: {', '.join(subjective_tags)}")
        logger.info(f"  Breakdown: {' '.join([f'{tag}:{percent}%' for tag, percent in tag_ratios.items()])}")
        
        if i % chunk_size == 0:
            save_checkpoint(processed_games)
            save_tag_context()
            logger.info(f"Reached checkpoint at {i} games")
            time.sleep(1)  # Brief pause between chunks
    
    output_file = 'acg_ratio_tags.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(processed_games, f, ensure_ascii=False, indent=2)
    
    logger.info("="*40)
    logger.info(f"Summary:")
    logger.info(f"Total games processed: {len(processed_games)}")
    logger.info(f"Results saved to {output_file}")
    
    if os.path.exists('acg_checkpoint.json'):
        os.remove('acg_checkpoint.json')
        logger.info("Checkpoint file removed after successful completion")
        
    return processed_games

def main():
    banner = """
    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
    ┃                      ACG REVIEW TAG GENERATOR v1.0.1                          ┃
    ┃        Create gameplay mechanic tags and ratios from ACG review videos        ┃
    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛
    """
    print(banner)
    
    load_dotenv()
    yt_api_key = os.getenv("YT_API_KEY")
    openai_api_key = os.getenv("OPENAI_API_KEY")
    
    if not yt_api_key:
        logger.error("YouTube API key not found. Please set YT_API_KEY environment variable.")
        print("Error: YouTube API key not found. Please set YT_API_KEY environment variable.")
        return
        
    if not openai_api_key:
        logger.error("OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        print("Error: OpenAI API key not found. Please set OPENAI_API_KEY environment variable.")
        return
    
    youtube = build('youtube', 'v3', developerKey=yt_api_key)
    
    default_channel = "@ACGreviews"
    channel_handle = input(f"Enter channel handle (default: {default_channel}): ").strip() or default_channel
    
    try:
        channel_info = get_channel_info(youtube, channel_handle)
        logger.info(f"Channel ID: {channel_info['channel_id']}")
        logger.info(f"Uploads Playlist ID: {channel_info['uploads_playlist_id']}")
    except ValueError as e:
        logger.error(f"Error: {e}")
        print(f"Error: {e}")
        return
    
    default_search = "Review"
    search_input = input(f"Search term (default: '{default_search}'): ").strip()
    search_term = search_input if search_input else default_search
    
    try:
        max_results_input = input("Maximum number of videos to process (default: 50, 'all' for all): ").strip()
        if max_results_input.lower() == 'all':
            max_results = None
        else:
            max_results = int(max_results_input) if max_results_input else 50
    except ValueError:
        logger.warning("Invalid input, using default of 50 videos.")
        max_results = 50
    
    videos = get_all_videos(youtube, channel_info['uploads_playlist_id'], search_term, max_results)
    
    videos.sort(key=lambda x: x['published_at'], reverse=True)
    
    if videos:
        print(f"\nFound {len(videos)} videos containing '{search_term}':")
        for i, video in enumerate(videos[:10], 1):  # Show only first 10
            print(f"{i}. {video['title']}")
            print(f"   URL: {video['url']}")
            print()
        
        if len(videos) > 10:
            print(f"...and {len(videos) - 10} more videos.")
            
        process_option = input("Process these videos to generate tags? (y/n): ").lower().strip()
        if process_option == 'y':
            try:
                chunk_size = int(input("Checkpoint frequency (videos per chunk, default: 10): ").strip() or "10")
            except ValueError:
                chunk_size = 10
                print("Invalid input, using default of 10 videos per chunk.")
            
            processed_games = process_with_transcripts(videos, youtube, chunk_size)
            print("\nProcessing complete! Tags have been generated successfully.")
            print("Output file: acg_ratio_tags.json")
        else:
            default_filename = f"{channel_handle.replace('@', '')}_{search_term.replace(' ', '_')[:20]}_videos.json"
            filename_input = input(f"Save raw video list to file? (default: '{default_filename}', 'n' to skip): ")
            
            if filename_input.lower() != 'n':
                filename = filename_input.strip() if filename_input.strip() else default_filename
                save_videos_to_json(videos, filename)
    else:
        logger.warning(f"No videos found containing '{search_term}'")
        print(f"No videos found containing '{search_term}'")

if __name__ == "__main__":
    main()