"use client"

import { useState } from "react"
import { ChevronDown } from "lucide-react"
import { EngineStory } from "@/components/engine-story"

export function EngineStoryExpand() {
  const [open, setOpen] = useState(false)
  return (
    <div className="mx-auto mt-2 max-w-3xl">
      <button type="button" aria-expanded={open} aria-controls="home-engine-story" onClick={() => setOpen(!open)} className="inline-flex min-h-12 items-center gap-2 text-base font-medium text-white sm:text-lg underline decoration-sky-200/40 underline-offset-4 transition hover:text-white">
        Why I built this engine <ChevronDown className={`h-5 w-5 transition-transform ${open ? "rotate-180" : ""}`} aria-hidden="true" />
      </button>
      <div id="home-engine-story" aria-hidden={!open} inert={!open} className={`grid transition-[grid-template-rows] duration-500 ease-out motion-reduce:transition-none ${open ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}>
        <div className="min-h-0 overflow-hidden">
          <div className="mt-4 rounded-2xl border border-white/15 bg-[#09131e]/95 p-6 shadow-xl sm:p-8">
            <EngineStory heading="h2" />
          </div>
        </div>
      </div>
    </div>
  )
}
