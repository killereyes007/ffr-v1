// Manches du jeu : les cartes sont tirées au hasard par le serveur (base de
// données), sans que le joueur choisisse quoi traduire. Hors ligne ou serveur
// sans base : repli sur les éléments embarqués dans l'application.

export interface RoundCard {
  id: string;
  domain_id: string;
  domain_label: string;
  kind: "mot" | "phrase" | "paragraphe";
  difficulty: "facile" | "moyen" | "difficile";
  text: string;
}

export interface DomainInfo {
  id: string;
  total: number;
  counts: Record<string, number>;
}

export const ROUND_SIZE = 5;
const SEEN_KEY = "fonSeenItems";
const SEEN_MAX = 300;

export function loadSeen(): string[] {
  try {
    const raw = JSON.parse(localStorage.getItem(SEEN_KEY) ?? "[]");
    return Array.isArray(raw) ? raw.filter((x) => typeof x === "string") : [];
  } catch {
    return [];
  }
}

export function markSeen(id: string): void {
  try {
    const seen = loadSeen().filter((x) => x !== id);
    seen.push(id);
    localStorage.setItem(SEEN_KEY, JSON.stringify(seen.slice(-SEEN_MAX)));
  } catch {
    // stockage indisponible : on retombera simplement sur des répétitions
  }
}

export async function fetchRound(domainId: string | null, level: number): Promise<RoundCard[]> {
  const params = new URLSearchParams({
    level: String(level),
    size: String(ROUND_SIZE),
    exclude: loadSeen().slice(-200).join(","),
  });
  if (domainId) params.set("domain", domainId);
  const response = await fetch(`/game/round?${params.toString()}`);
  if (!response.ok) throw new Error(`round ${response.status}`);
  const data = (await response.json()) as { cards?: RoundCard[] };
  if (!data.cards?.length) throw new Error("round vide");
  return data.cards;
}

export async function fetchDomainInfo(): Promise<DomainInfo[]> {
  const response = await fetch("/game/domains");
  if (!response.ok) throw new Error(`domains ${response.status}`);
  const data = (await response.json()) as { domains?: DomainInfo[] };
  return data.domains ?? [];
}

// Phrases d'encouragement (simples, tutoiement). La série = cartes de suite
// où le joueur a contribué.
const CHEERS: [number, string][] = [
  [5, "Manche parfaite !"],
  [4, "Tu es en feu !"],
  [3, "Trois d'affilée, bravo !"],
  [2, "Deux de suite, continue !"],
  [1, "Bien joué !"],
];

export function cheerFor(streak: number): string {
  for (const [n, text] of CHEERS) if (streak >= n) return text;
  return "Bien joué !";
}

export function roundVerdict(done: number, size: number): { title: string; text: string } {
  if (done >= size) return { title: "Manche parfaite !", text: "Tu as dit toutes les cartes. Merci pour ta voix." };
  if (done >= Math.ceil(size / 2)) return { title: "Très belle manche !", text: "Encore une manche pour battre ton score ?" };
  if (done > 0) return { title: "Bon début !", text: "Chaque phrase aide la langue fon à vivre." };
  return { title: "À la prochaine !", text: "Tu peux passer des cartes, mais ta voix compte vraiment." };
}
