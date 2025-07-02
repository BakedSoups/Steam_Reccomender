import os
import openai

# Create OpenAI client
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

- genre: A single high-level genre (e.g., "RPG", "Action").
- subgenre: A single category within that genre (e.g., "Management", "Puzzle").
- sub_subgenre: A list of specific gameplay structure types (e.g., ["Time Management", "Co-op Multiplayer", "Level-based Progression"]).
- era: A list of time periods, cultural references, or stylistic aesthetics (e.g., ["Modern", "Cartoonish", "Family-Friendly"]).
- setting: A list of in-game locations or environments (e.g., ["Restaurant", "Kitchen", "Fantasy World", "Chaos Scenarios"]).
- music: A list of soundtrack moods or styles (e.g., ["Upbeat", "Stressful", "Relaxing", "Cartoon Orchestra"]).

---

Then, generate a structured tag profile grouped into four sections. For each section, generate 4 to 8 tags, each with a relevance score from 0.0 to 1.0 based on how strongly it appears in the reviews.

1. mechanic_tags – Core gameplay systems and player actions (e.g., time management, item juggling, cooperative roles).
2. descriptive_tags – Aesthetic or emotional traits describing how the game feels (e.g., chaotic energy, colorful style, lighthearted tone).
3. gameplay_tags – How the player interacts with and progresses through the game (e.g., stage-based challenges, time pressure, communication).
4. unique_in_genre_tags – What makes this game stand out within its genre. These can reflect emergent play patterns, creative mechanics, or emotionally distinctive outcomes (e.g., joyful panic, coordination without words, puzzle-like kitchens).

Only include high-signal, specific, and distinctive tags. Avoid vague or generic ones unless clearly emphasized.

---

Output the result as a clean JSON object. Use this fictional example only for structure and depth — do not reuse the content:

{{
  "meta": {{
    "genre": "Simulation",
    "subgenre": "Management",
    "sub_subgenre": ["Time Management", "Co-op Multiplayer", "Level-based Progression"],
    "era": ["Modern", "Cartoonish"],
    "setting": ["Floating Restaurant", "Fantasy Kitchen"],
    "music": ["Upbeat", "Tense", "Lighthearted"]
  }},
  "mechanic_tags": {{
    "time_management": 1.0,
    "co_op_play": 0.95,
    "task_assignment": 0.9,
    "item_passing": 0.85,
    "ingredient_processing": 0.8,
    "combo_execution": 0.75
  }},
  "descriptive_tags": {{
    "chaotic_energy": 1.0,
    "bright_color_palette": 0.95,
    "fast_paced": 0.9,
    "lighthearted_tone": 0.85,
    "stressful_fun": 0.85,
    "cartoon_aesthetic": 0.8
  }},
  "gameplay_tags": {{
    "reaction_time_challenges": 1.0,
    "role_switching": 0.95,
    "order_completion_goals": 0.9,
    "kitchen_variants": 0.85,
    "level_unlocking": 0.8,
    "score_based_progression": 0.75
  }},
  "unique_in_genre_tags": {{
    "communication_without_words": 1.0,
    "joyful_chaos_design": 0.95,
    "emergent_team_dynamics": 0.9,
    "puzzle_like_kitchen_layouts": 0.85,
    "tension_as_fun": 0.8,
    "movement_as_strategy": 0.75,
    "nonverbal_coordination_pressure": 0.75
  }}
}}
"""

    # Send to OpenAI
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-16k",  # Or use "gpt-3.5-turbo-16k" for cheaper runs
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )

    return response.choices[0].message.content.strip()
