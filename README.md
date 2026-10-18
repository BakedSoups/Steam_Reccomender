# NextSteamGame

<img src="docs/assets/greg.png" alt="Greg" width="96" align="right" />

## How Steam Rec Works

<img width="1688" height="1260" alt="pipeline" src="https://github.com/user-attachments/assets/fb48c02d-53c1-4afd-ae4a-d7f58fee58f1" />

Steam Rec is essentially a RAG style retrieval system built around a hierarchical genre tree and the specific aspects of each game. The genre tree organizes games into primary genres, subgenres, and more specific branches. Review derived tags and vectors describe what players enjoy within those branches, from mission structure and combat systems to atmosphere and music. The genre branches contribute to both the embedded retrieval profile and the live genre match score; retrieval does not traverse the tree.

The expensive work happens ahead of time: collect reviews, extract game profiles, canonicalize tags, embed those profiles, and retrieve candidate games for each reference game. Those candidate pools are saved in Postgres. My small Vultr instance then loads a pool and reranks it using the aspects and weights you choose.

The RAG comparison describes the retrieval approach. The live engine returns scored game matches rather than generating an answer with an LLM. Keeping extraction and retrieval offline lets the project serve personalized searches without repeating that expensive work for every user.

## Why This Engine Exists

`NextSteamGame` is a Steam recommendation project built around the idea that games
should be matched by what they are, not only by player-overlap signals.

Most recommendation systems rely heavily on player-overlap data:

> Players who liked X also liked Y.

That works well for popular games, but it often struggles with niche preferences and rarely explains *why* two games are similar.

For example:

- Someone may enjoy Persona 5 because of its jazz fusion soundtrack and modern Tokyo setting.
- Another player may enjoy Persona 5 because of its social simulation and dungeon crawling.

Most recommendation systems treat those users identically.

NextSteamGame attempts to separate those signals and lets users directly control what aspects of a game matter most.

The project has three main layers:

- a metadata pipeline that builds and enriches `steam_metadata.db`
- a review/semantics pipeline that builds `steam_initial_noncanon.db` and `steam_final_canon.db`
- a live app stack that serves recommendations through FastAPI + a React frontend backed by Postgres

## App Preview

Current runtime application:

<img width="1958" height="1198" alt="image" src="https://github.com/user-attachments/assets/05f8ca2c-5578-41c2-8b3e-7d45d4ae61ff" />
<img width="1986" height="1433" alt="image" src="https://github.com/user-attachments/assets/26c461ad-472d-41d3-aee9-02e57d3ee42a" />

## Data and Build Stages

The current database contains roughly:

- 80,000 Steam games
- up to 2,000 reviews per game
- semantic vectors
- identity tags
- canonicalized genre and tag relationships

The expensive retrieval work is precomputed for each reference game. The live server loads that candidate pool and reranks it using the aspects and weights you choose. This leaves my small Vultr instance with a much lighter job than searching the entire catalog for every adjustment.

### Stage 1: Metadata Collection

The first stage creates a local metadata database using Steam's APIs and SteamSpy.

This includes:

- appids
- genres
- tags
- descriptions
- release information
- storefront artwork

Output:

```text
steam_metadata.db
```

### Stage 2: Review Collection & Filtering

For each game, the pipeline collects up to:

```text
2,000 reviews
```

Reviews are processed through several filtering stages:

- regex spam removal
- review quality scoring
- word diversity scoring
- insightful phrase detection
- review ranking heuristics

The goal is to prioritize reviews that actually explain the game rather than memes or one-line comments.

Reviews are then classified with ModernBERT into categories such as:

- gameplay explanations
- artistic discussion
- soundtrack discussion
- systems depth
- general descriptive reviews

This gives the pipeline separate review pools focused on different aspects of a game.

### Stage 3: Semantic Tag & Vector Generation

The highest quality review candidates are then passed into an LLM extraction pipeline.

This stage generates:

#### Focus Vectors

- mechanics
- narrative
- vibe
- structure_loop

#### Identity Metadata

- signature tags
- niche anchors
- identity tags
- music tags
- micro-tags

The goal is to capture details often missing from traditional tags.

For example, many players describe PlateUp!'s late-game automation systems as the most important part of the experience despite the game primarily being categorized as a cooperative cooking game.

### Stage 4: Canonical Tag Mapping

Generated tags frequently describe the same concept using different wording.

For example:

```text
Fast Action
Quick Action
High-Speed Combat
```

All represent nearly identical ideas.

To solve this, I built a separate canonicalization pipeline using:

- heuristics
- fuzzy matching
- embedding similarity
- vector search

This groups semantically similar tags together while preserving niche distinctions.

Output:

```text
steam_final_canon.db
```

### Stage 5: Retrieval Optimization

The recommendation system follows a retrieve and rerank approach. Think of it as the retrieval stage of RAG, with the expensive search computed ahead of time. LLMs extract focus vectors and identity metadata from reviews during the offline pipeline; the live app scores existing game profiles rather than generating recommendations with an LLM on each request.

During precomputation, Chroma finds nearby games using embeddings of their canonical profiles. The pipeline saves a candidate pool for each reference game in Postgres, in the `precomputed_candidates` table. The build default is 300 candidates per game, configurable with `--per-game`. The live retriever also defaults to a maximum pool of 300 candidates.

When a user asks for recommendations:

1. the server loads the reference game's saved candidate IDs from Postgres
2. it loads those games' profiles and scores their mechanics, narrative, vibe, structure, genres, identity, setting, music, and appeal against the user's preferences
3. it combines the weighted scores, applies metadata penalties and confidence adjustments, sorts the results, and returns the top matches

The normal path uses the saved pool. If it is missing or unusable, the retriever logs a warning and can fall back to Postgres prescreening and live Chroma retrieval when available.

Adjusting the controls changes the ranking within that candidate pool. The candidate relationships are precomputed; the final personalized order is calculated at request time.

This is how I keep my poor Vultr instance from doing the expensive work repeatedly. Review processing, LLM extraction, embedding generation, and catalog retrieval happen ahead of time. The usual live request is database reads and scoring a few hundred profiles, which keeps compute needs modest as more people use the engine. It also means a game outside the saved pool cannot appear through reranking alone; expanding discovery requires a broader pool or rebuilding retrieval.

## Runtime Stack

- backend: `FastAPI`
- frontend: `Next.js` / React
- runtime game store: `Postgres` through SQLAlchemy Core
- offline candidate retrieval: local `Chroma`
- live candidate lookup: `Postgres` (`precomputed_candidates`)
- upstream build artifacts: `SQLite`

The app flow is:

1. search for a Steam game
2. open it as the reference profile
3. inspect and adjust its focus vectors, identity tags, genres, and appeal axes
4. rerank the reference game's precomputed candidate pool using your chosen aspects and weights
