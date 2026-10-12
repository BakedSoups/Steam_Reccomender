export function EngineStory({ heading = "h1" }: { heading?: "h1" | "h2" }) {
  const Heading = heading
  const DetailsHeading = heading === "h1" ? "h2" : "h3"
  return (
    <section aria-labelledby="engine-story-title" className="mx-auto max-w-3xl text-left">
      <Heading id="engine-story-title" className="text-3xl font-semibold tracking-tight text-white sm:text-4xl">Why I built this engine</Heading>
      <div className="mt-4 space-y-4 text-base leading-8 text-white sm:text-lg">
        <p>
          I made this engine because I wanted to find games based on the specific aspects I enjoy. Other similarity sites I&apos;ve tried mostly let me enter a game, with little control over what makes the results similar. Steam&apos;s{" "}
          <a href="https://partner.steamgames.com/doc/store/tags" target="_blank" rel="noreferrer" className="text-sky-200 underline decoration-sky-200/50 underline-offset-4 hover:text-white">&ldquo;More Like This&rdquo; uses a game&apos;s top 20 tags</a>{" "}
          to find similar games, but I want to choose which similarities matter to me.
        </p>
        <p>
          I also feel like I get recommended the same games all the time. Systems that use player activity have more evidence to work with for popular games, which makes sense. But the cost can be that many other games fly under our radar. This engine tries to combat that by giving you more control over the aspects you&apos;re searching for.
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
          {" "}I&apos;m always open to suggestions, whether that&apos;s improvements to the algorithm or just small UI changes!
        </p>
        <a href="https://github.com/BakedSoups/NextSteamGame/issues" target="_blank" rel="noreferrer" className="mt-2 inline-flex min-h-10 items-center rounded-full border border-sky-200/30 bg-sky-200/10 px-4 py-2 text-sm font-medium text-sky-100 transition hover:border-sky-200/60 hover:bg-sky-200/20">
          Share a suggestion
        </a>
        <figure className="pt-4">
          <a href="https://share.google/1BqRdhGBdkUHUSQ4v" target="_blank" rel="noreferrer" className="block overflow-hidden rounded-xl border border-white/15">
            <img src="/local-comic-store.png" alt="Inside my local comic book store, with shelves of comics and a cozy browsing aisle" width="516" height="387" loading="lazy" className="h-auto w-full" />
          </a>
          <figcaption className="mt-2 text-sm text-slate-200">My local comic book store, which inspired the cozy theme of this website.</figcaption>
        </figure>
        <div className="space-y-4 border-t border-white/15 pt-6">
          <DetailsHeading className="text-2xl font-semibold text-white">How the engine works</DetailsHeading>
        <a href="https://github.com/user-attachments/assets/fb48c02d-53c1-4afd-ae4a-d7f58fee58f1" target="_blank" rel="noreferrer" className="block overflow-hidden rounded-xl border border-white/15 bg-white">
          <img src="https://github.com/user-attachments/assets/fb48c02d-53c1-4afd-ae4a-d7f58fee58f1" alt="Steam Rec pipeline: collect reviews, extract game profiles, canonicalize tags, precompute candidates, and rerank them for each search" loading="lazy" className="h-auto w-full" />
        </a>
        <p>
          Steam Rec is essentially a RAG style retrieval system built around a hierarchical genre tree and the aspects of each game. Genres, subgenres, and more specific branches contribute to the game profiles used for retrieval and matching, alongside things like mechanics, atmosphere, mission structure, and music.
        </p>
        <p>
          I precompute the expensive retrieval work ahead of time and save a candidate pool for each game. When you change what matters to you, my poor Vultr instance loads that pool and reranks the games using your choices. The candidates are precomputed; your personalized ranking happens live.
        </p>
        <p>
          LLMs help build the game profiles offline. Normal searches use those saved profiles rather than asking an LLM to generate recommendations. This keeps the live compute needs modest as more people use the engine.
        </p>
        </div>
      </div>
    </section>
  )
}
