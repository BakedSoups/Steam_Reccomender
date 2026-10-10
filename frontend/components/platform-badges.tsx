import { platformLabels } from "@/lib/platforms"
import type { PlatformSupport } from "@/lib/types"

export function PlatformBadges({ platforms }: { platforms?: PlatformSupport | null }) {
  const labels = platformLabels(platforms)
  return (
    <div className="mt-2 flex flex-wrap gap-1.5 text-xs text-slate-300" aria-label="Supported operating systems">
      {labels.length ? labels.map((label) => (
        <span key={label} className="rounded-full border border-white/15 bg-white/5 px-2 py-1">{label}</span>
      )) : <span>{platforms ? "No supported OS listed" : "OS compatibility unavailable"}</span>}
    </div>
  )
}
