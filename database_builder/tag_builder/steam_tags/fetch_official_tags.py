import ijson

def process_chunk(chunk):
    for record in chunk:
        print(record['name'])  # Or do your real processing here

chunk_size = 20
chunk = []

with open('steam_games_sample_with_reviews.json', 'r') as f:
    objects = ijson.items(f, 'item')  # Stream each object in the top-level list

    for obj in objects:
        chunk.append(obj)
        if len(chunk) == chunk_size:
            process_chunk(chunk)
            chunk = []

    # Process any remaining records
    if chunk:
        process_chunk(chunk)
