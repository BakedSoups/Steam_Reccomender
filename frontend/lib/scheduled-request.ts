interface ScheduledRequest<T> {
  delayMs: number
  load: (signal: AbortSignal) => Promise<T>
  onStart: () => void
  onSuccess: (value: T) => void
  onError: (error: unknown) => void
  onSettled: () => void
}

/** Effect cleanup cancels both pending work and in-flight fetches.
 * Guard callbacks too: a response may already be parsing when cancelled.
 */
export function scheduleRequest<T>(request: ScheduledRequest<T>): () => void {
  const controller = new AbortController()
  const timer = setTimeout(async () => {
    try {
      request.onStart()
      const value = await request.load(controller.signal)
      if (!controller.signal.aborted) request.onSuccess(value)
    } catch (error) {
      if (!controller.signal.aborted) request.onError(error)
    } finally {
      if (!controller.signal.aborted) request.onSettled()
    }
  }, request.delayMs)

  return () => {
    clearTimeout(timer)
    controller.abort()
  }
}
