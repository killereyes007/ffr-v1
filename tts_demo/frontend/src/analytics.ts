import { peekSpeakerId } from "./identity";

// Best-effort telemetry only: never blocks the UI, never surfaces an error to
// the user, never throws. A dropped event is acceptable; a frozen screen isn't.
export function logEvent(eventType: string, payload: Record<string, unknown> = {}): void {
  try {
    const speakerId = peekSpeakerId();
    void fetch("/analytics/event", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ event_type: eventType, speaker_id: speakerId, payload }),
    }).catch(() => {
      // ignored: telemetry delivery is not guaranteed
    });
  } catch {
    // ignored: e.g. JSON.stringify failing on a bad payload
  }
}
