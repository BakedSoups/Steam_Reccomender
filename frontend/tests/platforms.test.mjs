import test from "node:test"
import assert from "node:assert/strict"
import { platformLabels, supportsOperatingSystem } from "../lib/platforms.ts"

test("OS filters exclude unknown and unsupported games", () => {
  assert.equal(supportsOperatingSystem(null, "linux"), false)
  assert.equal(supportsOperatingSystem({ windows: true, mac: false, linux: false }, "linux"), false)
  assert.equal(supportsOperatingSystem({ windows: true, mac: false, linux: true }, "linux"), true)
  assert.equal(supportsOperatingSystem(null, ""), true)
})

test("supported Steam flags use user-facing OS names", () => {
  assert.deepEqual(platformLabels({ windows: true, mac: true, linux: false }), ["Windows", "macOS"])
  assert.deepEqual(platformLabels(null), [])
})
