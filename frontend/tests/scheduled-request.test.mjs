import assert from "node:assert/strict"
import test from "node:test"
import { scheduleRequest } from "../lib/scheduled-request.ts"

const flush = () => new Promise((resolve) => setImmediate(resolve))
function deferred() {
  let resolve, reject
  const promise = new Promise((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}
function callbacks(events) {
  return {
    onStart: () => events.push("start"),
    onSuccess: (value) => events.push(value),
    onError: () => events.push("error"),
    onSettled: () => events.push("settled"),
  }
}

test("cancelled debounce never starts a fetch", (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] })
  const events = []
  const cancel = scheduleRequest({ delayMs: 180, load: async () => "result", ...callbacks(events) })
  cancel()
  t.mock.timers.tick(180)
  assert.deepEqual(events, [])
})

test("a late response cannot replace newer results or their loading state", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] })
  const events = [], old = deferred(), next = deferred()
  let oldSignal
  const cancel = scheduleRequest({ delayMs: 180, load: (signal) => {
    oldSignal = signal
    return old.promise
  }, ...callbacks(events) })
  t.mock.timers.tick(180)
  cancel()
  scheduleRequest({ delayMs: 180, load: () => next.promise, ...callbacks(events) })
  t.mock.timers.tick(180)
  next.resolve("new results")
  await flush()
  old.resolve("stale results") // Simulates a transport ignoring abort or JSON already parsing.
  await flush()
  assert.equal(oldSignal.aborted, true)
  assert.deepEqual(events, ["start", "start", "new results", "settled"])
})

test("clearing a search suppresses late errors", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] })
  const events = [], task = deferred()
  const cancel = scheduleRequest({ delayMs: 180, load: () => task.promise, ...callbacks(events) })
  t.mock.timers.tick(180)
  cancel()
  task.reject(new Error("aborted"))
  await flush()
  assert.deepEqual(events, ["start"])
})

test("active failures still clear loading and surface the error", async (t) => {
  t.mock.timers.enable({ apis: ["setTimeout"] })
  const events = []
  scheduleRequest({ delayMs: 180, load: async () => { throw new Error("offline") }, ...callbacks(events) })
  t.mock.timers.tick(180)
  await flush()
  assert.deepEqual(events, ["start", "error", "settled"])
})
