import os 
import json
import time
from typing import List, Dict, Any
from dotenv import load_dotenv
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi, NoTranscriptFound, TranscriptsDisabled

def load_videos_from_json(filename: str) -> List[Dict[str, Any]]:
    """Load videos from a JSON file."""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
           return json.load(f)
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return []

def get_video_details(service, video_id: str, max_retries: int = 5) -> Dict[str, Any]:
    """Get additional video details including tags and topic categories."""
    retries = 0
    while retries <= max_retries:
        try:
            response = service.videos().list(
                part="snippet,topicDetails",
                id=video_id
            ).execute()
            
            if 'items' in response and len(response['items']) > 0:
                tags = response['items'][0]['snippet'].get('tags', [])
                
                # Get topic categories if available
                topics = {}
                if 'topicDetails' in response['items'][0] and 'topicCategories' in response['items'][0]['topicDetails']:
                    topics = {url.split('/')[-1]: url for url in response['items'][0]['topicDetails']['topicCategories']}
                
                return {
                    'tags': tags,
                    'topics': topics
                }
            else:
                return {'tags': [], 'topics': {}}
        except Exception as e:
            error_message = str(e).lower()
            # Check for YouTube API limiting messages
            if "quota" in error_message or "rate limit" in error_message or "403" in error_message or "unable to respond" in error_message:
                retries += 1
                wait_time = 10  # Wait 10 seconds before retrying as requested
                print(f"YouTube API limiting detected. Waiting {wait_time} seconds before retrying... (Attempt {retries}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"Error getting video details for {video_id}: {e}")
                return {'tags': [], 'topics': {}}
    
    print(f"Max retries reached for video {video_id} after API limiting")
    return {'tags': [], 'topics': {}}

def get_transcript(video_id: str, max_retries: int = 5) -> str:
    """Get the transcript for a video."""
    retries = 0
    while retries <= max_retries:
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
            return "".join(line['text'] + " " for line in transcript_list)
        except (NoTranscriptFound, TranscriptsDisabled) as e:
            print(f"No transcript available for {video_id}: {e}")
            return ""
        except Exception as e:
            error_message = str(e).lower()
            if "quota" in error_message or "rate limit" in error_message or "403" in error_message or "unable to respond" in error_message:
                retries += 1
                wait_time = 10  # Wait 10 seconds before retrying as requested
                print(f"YouTube API limiting detected. Waiting {wait_time} seconds before retrying... (Attempt {retries}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"Error getting transcript for {video_id}: {e}")
                return ""
    
    print(f"Max retries reached for transcript {video_id} after API limiting")
    return ""

def enrich_videos(service, videos: List[Dict[str, Any]], include_transcript: bool = True, output_file: str = None, batch_size: int = 50) -> List[Dict[str, Any]]:
    """Enrich video data with tags, topics, and transcripts."""
    enriched_videos = []
    total_videos = len(videos)
    
    # Process videos in batches
    batches = (total_videos + batch_size - 1) // batch_size
    
    for batch_num in range(batches):
        start_idx = batch_num * batch_size
        end_idx = min((batch_num + 1) * batch_size, total_videos)
        batch_videos = videos[start_idx:end_idx]
        
        print(f"Processing batch {batch_num + 1}/{batches} ({start_idx+1}-{end_idx} of {total_videos} videos)")
        
        batch_enriched = []
        for i, video in enumerate(batch_videos, 1):
            print(f"  Processing video {start_idx+i}/{total_videos}: {video['title']}")
            
            # Get tags and topics
            details = get_video_details(service, video['video_id'])
            
            # Get transcript if requested
            transcript = ""
            if include_transcript:
                print(f"    Fetching transcript...")
                transcript = get_transcript(video['video_id'])
                if transcript:
                    print(f"    Transcript fetched: {len(transcript)} characters")
                else:
                    print(f"    No transcript available")
            
            # Create enriched video data
            enriched_video = {
                "name": video['title'],
                "score": 0,  # Default score as requested in the format
                "url": video['url'],
                "tags": details['tags'],
                "topics": details['topics'],
                "transcript": transcript
            }
            
            batch_enriched.append(enriched_video)
            
            # Add a small delay to avoid rate limiting
            time.sleep(1)
        
        # Add all enriched videos from this batch to our master list
        enriched_videos.extend(batch_enriched)
        
        # If an output file is specified, save this batch immediately
        if output_file:
            # For proper JSON array format, we need to:
            # 1. Read existing data if not the first batch
            # 2. Add our new batch
            # 3. Write everything back as a proper JSON array
            
            if batch_num == 0:
                # First batch - create new file with opening bracket
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write('[\n')  # Start JSON array
                    # Write batch items with commas between them
                    for i, video in enumerate(batch_enriched):
                        json.dump(video, f, ensure_ascii=False, indent=2)
                        if i < len(batch_enriched) - 1 or end_idx < total_videos:
                            f.write(',\n')  # Add comma if not the last item
                        else:
                            f.write('\n')  # No comma for last item
                    
                    # If this is the only batch, close the array
                    if end_idx >= total_videos:
                        f.write(']\n')
            else:
                # For subsequent batches, we need to:
                # 1. Remove the closing bracket from the file
                # 2. Add a comma after the last item if needed
                # 3. Append our new batch
                # 4. Add the closing bracket
                
                # First, read the current file content
                with open(output_file, 'r', encoding='utf-8') as f:
                    content = f.read().rstrip()
                
                # Remove closing bracket if it's there
                if content.endswith(']'):
                    content = content[:-1].rstrip()
                
                # Rewrite the file
                with open(output_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                    
                    # Add comma if the last character isn't already a comma
                    if not content.endswith(','):
                        f.write(',\n')
                    
                    # Write batch items
                    for i, video in enumerate(batch_enriched):
                        json.dump(video, f, ensure_ascii=False, indent=2)
                        if i < len(batch_enriched) - 1 or end_idx < total_videos:
                            f.write(',\n')  # Add comma if not the last item
                        else:
                            f.write('\n')  # No comma for last item
                    
                    # If this is the last batch, close the array
                    if end_idx >= total_videos:
                        f.write(']\n')
        
        print(f"Completed batch {batch_num + 1}/{batches}")
    
    return enriched_videos

def main():
    # Load API key from environment variables
    load_dotenv()
    api_key = os.getenv("YT_API_KEY")
    
    if not api_key:
        print("Error: YouTube API key not found. Please set YT_API_KEY environment variable.")
        return
    
    # Build YouTube API service
    youtube = build('youtube', 'v3', developerKey=api_key)
    
    # Ask for input file
    input_file = "gameranxTV_before_you_buy_videos.json"
    if not os.path.exists(input_file):
        print(f"Error: File {input_file} not found.")
        return
    
    # Load videos from JSON
    videos = load_videos_from_json(input_file)
    if not videos:
        print("No videos found in the input file.")
        return
    
    print(f"Loaded {len(videos)} videos from {input_file}")
    
    # Ask if transcript should be included
    include_transcript = input("Include transcripts? (y/n, default: y): ").lower().strip() != 'n'
    
    # Get batch size
    batch_size = 50
    try:
        batch_input = input(f"Enter batch size (default: {batch_size}): ").strip()
        if batch_input:
            batch_size = int(batch_input)
    except ValueError:
        print(f"Invalid batch size, using default: {batch_size}")
    
    # Determine output file
    default_output = input_file.replace('.json', '_enriched.json')
    output_file = input(f"Enter output filename (default: {default_output}): ").strip() or default_output
    
    # Clear output file if it exists
    if os.path.exists(output_file):
        print(f"Warning: {output_file} already exists. It will be overwritten.")
        try:
            os.remove(output_file)
            print(f"Deleted existing file: {output_file}")
        except Exception as e:
            print(f"Error deleting existing file: {e}")
    
    # Process videos in batches and save directly to the output file
    enriched_videos = enrich_videos(
        service=youtube, 
        videos=videos, 
        include_transcript=include_transcript,
        output_file=output_file,
        batch_size=batch_size
    )
    
    print(f"Processing complete. All {len(enriched_videos)} videos have been enriched and saved to {output_file}")
    
if __name__ == "__main__":
    main()