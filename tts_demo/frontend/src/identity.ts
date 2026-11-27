const SPEAKER_ID_KEY = "fonSpeakerId";
const SPEAKER_LABEL_KEY = "fonSpeakerLabel";
const ONBOARDING_DONE_KEY = "fonOnboardingDone";
const CONSENT_GIVEN_KEY = "fonConsentGiven";
const CONTRIBUTION_MODE_KEY = "fonContributionMode";

export type ContributionMode = "audio_only" | "audio_text";

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

// Given once at first launch (writing-check step), right after consent.
// Absent (e.g. someone who onboarded before this step existed) is treated as
// "audio_text" by every caller, so this never blocks or re-prompts them.
export function getContributionMode(): ContributionMode | null {
  try {
    const value = localStorage.getItem(CONTRIBUTION_MODE_KEY);
    return value === "audio_only" || value === "audio_text" ? value : null;
  } catch {
    return null;
  }
}

export function saveContributionMode(mode: ContributionMode): void {
  try {
    localStorage.setItem(CONTRIBUTION_MODE_KEY, mode);
  } catch {
    // Storage unavailable: choice stays in-memory for this page load only.
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

// ---- Consentements détaillés, profil facultatif et domaines préférés ------
// Stockés localement uniquement. TODO serveur : transmettre ces choix avec
// chaque contribution (voir docs/audit_design.md, risque « Collecte de données »).
const CONSENT_DETAILS_KEY = "fonConsentDetails";
const PROFILE_KEY = "fonProfile";
const DOMAIN_PREFS_KEY = "fonDomainPrefs";

export interface ConsentDetails {
  profile: boolean;
  publication: boolean;
}

export interface SpeakerProfile {
  ageRange: string;
  region: string;
  variant: string;
}

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

function writeJson(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Storage unavailable: the choice stays in-memory for this page load only.
  }
}

export function saveConsentDetails(details: ConsentDetails): void {
  writeJson(CONSENT_DETAILS_KEY, details);
}

export function getConsentDetails(): ConsentDetails {
  return readJson<ConsentDetails>(CONSENT_DETAILS_KEY, { profile: false, publication: false });
}

export function saveProfile(profile: SpeakerProfile): void {
  writeJson(PROFILE_KEY, profile);
}

export function saveDomainPrefs(ids: string[]): void {
  writeJson(DOMAIN_PREFS_KEY, ids);
}

export function getDomainPrefs(): string[] {
  return readJson<string[]>(DOMAIN_PREFS_KEY, []);
}

export function peekSpeakerLabel(): string | null {
  try {
    return localStorage.getItem(SPEAKER_LABEL_KEY);
  } catch {
    return null;
  }
}

/** Retire l'accord : l'onboarding (consentement, pseudo, mode) sera redemandé. */
export function withdrawConsent(): void {
  try {
    localStorage.removeItem(CONSENT_GIVEN_KEY);
    localStorage.removeItem(CONSENT_DETAILS_KEY);
    localStorage.removeItem(ONBOARDING_DONE_KEY);
  } catch {
    // stockage indisponible : rien à retirer
  }
}

/** Efface toutes les données locales du jeu sur cet appareil (clés « fon* »). */
export function clearAllLocalData(): void {
  try {
    Object.keys(localStorage)
      .filter((key) => key.startsWith("fon"))
      .forEach((key) => localStorage.removeItem(key));
  } catch {
    // stockage indisponible : rien à effacer
  }
}
