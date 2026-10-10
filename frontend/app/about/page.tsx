import type { Metadata } from "next"
import Link from "next/link"
import { ArrowLeft } from "lucide-react"
import { EngineStory } from "@/components/engine-story"

export const metadata: Metadata = {
  title: "About this engine",
  description: "The idea behind NextSteamGame: make game discovery a fun conversation about the aspects you enjoy.",
  alternates: { canonical: "/about" },
  openGraph: { title: "About this engine | NextSteamGame", url: "/about" },
}

export default function AboutPage() {
  return (
    <main className="viewport-height bg-[#09131e] px-5 py-8 sm:px-8 sm:py-12">
      <div className="mx-auto max-w-3xl">
        <Link href="/" className="mb-10 inline-flex min-h-10 items-center gap-2 rounded-full border border-white/15 bg-white/5 px-4 py-2 text-sm text-slate-200 transition hover:border-sky-200/40 hover:text-white">
          <ArrowLeft className="h-4 w-4" aria-hidden="true" /> Back to search
        </Link>
        <p className="mb-4 text-xs font-medium uppercase tracking-[0.22em] text-sky-200">NextSteamGame</p>
        <EngineStory />
      </div>
    </main>
  )
}
