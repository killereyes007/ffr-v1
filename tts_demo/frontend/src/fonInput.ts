// Logique d'édition du clavier fon, indépendante de Vue : chaque fonction prend
// le texte et la sélection courants, et renvoie le nouveau texte et la position
// du curseur. Le texte rendu est toujours normalisé en NFC.

export type FonKey =
  | { kind: "text"; text: string }
  | { kind: "tone"; mark: string }
  | { kind: "backspace" }
  | { kind: "close" };

export type EditResult = { value: string; cursor: number };

// Signes diacritiques combinants des tons du fon.
export const FON_TONES = [
  { mark: "́", label: "´", name: "Ton haut", sample: "á" },
  { mark: "̀", label: "`", name: "Ton bas", sample: "à" },
  { mark: "̌", label: "ˇ", name: "Ton montant", sample: "ǎ" },
  { mark: "̂", label: "^", name: "Ton descendant", sample: "â" },
] as const;

const TONE_MARKS = new Set<string>(FON_TONES.map((t) => t.mark));
// Lettres qui peuvent porter un ton : voyelles orales, et nasales syllabiques.
const TONE_BEARERS = new Set(["a", "e", "ɛ", "i", "o", "ɔ", "u", "m", "n"]);
const COMBINING = /[̀-ͯ]/;

function nfcWithCursor(before: string, after: string): EditResult {
  const head = before.normalize("NFC");
  return { value: head + after.normalize("NFC"), cursor: head.length };
}

/** Début du dernier caractère visible (lettre de base + ses signes combinants). */
function lastClusterStart(text: string): number {
  let i = text.length;
  while (i > 0 && COMBINING.test(text[i - 1])) i -= 1;
  return Math.max(0, i - 1);
}

export function insertText(value: string, start: number, end: number, text: string): EditResult {
  return nfcWithCursor(value.slice(0, start) + text, value.slice(end));
}

export function backspace(value: string, start: number, end: number): EditResult {
  if (start !== end) return nfcWithCursor(value.slice(0, start), value.slice(end));
  if (start === 0) return { value, cursor: 0 };
  const head = value.slice(0, start);
  return nfcWithCursor(head.slice(0, lastClusterStart(head)), value.slice(end));
}

/**
 * Pose un ton sur la lettre juste avant le curseur. Le même ton une seconde
 * fois l'enlève ; un autre ton le remplace. Renvoie null si la lettre ne peut
 * pas porter de ton (consonne, espace, début du champ).
 */
export function applyTone(value: string, start: number, end: number, mark: string): EditResult | null {
  const head = value.slice(0, start);
  const from = lastClusterStart(head);
  const cluster = head.slice(from).normalize("NFD");
  const base = cluster[0];
  if (!base || !TONE_BEARERS.has(base.toLowerCase())) return null;
  const marks = [...cluster.slice(1)];
  const hadSame = marks.includes(mark);
  const kept = marks.filter((m) => !TONE_MARKS.has(m));
  const next = base + kept.join("") + (hadSame ? "" : mark);
  return nfcWithCursor(head.slice(0, from) + next, value.slice(end));
}

/** Applique une touche du clavier fon ; null si la touche n'a aucun effet. */
export function applyFonKey(value: string, start: number, end: number, key: FonKey): EditResult | null {
  switch (key.kind) {
    case "text":
      return insertText(value, start, end, key.text);
    case "backspace":
      return backspace(value, start, end);
    case "tone":
      return applyTone(value, start, end, key.mark);
    default:
      return null;
  }
}
