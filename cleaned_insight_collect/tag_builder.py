import os
import openai

# Ensure your API key is set in the environment
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def create_profile(review, steam_tags):
    prompt = f"""
{review}

Steam Tags: {steam_tags}

Using only the content of the reviews and Steam tags above, generate a structured game profile for vector-based comparison and search.

Ignore any content in the reviews that discusses technical performance (e.g., "runs well on PC", "low frame rate", "crashes"), pricing or sales, platform-specific issues, bugs, customer support, or general meta-commentary about the developer or store.

Only focus on descriptions of the gameplay, story, tone, themes, characters, music, mechanics, progression systems, and overall player experience.

---

First, infer the following metadata fields based strictly on what is described or strongly implied in the reviews and tags:

- **genre**: A single high-level genre (e.g., "RPG", "Action").
- **subgenre**: A single category within that genre (e.g., "JRPG", "Roguelike").
- **sub_subgenre**: A **list** of specific gameplay structure types (e.g., ["Life Simulation", "Dungeon Crawler", "Time Management RPG"]).
- **era**: A **list** of time periods, cultural references, or stylistic aesthetics that describe the game’s world or presentation (e.g., ["Modern", "Early 2000s", "Supernatural"]).
- **setting**: A **list** of locations or thematic environments described in the reviews (e.g., ["Tokyo", "School", "Urban", "Fantasy Realm"]).
- **music**: A **list** of soundtrack styles, moods, or instruments based on how music is described (e.g., ["Energetic", "Melancholic", "Orchestral", "Vocal-heavy", "Ambient"]).

---

Next, generate a structured tag profile grouped into four sections. For each tag, assign a **relevance score from 0.0 to 1.0** based on how strongly it appears in the reviews:

1. **mechanic_tags** – Core gameplay systems (e.g., turn-based combat, character fusion, exploration, crafting).
2. **descriptive_tags** – Aesthetic, emotional, or stylistic traits (e.g., anime-inspired, rebellious tone, minimal UI).
3. **gameplay_tags** – How the player progresses or interacts (e.g., routine-based decision-making, dialogue choice impact, social link progression).
4. **unique_in_genre_tags** – What makes this game distinctive within its genre (e.g., dual-world metaphor, narrative-driven UI, fusion tied to relationships).

Only include the **most meaningful and distinguishing tags**. Avoid generic or low-signal tags unless strongly emphasized.

---

Output the final result as a well-structured JSON object in the following format:

(Example Format — for structure only; do not reuse the values below)

```json
{{
  "meta": {{
    "genre": "Action RPG",
    "subgenre": "Soulslike",
    "sub_subgenre": ["Boss-Focused", "Methodical Combat", "World Interconnection"],
    "era": ["Medieval", "Dark Fantasy"],
    "setting": ["Ruined Kingdom", "Castles", "Graveyards"],
    "music": ["Orchestral", "Melancholic", "Atmospheric"]
  }},
  "mechanic_tags": {{
    "melee_combat": 1.0,
    "stamina_management": 0.9
  }},
  "descriptive_tags": {{
    "high_difficulty": 1.0,
    "dark_tone": 1.0
  }},
  "gameplay_tags": {{
    "boss_progression": 1.0,
    "checkpoint_risk_system": 0.9
  }},
  "unique_in_genre_tags": {{
    "interconnected_world_map": 1.0,
    "nonverbal_storytelling": 0.9
  }}
}}
"""

    response = client.chat.completions.create(
        model="gpt-3.5-turbo-16k",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return response.choices[0].message.content.strip()
