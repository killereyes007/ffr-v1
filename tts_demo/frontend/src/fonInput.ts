// Logique du clavier fon, indépendante de Vue : chaque fonction d'édition prend
// le texte et la sélection courants, et renvoie le nouveau texte et la position
// du curseur. Le texte rendu est toujours normalisé en NFC.
//
// À VALIDER AVEC UN LINGUISTE DU FON (voir docs/clavier-fon-a-valider.md) :
// la liste des lettres, la notation des tons et celle des voyelles nasales.
// Tout est défini ici pour être changé à un seul endroit.

export type FonKey = { kind: "text"; text: string } | { kind: "backspace" } | { kind: "close" };

export type EditResult = { value: string; cursor: number };

/** Lettres propres au fon, sur leur rangée dédiée. */
export const FON_SPECIAL_LETTERS = ["ɖ", "ɛ", "ɔ", "ɣ"] as const;

/** Lettres latines de l'alphabet fon (pas de q). */
export const FON_LATIN_ROWS = [
  ["a", "b", "c", "d", "e", "f", "g", "h", "i", "j"],
  ["k", "l", "m", "n", "o", "p", "r", "s", "t", "u"],
  ["v", "w", "x", "y", "z"],
] as const;

/** Voyelles qui portent un ton (appui long sur la touche). */
export const FON_TONE_VOWELS = ["a", "e", "ɛ", "i", "o", "ɔ", "u"] as const;

/** Tons du fon, notés par un signe diacritique combinant au-dessus de la voyelle. */
export const FON_TONES = [
  { mark: "́", name: "ton haut" },
  { mark: "̀", name: "ton bas" },
  { mark: "̌", name: "ton montant" },
  { mark: "̂", name: "ton descendant" },
] as const;

const COMBINING = /[̀-ͯ]/;

export function isToneVowel(letter: string): boolean {
  return (FON_TONE_VOWELS as readonly string[]).includes(letter.toLowerCase());
}

/** La voyelle sans ton, puis ses variantes tonales (NFC) : a, á, à, ǎ, â. */
export function toneVariants(vowel: string): { text: string; name: string }[] {
  return [
    { text: vowel, name: "sans ton" },
    ...FON_TONES.map((tone) => ({ text: (vowel + tone.mark).normalize("NFC"), name: tone.name })),
  ];
}

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

/** Efface la sélection, ou le dernier caractère visible avec son ton. */
export function backspace(value: string, start: number, end: number): EditResult {
  if (start !== end) return nfcWithCursor(value.slice(0, start), value.slice(end));
  if (start === 0) return { value, cursor: 0 };
  const head = value.slice(0, start);
  return nfcWithCursor(head.slice(0, lastClusterStart(head)), value.slice(end));
}

/** Applique une touche du clavier fon ; null si la touche ne modifie pas le texte. */
export function applyFonKey(value: string, start: number, end: number, key: FonKey): EditResult | null {
  switch (key.kind) {
    case "text":
      return insertText(value, start, end, key.text);
    case "backspace":
      return backspace(value, start, end);
    default:
      return null;
  }
}
