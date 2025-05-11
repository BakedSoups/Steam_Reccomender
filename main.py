import random
import copy

BATTLEFIELD_2042 = {
    "detail_id": 68,
    "steam_appid": 1517290,
    "name": "Battlefield™ 2042",
    "description": "Battlefield™ 2042 is a first-person shooter that marks the return to the iconic all-out warfare of the franchise.",
    "website": "https://www.ea.com/games/battlefield/battlefield-2042/",
    "header_image": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1517290/header.jpg?t=1744718390",
    "background": "https://store.akamai.steamstatic.com/images/storepagebackground/app/1517290?t=1744718390",
    "screenshot": "https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/1517290/a0c5c62e72cafdddb10c4175c1cba00cba0b0fb1/ss_a0c5c62e72cafdddb10c4175c1cba00cba0b0fb1.1920x1080.jpg?t=1744718390",
    "steam_url": "https://store.steampowered.com/app/1517290",
    "pricing": "A$ 7.19",
    "achievements": "34 achievements",
    "score": "8.5/10",
    "main_genre": "FPS",
    "tag_ratios": {"fps": 40, "multiplayer": 35, "action": 25},
    "unique_tags": ["large-scale-battles", "vehicles", "destruction"],
    "verdict": "A return to form for the Battlefield franchise, offering massive battles with cutting-edge graphics and gameplay."
}

def generate_variants(base_game, num_variants=5):
    game_list = []

    for i in range(num_variants):
        game = copy.deepcopy(base_game)
        game["detail_id"] += i + 1
        game["steam_appid"] += i + 1
        game["name"] = f"{base_game['name']} Variant {i+1}"
        game["pricing"] = f"A$ {round(5 + random.uniform(1, 10), 2)}"
        game["score"] = f"{round(random.uniform(6.0, 9.5), 1)}/10"
        
        # Slightly shuffle tag ratios
        fps = random.randint(30, 50)
        multiplayer = random.randint(20, 40)
        action = 100 - (fps + multiplayer)
        action = max(0, action)
        game["tag_ratios"] = {
            "fps": fps,
            "multiplayer": multiplayer,
            "action": action
        }

        game_list.append(game)

    return game_list

game_variants = generate_variants(BATTLEFIELD_2042, num_variants=5)

for game in game_variants:
    print(game)
    print("\n" + "-"*80 + "\n")
