// Points d'effort, série de jours, niveaux et progression par domaine.
// Stockage local uniquement (localStorage).
// TODO données : les seuils et les points sont PROVISOIRES. Les points complets
// ne comptent qu'après validation par un expert (voir docs/audit_design.md) ;
// ici on ne compte que l'effort de l'utilisateur sur cet appareil.

const KEY = "fonGameState";

export const POINTS_VOICE = 10;
export const POINTS_WRITE = 5;

export interface Level {
  n: number;
  name: string;
  min: number;
}

export const LEVELS: Level[] = [
  { n: 1, name: "Découverte", min: 0 },
  { n: 2, name: "Apprenti", min: 40 },
  { n: 3, name: "Confirmé", min: 120 },
  { n: 4, name: "Maître", min: 300 },
  { n: 5, name: "Gardien de la langue", min: 600 },
];

interface GameState {
  points: number;
  days: string[]; // dates ISO (AAAA-MM-JJ) où l'utilisateur a contribué
  byDomain: Record<string, number>;
}

function today(offset = 0): string {
  const d = new Date();
  d.setDate(d.getDate() - offset);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

export function loadGame(): GameState {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Partial<GameState>;
      return {
        points: Number(parsed.points) || 0,
        days: Array.isArray(parsed.days) ? parsed.days : [],
        byDomain: parsed.byDomain && typeof parsed.byDomain === "object" ? parsed.byDomain : {},
      };
    }
  } catch {
    // stockage indisponible : on repart d'un état vide
  }
  return { points: 0, days: [], byDomain: {} };
}

function save(state: GameState): void {
  try {
    localStorage.setItem(KEY, JSON.stringify(state));
  } catch {
    // stockage indisponible : l'état reste en mémoire pour cette session
  }
}

export function levelFor(points: number): Level {
  let current = LEVELS[0];
  for (const level of LEVELS) if (points >= level.min) current = level;
  return current;
}

export function nextLevel(points: number): Level | null {
  return LEVELS.find((level) => level.min > points) ?? null;
}

/** Série : nombre de jours consécutifs (aujourd'hui ou hier compris). */
export function streakOf(days: string[]): number {
  const set = new Set(days);
  let offset = set.has(today()) ? 0 : set.has(today(1)) ? 1 : -1;
  if (offset < 0) return 0;
  let count = 0;
  while (set.has(today(offset))) {
    count += 1;
    offset += 1;
  }
  return count;
}

export interface Award {
  points: number;
  total: number;
  leveledUp: Level | null;
}

export function awardPoints(domainId: string, points: number): Award {
  const state = loadGame();
  const before = levelFor(state.points);
  state.points += points;
  state.byDomain[domainId] = (state.byDomain[domainId] ?? 0) + 1;
  const day = today();
  if (!state.days.includes(day)) state.days.push(day);
  state.days = state.days.slice(-60);
  save(state);
  const after = levelFor(state.points);
  return { points, total: state.points, leveledUp: after.n > before.n ? after : null };
}

// ---- Historique local des contributions envoyées depuis cet appareil ----
// TODO serveur : les statuts après « Reçu » (En relecture, À valider par un expert,
// Validé, Rejeté) doivent venir d'une route serveur ; ici tout est « Reçu ».
const CONTRIB_KEY = "fonContributions";

export interface ContributionRecord {
  id: string;
  at: number;
  domain: string;
  text: string;
}

export function loadContributions(): ContributionRecord[] {
  try {
    const raw = localStorage.getItem(CONTRIB_KEY);
    const list = raw ? (JSON.parse(raw) as ContributionRecord[]) : [];
    return Array.isArray(list) ? list : [];
  } catch {
    return [];
  }
}

export function addContribution(record: ContributionRecord): void {
  try {
    const list = [record, ...loadContributions()].slice(0, 100);
    localStorage.setItem(CONTRIB_KEY, JSON.stringify(list));
  } catch {
    // stockage indisponible : l'historique n'est pas conservé
  }
}
