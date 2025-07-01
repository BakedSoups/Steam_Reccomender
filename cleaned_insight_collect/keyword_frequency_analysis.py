import re
def has_ascii_art(text):
    # Remove whitespace for analysis
    text_no_spaces = re.sub(r'\s', '', text)
    
    if len(text_no_spaces) > 0:
        non_alnum_ratio = len(re.sub(r'[a-zA-Z0-9]', '', text_no_spaces)) / len(text_no_spaces)
        if non_alnum_ratio > 0.3:  # More than 30% non-alphanumeric
            return True
    
    # Check for repeated patterns that suggest ASCII art
    ascii_art_patterns = [
        r'[▀▄█▌▐░▒▓]',  # Block characters
        r'[^\w\s]{10,}',  # 10+ consecutive non-word characters
        r'(\S)\1{5,}',  # Same character repeated 6+ times
    ]
    
    for pattern in ascii_art_patterns:
        if re.search(pattern, text, re.MULTILINE):
            return True
    
    return False


def count_review_keywords(review_text) -> int:
    # Define categories of relevant keywords
    keywords = {
        # Gameplay related
        'gameplay': ['gameplay', 'game play', 'mechanics', 'controls', 'difficulty',],
        'graphics': ['graphics', 'visuals', 'art style', 'animation', 'textures', 'fps'],
        'story': ['story', 'plot', 'narrative', 'characters', 'dialogue', 'writing'],
        'audio': ['sound', 'music', 'audio', 'soundtrack', 'voice acting', 'sfx'],
        'performance': ['performance', 'optimization', 'bugs', 'glitches', 'lag', 'framerate'],
        'content': ['content', 'length', 'replay', 'replayability', 'hours', 'campaign'],
        'multiplayer': ['multiplayer', 'online', 'co-op', 'pvp', 'servers', 'matchmaking'],
        'value': ['price', 'worth', 'value', 'money', 'cost', 'expensive', 'cheap'],
        'reviewer':['underated', 'gem']
    }
    
    # Convert to lowercase for case-insensitive matching
    review_lower = review_text.lower()
    
    # Count all keywords
    keyword_counts = {}
    total_keywords = 0
    
    for category, terms in keywords.items():
        category_count = 0
        for term in terms:
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(term) + r'\b'
            matches = len(re.findall(pattern, review_lower))
            category_count += matches
            total_keywords += matches
        
        if category_count > 0:
            keyword_counts[category] = category_count
    
    # Add total count
    keyword_counts['total_keywords'] = total_keywords
    
    return keyword_counts