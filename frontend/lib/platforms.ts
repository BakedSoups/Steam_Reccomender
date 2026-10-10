import type { OperatingSystem, PlatformSupport } from "./types.ts"

export const OPERATING_SYSTEMS: { id: OperatingSystem; label: string }[] = [
  { id: "windows", label: "Windows" },
  { id: "mac", label: "macOS" },
  { id: "linux", label: "Linux" },
]

export function supportsOperatingSystem(platforms: PlatformSupport | null | undefined, os: OperatingSystem | ""): boolean {
  return !os || platforms?.[os] === true
}

export function platformLabels(platforms: PlatformSupport | null | undefined): string[] {
  return OPERATING_SYSTEMS.filter(({ id }) => platforms?.[id] === true).map(({ label }) => label)
}
