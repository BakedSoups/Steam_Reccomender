
from dotenv import load_dotenv
import os
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi

def configure(): 
    load_dotenv()

def main():
    configure()
    servicer = build('youtube', 'v3', developerKey=os.getenv('api_key'))
    
    # Get channel id:
    channel_request = servicer.channels().list(
        part = 'id',
        forHandle = '@gameranxTV')
    channel_response = channel_request.execute()
    channel_id = channel_response['items'][0]['id']
    
    # Get ids for channel videos:
    MAX_VIDEOS = 2
    video_request = servicer.search().list(
        part = 'snippet',
        channelId = channel_id,
        type = 'video',
        videoCaption = 'closedCaption',
        maxResults = MAX_VIDEOS)
    video_response = video_request.execute()
    videos = {item['id']['videoId']: item['snippet']['title'] for item in video_response['items']}
    
    # Save to files:
    ytt_api = YouTubeTranscriptApi()
    for vid, name in videos.items():
        with open(f"transcripts/{"_".join(word for word in name.split())}.txt", 'w') as f:
            for line in ytt_api.get_transcript(vid):
                f.write(f"{line['text']}\n")
main()