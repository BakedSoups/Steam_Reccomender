
# File: app.py
from flask import Flask, render_template, request

app = Flask(__name__)

# Sample game data (duplicated Battlefield 2042 example)
GAMES = [
    {
        "detail_id": 68,
        "steam_appid": 1517290,
        "name": "Battlefield™ 2042",
        "description": "Battlefield™ 2042 is a first-person shooter that marks the return to the iconic all-out warfare of the franchise.",
        "website": "https://www.ea.com/games/battlefield/battlefield-2042/",
        "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1517290/header.jpg?t=1744718390",
        "background": "https://store.akamai.steamstatic.com/images/storepagebackground/app/1517290?t=1744718390",
        "screenshot": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1517290/a0c5c62e72cafdddb10c4175c1cba00cba0b0fb1/ss_a0c5c62e72cafdddb10c4175c1cba00cba0b0fb1.1920x1080.jpg?t=1744718390",
        "steam_url": "https://store.steampowered.com/app/1517290",
        "pricing": "$59.99",
        "discount": "75%",
        "final_price": "$14.99",
        "achievements": "34 achievements",
        "score": "8.5/10",
        "main_genre": "FPS",
        "tag_ratios": {"fps": 40, "multiplayer": 35, "action": 25},
        "unique_tags": ["large-scale-battles", "vehicles", "destruction"],
        "verdict": "A return to form for the Battlefield franchise, offering massive battles with cutting-edge graphics and gameplay.",
        "release_date": "May 16, 2011",
        "publisher": "EA Games",
        "overall_review": 30000,
        "positive_reviews": 18000,
        "negative_reviews": 12000
    }
] * 5  # Duplicate the game 5 times

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    return render_template('results.html', games=GAMES)

if __name__ == '__main__':
    app.run(debug=True)