"use client"

import { useRef, useState } from "react"

const greetings = ["What's up?", "Oh, OK!", "Found anything good?", "Just browsing.", "Take your time."]

export function CozyReader() {
  const nextGreeting = useRef(0)
  const [greeting, setGreeting] = useState<string | null>(null)
  const sayHello = () => {
    setGreeting(greetings[nextGreeting.current % greetings.length])
    nextGreeting.current += 1
  }

  return (
    <div className="relative shrink-0">
      {greeting && <span role="status" className="pointer-events-none absolute bottom-full left-1/2 z-20 mb-2 -translate-x-1/2 whitespace-nowrap rounded-2xl border border-white/40 bg-[#0b1823] px-4 py-2 text-sm font-medium text-white shadow-lg">{greeting}<span aria-hidden="true" className="absolute left-1/2 top-full -mt-1 h-3 w-3 -translate-x-1/2 rotate-45 border-b border-r border-white/40 bg-[#0b1823]" /></span>}
      <button type="button" aria-label="Say hello to the cozy reader" onMouseEnter={sayHello} onMouseLeave={() => setGreeting(null)} onFocus={sayHello} onBlur={() => setGreeting(null)} onClick={sayHello} className="block rounded-xl focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-amber-200">
        <img src={greeting ? "/nextsteamgame-reader-looking-up.svg?v=flared-lamp-6" : "/nextsteamgame-icon.svg?v=flared-lamp-6"} alt="A guy reading a magazine beside a desk lamp" className="launch-logo h-20 w-20 object-contain sm:h-24 sm:w-24 md:h-28 md:w-28" />
      </button>
    </div>
  )
}
