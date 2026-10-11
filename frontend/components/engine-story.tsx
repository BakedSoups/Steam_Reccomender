export function EngineStory({ heading = "h1" }: { heading?: "h1" | "h2" }) {
  const Heading = heading
  return (
    <section aria-labelledby="engine-story-title" className="mx-auto max-w-3xl text-left">
      <Heading id="engine-story-title" className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">Why I built this engine</Heading>
      <div className="mt-4 space-y-4 text-base leading-8 text-white sm:text-lg">
        <a href="https://github.com/user-attachments/assets/fb48c02d-53c1-4afd-ae4a-d7f58fee58f1" target="_blank" rel="noreferrer" className="block overflow-hidden rounded-xl border border-white/15 bg-white">
          <img src="https://github.com/user-attachments/assets/fb48c02d-53c1-4afd-ae4a-d7f58fee58f1" alt="Steam Rec pipeline: collect reviews, extract game profiles, canonicalize tags, precompute candidates, and rerank them for each search" loading="lazy" className="h-auto w-full" />
        </a>
        <p>
          Steam Rec is essentially a RAG style retrieval system built around a hierarchical genre tree and the aspects of each game. Genres, subgenres, and more specific branches contribute to the game profiles used for retrieval and matching, alongside things like mechanics, atmosphere, mission structure, and music.
        </p>
        <p>
          I precompute the expensive retrieval work ahead of time and save a candidate pool for each game. When you change what matters to you, my small Vultr instance loads that pool and reranks the games using your choices. The candidates are precomputed; your personalized ranking happens live.
        </p>
        <p>
          LLMs help build the game profiles offline. Normal searches use those saved profiles rather than asking an LLM to generate recommendations. This keeps the live compute needs modest as more people use the engine.
        </p>
        <p>
          Searching for games can feel limiting when you can&apos;t describe what you&apos;re looking for, or when broad tags don&apos;t capture what you enjoy. Recommendation algorithms often favor games that already get plenty of traffic because that traffic provides consistent data. This is effective, but it can mean seeing the same games over and over while many others fly under our radar.
        </p>
        <p>
          NextSteamGame.com tries to put that control in your hands by letting you choose the aspects of your favorite game that you want to find in something new. This engine aims to help you discover games that don&apos;t appeal to an algorithm but might appeal to you.
        </p>
        <p>
          I had this idea because I used to find new comic books by talking about the aspects of my favorite comics with the store owner at my{" "}
          <a href="https://share.google/1BqRdhGBdkUHUSQ4v" target="_blank" rel="noreferrer" className="text-sky-200 underline decoration-sky-200/50 underline-offset-4 hover:text-white">local comic store</a>.
          {" "}Those conversations made discovery fun, and I wanted to bring that feeling to searching for games. The store also inspired the theme of this website: a cozy place to just look at games.
        </p>
        <p>
          This engine is a work in progress and{" "}
          <a href="https://github.com/BakedSoups/NextSteamGame" target="_blank" rel="noreferrer" className="text-sky-200 underline decoration-sky-200/50 underline-offset-4 hover:text-white">open source</a>!
          {" "}I&apos;m always open to suggestions for fixing it and making it better.
        </p>
        <a href="https://github.com/BakedSoups/NextSteamGame/issues" target="_blank" rel="noreferrer" className="mt-2 inline-flex min-h-10 items-center rounded-full border border-sky-200/30 bg-sky-200/10 px-4 py-2 text-sm font-medium text-sky-100 transition hover:border-sky-200/60 hover:bg-sky-200/20">
          Share a suggestion
        </a>
      </div>
    </section>
  )
}
