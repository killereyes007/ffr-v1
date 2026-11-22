const SPEAKER_ID_KEY = "fonSpeakerId";
const SPEAKER_LABEL_KEY = "fonSpeakerLabel";
const ONBOARDING_DONE_KEY = "fonOnboardingDone";
const CONSENT_GIVEN_KEY = "fonConsentGiven";

export interface SpeakerIdentity {
  speakerId: string;
  speakerLabel: string;
}

export function generateDefaultLabel(): string {
  const digits = Math.floor(1000 + Math.random() * 9000);
  return `Voix-${digits}`;
}

function generateId(): string {
  try {
    return crypto.randomUUID();
  } catch {
    return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  }
}

export function hasOnboarded(): boolean {
  try {
    return localStorage.getItem(ONBOARDING_DONE_KEY) === "1";
  } catch {
    // Storage unavailable (private mode / blocked): don't gate the app behind
    // onboarding on every single load, just let it through.
    return true;
  }
}

// Given once at first launch (onboarding/identify step), covering every
// contribution made on this device afterwards — no need to re-confirm it on
// each recording.
export function hasConsented(): boolean {
  try {
    return localStorage.getItem(CONSENT_GIVEN_KEY) === "1";
  } catch {
    return true;
  }
}

export function saveConsent(): void {
  try {
    localStorage.setItem(CONSENT_GIVEN_KEY, "1");
  } catch {
    // Storage unavailable: consent stays in-memory for this page load only.
  }
}

export function saveIdentity(label: string): SpeakerIdentity {
  const speakerLabel = label.trim() || generateDefaultLabel();
  const speakerId = generateId();
  try {
    localStorage.setItem(SPEAKER_ID_KEY, speakerId);
    localStorage.setItem(SPEAKER_LABEL_KEY, speakerLabel);
    localStorage.setItem(ONBOARDING_DONE_KEY, "1");
  } catch {
    // Storage unavailable: identity stays in-memory for this page load only.
  }
  return { speakerId, speakerLabel };
}

// Read-only, side-effect-free lookup for telemetry: unlike getSpeakerIdentity(),
// this never creates or persists an identity, so logging an event before the
// identify step can't silently mark onboarding as done.
export function peekSpeakerId(): string | null {
  try {
    return localStorage.getItem(SPEAKER_ID_KEY);
  } catch {
    return null;
  }
}

export function getSpeakerIdentity(): SpeakerIdentity {
  try {
    const storedId = localStorage.getItem(SPEAKER_ID_KEY);
    const storedLabel = localStorage.getItem(SPEAKER_LABEL_KEY);
    if (storedId && storedLabel) {
      return { speakerId: storedId, speakerLabel: storedLabel };
    }
  } catch {
    // ignore and fall through to generating a fresh identity below
  }
  // Never send an empty speaker_id to the server: if identity is missing for
  // any reason (storage blocked, onboarding skipped by a direct deep link),
  // generate and persist one on the fly.
  return saveIdentity(generateDefaultLabel());
}
