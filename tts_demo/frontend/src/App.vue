<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { usePwaInstall } from "./pwaInstall";
import {
  generateDefaultLabel,
  getConsentDetails,
  getContributionMode,
  getDomainPrefs,
  getSpeakerIdentity,
  hasConsented,
  hasOnboarded,
  clearAllLocalData,
  peekSpeakerLabel,
  withdrawConsent,
  saveConsent,
  saveConsentDetails,
  saveContributionMode,
  saveDomainPrefs,
  saveIdentity,
  saveProfile,
} from "./identity";
import { logEvent } from "./analytics";
import XoCube from "./XoCube.vue";
import XoIcon from "./XoIcon.vue";
import XoLogo from "./XoLogo.vue";
import XoLeaf from "./XoLeaf.vue";
import FonKeyboard from "./FonKeyboard.vue";
import { applyFonKey, type FonKey } from "./fonInput";
import { setTheme, themePref, type ThemePref } from "./theme";
import {
  addContribution,
  awardPoints,
  loadContributions,
  type ContributionRecord,
  levelFor,
  loadGame,
  nextLevel,
  POINTS_VOICE,
  POINTS_WRITE,
  streakOf,
  type Award,
  type Level,
} from "./gamification";
import { vXoTilt } from "./xoTilt";
import { ROUND_SIZE, cheerFor, fetchDomainInfo, fetchRound, markSeen, roundVerdict, type DomainInfo, type RoundCard } from "./rounds";

interface AudioCapture {
  stream: MediaStream;
  context: AudioContext;
  source: MediaStreamAudioSourceNode;
  processor: ScriptProcessorNode;
  silentOutput: GainNode;
  chunks: Float32Array[];
  sampleRate: number;
}

interface DomainItem {
  id?: string;
  text: string;
  kind: "mot" | "phrase" | "paragraphe";
}

interface DomainStory {
  kicker: string;
  title: string;
  body: string;
}

interface Domain {
  id: string;
  label: string;
  icon: string;
  image?: string;
  mode: "histoire" | "phrases";
  story?: DomainStory;
  items: DomainItem[];
}

// Dynamic bindings (not a static `src="..."` attribute) so Vue's compile-time
// asset-url transform doesn't try to resolve these /game-assets/ public paths
// as local module imports.

const domains: Domain[] = [
  {
    id: "sante",
    label: "Santé",
    icon: "✚",
    image: "/game-assets/images/domains/sante.png",
    mode: "histoire",
    story: {
      kicker: "Un centre de santé de quartier",
      title: "Au centre de santé du quartier",
      body:
        "L'agent de santé reçoit les habitants du quartier dès le matin. Aujourd'hui, une mère est venue avec son enfant qui tousse depuis plusieurs jours.",
    },
    items: [
      { text: "la fièvre", kind: "mot" },
      { text: "le médicament", kind: "mot" },
      { text: "Bonjour, qu'est-ce qui vous amène aujourd'hui ?", kind: "phrase" },
      { text: "Avez-vous de la fièvre depuis combien de jours ?", kind: "phrase" },
      { text: "Buvez beaucoup d'eau et reposez-vous.", kind: "phrase" },
      { text: "N'oubliez pas de revenir si ça ne va pas mieux.", kind: "phrase" },
      {
        text:
          "L'agent de santé explique calmement que la fièvre peut avoir plusieurs causes, qu'il faut surveiller la température chaque soir et revenir si elle ne baisse pas après trois jours de repos.",
        kind: "paragraphe",
      },
    ],
  },
  {
    id: "education",
    label: "Éducation",
    icon: "✎",
    image: "/game-assets/images/domains/education.png",
    mode: "histoire",
    story: {
      kicker: "Une salle de classe de village",
      title: "La rentrée à l'école du village",
      body:
        "C'est le premier jour de classe après les vacances. L'instituteur accueille les élèves devant l'école, certains reviennent de loin pour cette rentrée.",
    },
    items: [
      { text: "le cahier", kind: "mot" },
      { text: "la leçon", kind: "mot" },
      { text: "Ouvrez vos cahiers à la page dix.", kind: "phrase" },
      { text: "Qui peut me dire la capitale du Bénin ?", kind: "phrase" },
      { text: "Le travail que tu as fait est très bien.", kind: "phrase" },
      { text: "N'oublie pas d'apporter ton livre demain.", kind: "phrase" },
      {
        text:
          "L'instituteur rappelle que chaque élève doit relire sa leçon le soir, et que ceux qui ont des difficultés peuvent rester après la classe pour qu'on reprenne ensemble les parties mal comprises.",
        kind: "paragraphe",
      },
    ],
  },
  {
    id: "religion_traditions",
    label: "Religion & traditions",
    icon: "◆",
    image: "/game-assets/images/domains/religion_traditions.png",
    mode: "histoire",
    story: {
      kicker: "Une cérémonie saisonnière",
      title: "La cérémonie du village",
      body:
        "Une fois par saison, les familles du village se réunissent autour des anciens pour une cérémonie transmise depuis des générations.",
    },
    items: [
      { text: "la cérémonie", kind: "mot" },
      { text: "les anciens", kind: "mot" },
      { text: "Les anciens nous ont transmis cette histoire.", kind: "phrase" },
      { text: "Chaque saison, le village se réunit ici.", kind: "phrase" },
      { text: "Respecte la terre de tes ancêtres.", kind: "phrase" },
      { text: "Cette fête rassemble toute la famille.", kind: "phrase" },
      {
        text:
          "Chaque saison, les familles se rassemblent autour des anciens pour écouter les récits transmis de génération en génération, et personne ne quitte la cérémonie avant que le dernier chant ne soit terminé.",
        kind: "paragraphe",
      },
    ],
  },
  {
    id: "agriculture",
    label: "Agriculture",
    icon: "✦",
    mode: "phrases",
    items: [
      { text: "la récolte", kind: "mot" },
      { text: "Il va pleuvoir, il faut rentrer les régimes de maïs.", kind: "phrase" },
      { text: "Le champ de mon père est derrière la rivière.", kind: "phrase" },
      {
        text:
          "Chaque matin, je vais au champ avant qu'il fasse trop chaud. Je m'occupe des plants et j'arrose quand la terre est sèche.",
        kind: "paragraphe",
      },
    ],
  },
  {
    id: "commerce_marche",
    label: "Commerce & marché",
    icon: "⚖",
    mode: "phrases",
    items: [
      { text: "le prix", kind: "mot" },
      { text: "Combien coûte ce tissu ?", kind: "phrase" },
      { text: "C'est trop cher, peux-tu baisser un peu ?", kind: "phrase" },
      { text: "Je reviendrai demain acheter plus.", kind: "phrase" },
    ],
  },
  {
    id: "administration",
    label: "Administration & vie quotidienne",
    icon: "▤",
    mode: "phrases",
    items: [
      { text: "la carte d'identité", kind: "mot" },
      { text: "Où se trouve le bureau du quartier ?", kind: "phrase" },
      { text: "J'ai besoin d'un certificat de naissance.", kind: "phrase" },
      { text: "Le marché ferme à quelle heure aujourd'hui ?", kind: "phrase" },
    ],
  },
  {
    id: "metiers_travail",
    label: "Métiers & travail",
    icon: "⚒",
    mode: "phrases",
    items: [
      { text: "le mécanicien", kind: "mot" },
      { text: "Je cherche du travail pour la saison sèche.", kind: "phrase" },
      { text: "Mon oncle est menuisier depuis vingt ans.", kind: "phrase" },
      {
        text:
          "Mon frère répare les motos au bord de la route. Beaucoup de gens viennent le voir quand leur moto tombe en panne.",
        kind: "paragraphe",
      },
    ],
  },
];


const activeScreen = ref<"home" | "game" | "assistant" | "profile" | "contributions">("home");
// Destination demandée depuis l'accueil, à rejoindre une fois l'onboarding terminé.
const pendingTarget = ref<"game" | "assistant" | null>(null);
const menuOpen = ref(false);
function openMenu() {
  menuOpen.value = true;
  void nextTick(() => document.querySelector<HTMLElement>("#xo-drawer .xo-drawer-item")?.focus());
}
function closeMenu() {
  menuOpen.value = false;
}
function menuGo(action: "home" | "game" | "assistant" | "how" | "install" | "profile" | "contributions") {
  closeMenu();
  if (action === "home") showHome();
  else if (action === "game") enterApp("game");
  else if (action === "assistant") enterApp("assistant");
  else if (action === "profile" || action === "contributions") openProfileScreen(action);
  else if (action === "how") {
    showHome();
    void nextTick(() => explainHowItWorks());
  } else void handleInstallClick();
}
function onGlobalKeydown(e: KeyboardEvent) {
  if (e.key === "Escape" && menuOpen.value) closeMenu();
}
const contributionMode = ref<"domain" | "free">("domain");
const selectedDomainId = ref<string | null>(null);
const selectedDomain = computed(
  () => domains.find((domain) => domain.id === selectedDomainId.value) ?? null,
);
const selectedItem = ref<DomainItem | null>(null);
const domainStoryAcknowledged = ref(false);
const itemFinished = ref(false);

// --- Manches : le serveur tire les cartes au hasard, le joueur ne choisit pas. ---
const roundCards = ref<RoundCard[]>([]);
const roundIndex = ref(0);
const roundContributed = ref(0);
const roundStreak = ref(0);
const roundPoints = ref(0);
const roundSummary = ref(false);
const roundLoading = ref(false);
const roundError = ref("");
const roundDomainId = ref<string | null>(null);
const domainInfo = ref<Record<string, DomainInfo>>({});
const roundVerdictText = computed(() => roundVerdict(roundContributed.value, roundCards.value.length || ROUND_SIZE));
const roundCheer = computed(() => cheerFor(roundStreak.value));
const currentCard = computed(() => roundCards.value[roundIndex.value] ?? null);
const isLastCard = computed(() => roundIndex.value >= roundCards.value.length - 1);

// --- Difficulty levels: derived from each item's existing kind classification,
// not a separate scoring system. Kept as a plain ref so switching domains
// preserves the player's last-picked level for the session. ---
type Difficulty = "facile" | "moyen" | "difficile";
const kindToDifficulty: Record<DomainItem["kind"], Difficulty> = {
  mot: "facile",
  phrase: "moyen",
  paragraphe: "difficile",
};

interface OnboardingSlide {
  title: string;
  body?: string;
  list?: { label: string; detail: string }[];
}

const onboardingSlides: OnboardingSlide[] = [
  {
    title: "Bienvenue dans Le carnet des voix",
    body:
      "Un prototype de recherche sur le fon, créé pour explorer la traduction, la voix et la collecte de phrases avec les locuteurs. Ce n'est pas un produit fini : certaines réponses peuvent être imparfaites.",
  },
  {
    title: "Quatre façons de participer",
    list: [
      { label: "Histoire", detail: "Les repères historiques du Bénin." },
      {
        label: "Ma voix",
        detail: "Traduire une réplique de mission ou proposer librement ta propre phrase.",
      },
      { label: "Assistant", detail: "Parler et écouter une réponse en fon." },
      { label: "Accueil", detail: "Revenir au point de départ à tout moment." },
    ],
  },
  {
    title: "Tes contributions, tes choix",
    body:
      "Chaque enregistrement est facultatif et demande ton consentement explicite. Les données sont conservées sur le serveur du prototype pour l'évaluation et l'amélioration des outils, et restent à vérifier par des locuteurs.",
  },
];

const appStage = ref<"onboarding" | "identify" | "profile" | "writing-check" | "domains" | "ready">("ready");
const onboardingSlideIndex = ref(0);
const isLastOnboardingSlide = computed(
  () => onboardingSlideIndex.value === onboardingSlides.length - 1,
);
const speakerLabelInput = ref("");
const onboardingConsent = ref(false);
const consentAge = ref(false);
const consentProfile = ref(getConsentDetails().profile);
const consentPublication = ref(getConsentDetails().publication);
const profileAge = ref("");
const profileRegion = ref("");
const profileVariant = ref("");
const preferredDomains = ref<string[]>(getDomainPrefs());
const domainChoiceSkipped = ref(false);
const orderedDomains = computed(() => {
  const prefs = preferredDomains.value;
  return [...domains].sort((a, b) => Number(prefs.includes(b.id)) - Number(prefs.includes(a.id)));
});
const writingCheckSample = "Bonjour, comment vas-tu ?";
const writingCheckInput = ref("");
const writingCheckNudge = ref(false);
const contributionModeChoice = ref<"audio_only" | "audio_text">("audio_text");

function nextOnboardingSlide() {
  if (isLastOnboardingSlide.value) {
    goToIdentify();
    return;
  }
  onboardingSlideIndex.value += 1;
  logEvent("onboarding_step_view", { slide_index: onboardingSlideIndex.value });
}

function goToIdentify() {
  logEvent("onboarding_complete");
  appStage.value = "identify";
  speakerLabelInput.value = generateDefaultLabel();
}

function confirmIdentity() {
  if (!onboardingConsent.value || !consentAge.value) return;
  saveIdentity(speakerLabelInput.value);
  saveConsent();
  saveConsentDetails({ profile: consentProfile.value, publication: consentPublication.value });
  logEvent("identify_complete", { speaker_label: speakerLabelInput.value });
  // Le profil n'est demandé que si la personne a accepté de le partager.
  appStage.value = consentProfile.value ? "profile" : "writing-check";
}

function confirmProfile() {
  saveProfile({
    ageRange: profileAge.value,
    region: profileRegion.value.trim(),
    variant: profileVariant.value.trim(),
  });
  appStage.value = "writing-check";
}

function toggleDomainPref(id: string) {
  const list = preferredDomains.value;
  if (list.includes(id)) {
    preferredDomains.value = list.filter((x) => x !== id);
  } else if (list.length < 3) {
    preferredDomains.value = [...list, id];
  }
}

function finishDomainChoice(save: boolean) {
  if (save) saveDomainPrefs(preferredDomains.value);
  appStage.value = "ready";
  goToPendingTarget();
}

// Après le choix du mode : choix des domaines préférés (une seule fois).
function afterWritingCheck() {
  if (getDomainPrefs().length === 0 && !domainChoiceSkipped.value) {
    appStage.value = "domains";
    return;
  }
  appStage.value = "ready";
  goToPendingTarget();
}

function tryChooseAudioText() {
  if (writingCheckInput.value.trim().length < 3) {
    writingCheckNudge.value = true;
    return;
  }
  writingCheckNudge.value = false;
  contributionModeChoice.value = "audio_text";
  saveContributionMode("audio_text");
  logEvent("contribution_mode_chosen", { mode: "audio_text" });
  afterWritingCheck();
}

function chooseAudioOnly() {
  contributionModeChoice.value = "audio_only";
  saveContributionMode("audio_only");
  logEvent("contribution_mode_chosen", { mode: "audio_only" });
  afterWritingCheck();
}
const currentScreenName = computed<string | null>(() => {
  if (appStage.value !== "ready") return null;
  if (activeScreen.value === "game") return "ma_voix";
  return activeScreen.value;
});

watch(
  currentScreenName,
  (value) => {
    if (value) logEvent("screen_view", { screen: value });
  },
  { immediate: true },
);
const gameStatus = ref("");
const gameStatusType = ref<"info" | "error" | "success">("info");
const savedContributions = ref(0);

// --- Joueur : points d'effort, série, niveau (stockage local, voir gamification.ts) ---
const game = ref(loadGame());
const playerLevel = computed(() => levelFor(game.value.points));
const playerNext = computed(() => nextLevel(game.value.points));
const levelProgress = computed(() => {
  const next = playerNext.value;
  if (!next) return 100;
  const start = playerLevel.value.min;
  return Math.round(((game.value.points - start) / (next.min - start)) * 100);
});
const streakDays = computed(() => streakOf(game.value.days));
const lastAward = ref<Award | null>(null);
const levelUp = ref<Level | null>(null);
// --- Profil et suivi ---
const myContributions = ref<ContributionRecord[]>(loadContributions());
const consentView = ref(getConsentDetails());
const confirmWithdraw = ref(false);
const confirmErase = ref(false);
const speakerName = computed(() => peekSpeakerLabel() ?? "Pas encore de pseudo");
const statusLegend = [
  { key: "recu", label: "Reçu", help: "Ta contribution est bien arrivée." },
  { key: "relecture", label: "En relecture", help: "Un relecteur la regarde." },
  { key: "expert", label: "À valider par un expert", help: "Elle attend un expert de la langue." },
  { key: "valide", label: "Validé", help: "Elle est acceptée dans le corpus." },
  { key: "rejete", label: "Rejeté", help: "Elle n'a pas pu être gardée." },
] as const;

function formatContribDate(at: number): string {
  return new Date(at).toLocaleDateString("fr-FR", { day: "numeric", month: "long" });
}
function setModeChoice(mode: "audio_only" | "audio_text") {
  contributionModeChoice.value = mode;
  saveContributionMode(mode);
  logEvent("contribution_mode_chosen", { mode, from: "profile" });
}
function setOptionalConsent(key: "profile" | "publication", value: boolean) {
  consentView.value = { ...consentView.value, [key]: value };
  saveConsentDetails(consentView.value);
}
function retakeWritingTest() {
  pendingTarget.value = null;
  appStage.value = "writing-check";
}
function doWithdrawConsent() {
  withdrawConsent();
  window.location.reload();
}
function doEraseLocalData() {
  clearAllLocalData();
  window.location.reload();
}
function openProfileScreen(target: "profile" | "contributions") {
  activeScreen.value = target;
  if (target === "contributions") myContributions.value = loadContributions();
  confirmWithdraw.value = false;
  confirmErase.value = false;
  void nextTick(() => document.querySelector(".shell main")?.scrollTo({ top: 0 }));
}

const themeOptions: { v: ThemePref; label: string; icon: "auto" | "sun" | "moon" }[] = [
  { v: "auto", label: "Auto", icon: "auto" },
  { v: "light", label: "Clair", icon: "sun" },
  { v: "dark", label: "Sombre", icon: "moon" },
];

const writeOpen = ref(false);
const writeSkipped = ref(false);
const dailyMission = computed(
  () => orderedDomains.value.find((d) => (game.value.byDomain[d.id] ?? 0) < d.items.length) ?? orderedDomains.value[0] ?? null,
);

const domainIcons: Record<string, "heart" | "book" | "drum" | "leaf" | "cart" | "building" | "tools"> = {
  sante: "heart",
  education: "book",
  religion_traditions: "drum",
  agriculture: "leaf",
  commerce_marche: "cart",
  administration: "building",
  metiers_travail: "tools",
};

// Domaines verrouillés au lancement. TODO données : pas encore de contenu pour ces domaines.
const lockedDomains: { id: string; label: string; icon: "bus" | "book" | "drum" | "scroll"; level: number }[] = [
  { id: "transport_ville", label: "Transport et ville", icon: "bus", level: 3 },
  { id: "ecole_numerique", label: "École et numérique", icon: "book", level: 3 },
  { id: "ceremonies_culture", label: "Cérémonies et culture", icon: "drum", level: 3 },
  { id: "proverbes_contes", label: "Proverbes et contes", icon: "scroll", level: 4 },
];

function domainProgress(domain: Domain): number {
  const done = game.value.byDomain[domain.id] ?? 0;
  const total = domainInfo.value[domain.id]?.total ?? domain.items.length;
  return Math.min(100, Math.round((done / Math.max(1, total)) * 100));
}

function dismissLevelUp() {
  levelUp.value = null;
}
const clock = ref("");

// --- Clavier fon (champ d'essai d'écriture et « Ta traduction en fon ») :
// quand un champ fon a le focus, le clavier fon s'affiche en bas de l'écran à la
// place du clavier du téléphone (inputmode="none" sur le champ). Un clavier
// physique reste utilisable sur ordinateur. ---

const fonKbTarget = ref<HTMLTextAreaElement | null>(null);

function openFonKeyboard(event: FocusEvent) {
  const el = event.target as HTMLTextAreaElement;
  fonKbTarget.value = el;
  void nextTick(() => el.scrollIntoView({ block: "center", behavior: "smooth" }));
}

function closeFonKeyboard(event: FocusEvent) {
  if (event.target === fonKbTarget.value) fonKbTarget.value = null;
}

// Bouton « Réécouter » du clavier : l'audio lié au champ en cours d'écriture
// (ta voix pour ta traduction, la réponse du guide pour sa correction).
const fonKbListening = ref(false);
let fonKbAudio: HTMLAudioElement | null = null;
const fonKbListenUrl = computed(() => {
  const id = fonKbTarget.value?.id;
  if (id === "contribution-fon") return contributionAudioUrl.value;
  if (id === "assistant-answer") return assistantResponseAudioUrl.value;
  return null;
});

function stopFonKbAudio() {
  fonKbAudio?.pause();
  fonKbListening.value = false;
}

function toggleFonKbListen() {
  toggleListen(fonKbListenUrl.value);
}

function toggleContributionVoice() {
  toggleListen(contributionAudioUrl.value);
}

function toggleListen(url: string | null) {
  if (!url) return;
  if (fonKbListening.value) {
    stopFonKbAudio();
    return;
  }
  if (!fonKbAudio) {
    fonKbAudio = new Audio();
    fonKbAudio.addEventListener("ended", () => (fonKbListening.value = false));
  }
  if (fonKbAudio.src !== url) fonKbAudio.src = url;
  fonKbAudio.currentTime = 0;
  fonKbListening.value = true;
  void fonKbAudio.play().catch(() => (fonKbListening.value = false));
}

watch(fonKbTarget, (el) => {
  if (!el) stopFonKbAudio();
});

function onFonKey(key: FonKey) {
  const el = fonKbTarget.value;
  if (!el) return;
  if (key.kind === "close") {
    el.blur();
    return;
  }
  const start = el.selectionStart ?? el.value.length;
  const end = el.selectionEnd ?? el.value.length;
  const result = applyFonKey(el.value, start, end, key);
  if (!result) return;
  const max = el.maxLength > 0 ? el.maxLength : Infinity;
  if (result.value.length > max) return;
  // Écrit dans le champ puis émet « input » : le v-model du champ se met à jour,
  // quel que soit le champ fon ciblé.
  el.value = result.value;
  el.dispatchEvent(new Event("input", { bubbles: true }));
  void nextTick(() => el.setSelectionRange(result.cursor, result.cursor));
}

// --- Contribution zone shared by "Phrase proposée" (mission) and "Ma phrase" (free) modes ---

const contributionFrench = ref("");
const contributionFon = ref("");
const contributionAiAudioUrl = ref<string | null>(null);
const contributionAiAudioBase64 = ref<string | null>(null);
const contributionHumanAudio = ref<string | null>(null);
const contributionAudioUrl = ref<string | null>(null);
const contributionRecording = ref(false);
const contributionPlayingAi = ref(false);
const contributionRecordStatus = ref("Lis ta phrase à voix haute (obligatoire), 30 secondes maximum.");
const contributionSaving = ref(false);
const contributionSaved = ref(false);
const contributionStatus = ref("");
const contributionStatusState = ref<"info" | "error" | "success">("info");
const contributionAiAudioEl = ref<HTMLAudioElement | null>(null);

const isAudioOnlyMode = computed(() => contributionModeChoice.value === "audio_only");
// L'écriture est facultative : sans texte fon, la contribution part en mode voix seule.
const hasWrittenFon = computed(() => !isAudioOnlyMode.value && contributionFon.value.trim().length > 0);

const canSaveContribution = computed(
  () =>
    Boolean(
      contributionFrench.value.trim() &&
        contributionHumanAudio.value &&
        !contributionRecording.value &&
        !contributionSaving.value,
    ),
);

let capture: AudioCapture | null = null;
let stopTimer: ReturnType<typeof setTimeout> | null = null;
let clockTimer: ReturnType<typeof setInterval> | null = null;
let contributionRecordingStartedAt: number | null = null;

function updateClock() {
  clock.value = new Intl.DateTimeFormat("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
}

function openDomainSelector() {
  activeScreen.value = "game";
  contributionMode.value = "domain";
  selectedDomainId.value = null;
  selectedItem.value = null;
  domainStoryAcknowledged.value = false;
  itemFinished.value = false;
  setGameStatus("");
  void nextTick(() => {
    document.querySelector(".shell main")?.scrollTo({ top: 0 });
  });
}

function scrollToContribution() {
  enterApp("game");
}

function goToPendingTarget() {
  const target = pendingTarget.value;
  pendingTarget.value = null;
  if (target === "assistant") {
    activeScreen.value = "assistant";
  } else {
    openDomainSelector();
  }
}

// Porte d'entrée unique depuis l'accueil : l'onboarding (consentement, pseudo,
// choix du mode) ne s'affiche qu'au premier passage, après un appui sur JOUER.
function enterApp(target: "game" | "assistant") {
  if (!hasOnboarded() || !hasConsented()) {
    pendingTarget.value = target;
    appStage.value = "onboarding";
    onboardingSlideIndex.value = 0;
    logEvent("onboarding_step_view", { slide_index: 0 });
    return;
  }
  if (!getContributionMode()) {
    pendingTarget.value = target;
    appStage.value = "writing-check";
    return;
  }
  pendingTarget.value = target;
  goToPendingTarget();
}

function explainHowItWorks() {
  document.getElementById("xo-how")?.scrollIntoView({ behavior: "smooth", block: "start" });
}

function showHome() {
  activeScreen.value = "home";
  void nextTick(() => {
    document.querySelector(".shell main")?.scrollTo({ top: 0 });
  });
}

function startChapter() {
  enterApp("game");
}

function setGameStatus(message: string, type: "info" | "error" | "success" = "info") {
  gameStatus.value = message;
  gameStatusType.value = type;
}

function clearContributionRecording() {
  contributionHumanAudio.value = null;
  if (contributionAudioUrl.value) URL.revokeObjectURL(contributionAudioUrl.value);
  contributionAudioUrl.value = null;
}

watch(contributionFon, clearContributionRecording);

watch(contributionFrench, () => {
  contributionSaved.value = false;
  contributionStatus.value = "";
});

watch(contributionFon, () => {
  contributionSaved.value = false;
  contributionStatus.value = "";
  contributionAiAudioBase64.value = null;
  if (contributionAiAudioUrl.value) {
    URL.revokeObjectURL(contributionAiAudioUrl.value);
    contributionAiAudioUrl.value = null;
  }
});

async function playContributionAiVoice() {
  const text = contributionFon.value.trim();
  if (!text) {
    contributionRecordStatus.value = "Écris d'abord une traduction en fon.";
    return;
  }
  contributionPlayingAi.value = true;
  try {
    const response = await fetch("/training-synthesis", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ fon_text: text }),
    });
    const result: unknown = await response.json();
    const record = result as { detail?: string; audio?: string };
    if (!response.ok) throw new Error(record.detail || "La synthèse n'a pas pu être générée.");
    contributionAiAudioBase64.value = record.audio ?? null;
    const audioBytes = Uint8Array.from(atob(String(record.audio)), (character) => character.charCodeAt(0));
    if (contributionAiAudioUrl.value) URL.revokeObjectURL(contributionAiAudioUrl.value);
    contributionAiAudioUrl.value = URL.createObjectURL(new Blob([audioBytes], { type: "audio/wav" }));
    await nextTick();
    await contributionAiAudioEl.value?.play();
    contributionRecordStatus.value = "Lecture de la traduction en fon.";
  } catch (error) {
    contributionRecordStatus.value = `Erreur : ${error instanceof Error ? error.message : "erreur inconnue"}`;
  } finally {
    contributionPlayingAi.value = false;
  }
}

function encodeWav(chunks: Float32Array[], sampleRate: number): Blob {
  const frameCount = chunks.reduce((sum, chunk) => sum + chunk.length, 0);
  const buffer = new ArrayBuffer(44 + frameCount * 2);
  const view = new DataView(buffer);
  const writeText = (offset: number, text: string) => {
    for (let index = 0; index < text.length; index += 1) {
      view.setUint8(offset + index, text.charCodeAt(index));
    }
  };
  writeText(0, "RIFF");
  view.setUint32(4, buffer.byteLength - 8, true);
  writeText(8, "WAVE");
  writeText(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true);
  view.setUint16(22, 1, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  writeText(36, "data");
  view.setUint32(40, frameCount * 2, true);
  let offset = 44;
  for (const chunk of chunks) {
    for (const sample of chunk) {
      const clipped = Math.max(-1, Math.min(1, sample));
      view.setInt16(
        offset,
        clipped < 0 ? clipped * 32768 : clipped * 32767,
        true,
      );
      offset += 2;
    }
  }
  return new Blob([buffer], { type: "audio/wav" });
}

async function encodeBase64(blob: Blob): Promise<string> {
  const bytes = new Uint8Array(await blob.arrayBuffer());
  let binary = "";
  for (let offset = 0; offset < bytes.length; offset += 0x8000) {
    binary += String.fromCharCode(...bytes.subarray(offset, offset + 0x8000));
  }
  return btoa(binary);
}

async function finishContributionRecording() {
  if (!capture) return;
  if (stopTimer) clearTimeout(stopTimer);
  stopTimer = null;
  const activeCapture = capture;
  capture = null;
  contributionRecording.value = false;
  try {
    activeCapture.processor.disconnect();
    activeCapture.source.disconnect();
    activeCapture.silentOutput.disconnect();
    activeCapture.stream.getTracks().forEach((track) => track.stop());
    await activeCapture.context.close();
    if (!activeCapture.chunks.length) {
      contributionRecordStatus.value =
        "Aucun son capturé. Réessaie l'enregistrement.";
      return;
    }
    const blob = encodeWav(activeCapture.chunks, activeCapture.sampleRate);
    contributionHumanAudio.value = await encodeBase64(blob);
    contributionAudioUrl.value = URL.createObjectURL(blob);
    contributionRecordStatus.value = "Enregistrement prêt. Écoute-le avant de l'envoyer.";
    const durationSeconds = contributionRecordingStartedAt
      ? Math.round((performance.now() - contributionRecordingStartedAt) / 100) / 10
      : null;
    contributionRecordingStartedAt = null;
    logEvent("recording_complete", { screen: contributionMode.value, duration_seconds: durationSeconds });
  } catch (error) {
    contributionRecordStatus.value = `Impossible de finaliser l'enregistrement : ${error instanceof Error ? error.message : "erreur inconnue"}`;
  }
}

async function startContributionRecording() {
  // La voix passe en premier : l'écriture est facultative et vient après.
  if (!navigator.mediaDevices?.getUserMedia) {
    contributionRecordStatus.value = "L'accès au micro n'est pas disponible dans ce navigateur.";
    return;
  }
  contributionRecordStatus.value = "Demande d'accès au microphone…";
  let stream: MediaStream | null = null;
  let context: AudioContext | null = null;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      },
    });
    context = new AudioContext();
    await context.resume();
    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(4096, 1, 1);
    const silentOutput = context.createGain();
    silentOutput.gain.value = 0;
    const chunks: Float32Array[] = [];
    processor.onaudioprocess = (event) => {
      chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
    };
    source.connect(processor);
    processor.connect(silentOutput);
    silentOutput.connect(context.destination);
    capture = {
      stream,
      context,
      source,
      processor,
      silentOutput,
      chunks,
      sampleRate: context.sampleRate,
    };
    clearContributionRecording();
    contributionRecording.value = true;
    contributionRecordingStartedAt = performance.now();
    contributionRecordStatus.value = "Enregistrement… dis la phrase en fon.";
    logEvent("recording_start", { screen: contributionMode.value });
    stopTimer = setTimeout(() => void finishContributionRecording(), 30_000);
  } catch (error) {
    stream?.getTracks().forEach((track) => track.stop());
    if (context && context.state !== "closed") await context.close();
    contributionRecordStatus.value = `Impossible d'accéder au microphone : ${error instanceof Error ? error.message : "erreur inconnue"}`;
  }
}

function setContributionMode(mode: "domain" | "free") {
  if (contributionMode.value === mode) return;
  contributionMode.value = mode;
  contributionFon.value = "";
  clearContributionRecording();
  contributionStatus.value = "";
  contributionSaved.value = false;
  if (mode === "free") {
    contributionFrench.value = "";
    selectedDomainId.value = null;
    selectedItem.value = null;
  } else {
    contributionFrench.value = selectedItem.value?.text ?? "";
  }
  logEvent("mode_switch", { mode });
}

function chooseFreeDomain() {
  setContributionMode("free");
  logEvent("domain_selected", { domain_id: "libre" });
  void nextTick(() => {
    document.querySelector("#contribution")?.scrollIntoView({ behavior: "smooth" });
  });
}

watch([selectedItem, contributionMode], () => {
  writeOpen.value = false;
  writeSkipped.value = false;
});

function nextPhrase() {
  if (isLastCard.value) {
    endRound();
    return;
  }
  showCard(roundIndex.value + 1);
  void nextTick(() => document.querySelector(".shell main")?.scrollTo({ top: 0 }));
}

function localRound(domainId: string | null): RoundCard[] {
  const pool = domains
    .filter((d) => !domainId || d.id === domainId)
    .flatMap((d) =>
      d.items.map((i) => ({
        id: `local:${d.id}:${i.text}`,
        domain_id: d.id,
        domain_label: d.label,
        kind: i.kind,
        difficulty: kindToDifficulty[i.kind],
        text: i.text,
      })),
    );
  const order = { mot: 0, phrase: 1, paragraphe: 2 } as const;
  return pool
    .sort(() => Math.random() - 0.5)
    .slice(0, ROUND_SIZE)
    .sort((a, b) => order[a.kind] - order[b.kind]);
}

function showCard(i: number) {
  const card = roundCards.value[i];
  if (!card) return;
  roundIndex.value = i;
  if (domains.some((d) => d.id === card.domain_id)) selectedDomainId.value = card.domain_id;
  selectedItem.value = { id: card.id, text: card.text, kind: card.kind };
  itemFinished.value = false;
  contributionFrench.value = card.text;
  contributionFon.value = "";
  clearContributionRecording();
  lastAward.value = null;
  setGameStatus("");
  markSeen(card.id);
  logEvent("round_card_shown", { domain_id: card.domain_id, index: i });
}

async function startRound(domainId: string | null) {
  contributionMode.value = "domain";
  roundDomainId.value = domainId;
  roundSummary.value = false;
  roundError.value = "";
  roundContributed.value = 0;
  roundStreak.value = 0;
  roundPoints.value = 0;
  roundIndex.value = 0;
  roundCards.value = [];
  selectedItem.value = null;
  itemFinished.value = false;
  contributionFrench.value = "";
  contributionFon.value = "";
  clearContributionRecording();
  setGameStatus("");
  const first = domainId ? domains.find((d) => d.id === domainId) : orderedDomains.value[0];
  selectedDomainId.value = first?.id ?? null;
  domainStoryAcknowledged.value = !first || !domainId || first.mode !== "histoire";
  logEvent("round_start", { domain_id: domainId ?? "mix", level: playerLevel.value.n });
  roundLoading.value = true;
  try {
    roundCards.value = await fetchRound(domainId, playerLevel.value.n);
  } catch {
    roundCards.value = localRound(domainId);
  } finally {
    roundLoading.value = false;
  }
  if (!roundCards.value.length) {
    roundError.value = "Aucune carte disponible pour le moment.";
    return;
  }
  showCard(0);
}

function endRound() {
  roundSummary.value = true;
  selectedItem.value = null;
  itemFinished.value = false;
  contributionFrench.value = "";
  logEvent("round_end", { contributed: roundContributed.value, size: roundCards.value.length });
  void nextTick(() => document.querySelector(".shell main")?.scrollTo({ top: 0 }));
}

function selectDomainCard(domain: Domain) {
  void startRound(domain.id);
}

function acknowledgeDomainStory() {
  domainStoryAcknowledged.value = true;
}

function finishDomainItem(contributed: boolean) {
  const domain = selectedDomain.value;
  if (!domain || !selectedItem.value) return;
  itemFinished.value = true;
  if (contributed) {
    roundContributed.value += 1;
    roundStreak.value += 1;
    roundPoints.value += lastAward.value?.points ?? 0;
  } else {
    roundStreak.value = 0;
  }
  setGameStatus(
    contributed
      ? `Contribution reçue pour « ${domain.label} » ; elle reste à vérifier.`
      : "Passé sans contribuer. Aucun texte ni audio n'a été enregistré.",
    contributed ? "success" : "info",
  );
  logEvent("domain_item_complete", { domain_id: domain.id, contributed });
}

// --- Glisser la carte de la phrase (gauche ou droite) pour la passer. Le geste
// ne démarre pas sur un bouton, un champ ou un lecteur audio, et reste
// désactivé pendant un enregistrement ou un envoi. ---
const SWIPE_THRESHOLD = 90;
const swipeDx = ref(0);
const swipeLeaving = ref(false);
let swipeStart: { x: number; y: number; id: number } | null = null;
let swipeHorizontal = false;

const canSwipeSkip = computed(
  () =>
    contributionMode.value === "domain" &&
    !!selectedItem.value &&
    !itemFinished.value &&
    !contributionRecording.value &&
    !contributionSaving.value,
);
const swipeStyle = computed(() => {
  if (!swipeDx.value && !swipeLeaving.value) return undefined;
  return {
    transform: `translateX(${swipeDx.value}px) rotate(${swipeDx.value / 25}deg)`,
    opacity: String(Math.max(0.35, 1 - Math.abs(swipeDx.value) / 420)),
    transition: swipeStart ? "none" : "transform 0.22s ease, opacity 0.22s ease",
  };
});

function onSwipeDown(event: PointerEvent) {
  if (!canSwipeSkip.value || swipeLeaving.value || event.button > 0) return;
  const target = event.target as HTMLElement;
  if (target.closest("button, a, textarea, input, select, audio, label, .xo-write")) return;
  swipeStart = { x: event.clientX, y: event.clientY, id: event.pointerId };
  swipeHorizontal = false;
}

function onSwipeMove(event: PointerEvent) {
  if (!swipeStart || event.pointerId !== swipeStart.id) return;
  const dx = event.clientX - swipeStart.x;
  const dy = event.clientY - swipeStart.y;
  if (!swipeHorizontal) {
    if (Math.abs(dx) < 10) return;
    // Geste surtout vertical : on laisse défiler la page.
    if (Math.abs(dy) > Math.abs(dx)) {
      swipeStart = null;
      return;
    }
    swipeHorizontal = true;
    (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  }
  swipeDx.value = dx;
}

function onSwipeEnd() {
  if (!swipeStart) return;
  swipeStart = null;
  const dx = swipeDx.value;
  if (swipeHorizontal && Math.abs(dx) >= SWIPE_THRESHOLD && canSwipeSkip.value) {
    swipeLeaving.value = true;
    swipeDx.value = Math.sign(dx) * 520;
    window.setTimeout(() => {
      finishDomainItem(false);
      swipeDx.value = 0;
      swipeLeaving.value = false;
    }, 220);
  } else {
    swipeDx.value = 0;
  }
}

function classifySaveFailure(error: unknown): "network" | "server_error" | "validation" {
  if (error instanceof TypeError) return "network";
  const status = (error as { status?: number } | null)?.status;
  if (typeof status === "number" && status >= 400 && status < 500) return "validation";
  return "server_error";
}

async function saveContribution() {
  if (!canSaveContribution.value) return;
  if (contributionMode.value === "domain" && (!selectedItem.value || !selectedDomain.value)) return;
  contributionSaving.value = true;
  const domainId = contributionMode.value === "domain" ? selectedDomain.value?.id ?? "inconnu" : "libre";
  const contentMode = contributionMode.value === "domain" ? selectedDomain.value?.mode ?? "phrases" : "libre";
  const source = domainId;
  if (contributionMode.value === "domain") {
    setGameStatus("Envoi de la contribution au serveur du prototype…");
  } else {
    contributionStatus.value = "Envoi de la contribution au serveur du prototype…";
    contributionStatusState.value = "info";
  }
  logEvent("save_attempt", { source, domain: domainId });
  try {
    const identity = getSpeakerIdentity();
    const response = await fetch("/training-phrases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        consent: true,
        source,
        domain: domainId,
        content_mode: contentMode,
        mission_id: contributionMode.value === "domain" ? selectedDomain.value?.id ?? null : null,
        mission_title: contributionMode.value === "domain" ? selectedDomain.value?.label ?? null : null,
        difficulty:
          contributionMode.value === "domain" && selectedItem.value
            ? kindToDifficulty[selectedItem.value.kind]
            : null,
        french_text: contributionFrench.value.trim(),
        fon_text: hasWrittenFon.value ? contributionFon.value.trim() : "",
        contribution_mode: hasWrittenFon.value ? "audio_text" : "audio_only",
        human_audio: contributionHumanAudio.value,
        synthesized_audio: contributionAiAudioBase64.value,
        self_reviewed: true,
        speaker_id: identity.speakerId,
        speaker_label: identity.speakerLabel,
      }),
    });
    const data: unknown = await response.json();
    if (!response.ok) {
      const detail =
        typeof data === "object" && data !== null && "detail" in data
          ? String(data.detail)
          : "La contribution n'a pas pu être enregistrée.";
      const error = new Error(detail) as Error & { status?: number };
      error.status = response.status;
      throw error;
    }
    logEvent("save_success", { source, domain: domainId });
    const award = awardPoints(domainId, POINTS_VOICE + (hasWrittenFon.value ? POINTS_WRITE : 0));
    lastAward.value = award;
    game.value = loadGame();
    if (award.leveledUp) levelUp.value = award.leveledUp;
    addContribution({
      id: String(Date.now()),
      at: Date.now(),
      domain: domainId === "libre" ? "Phrase libre" : selectedDomain.value?.label ?? domainId,
      text: contributionFrench.value.trim(),
    });
    myContributions.value = loadContributions();
    if (contributionMode.value === "domain") {
      savedContributions.value += 1;
      finishDomainItem(true);
    } else {
      contributionSaved.value = true;
      contributionStatus.value = "Contribution enregistrée. Merci !";
      contributionStatusState.value = "success";
    }
  } catch (error) {
    const reason = classifySaveFailure(error);
    logEvent("save_failure", { source, reason });
    const message =
      reason === "network"
        ? "Ta contribution n'a pas pu être envoyée. Vérifie ta connexion internet et réessaie."
        : `Échec de l'enregistrement : ${error instanceof Error ? error.message : "erreur inconnue"}`;
    if (contributionMode.value === "domain") {
      setGameStatus(message, "error");
    } else {
      contributionStatus.value = message;
      contributionStatusState.value = "error";
    }
  } finally {
    contributionSaving.value = false;
  }
}

// --- Assistant screen (voice conversation: mic -> ASR -> LLM -> traduction -> TTS) ---

type GuideState = "idle" | "listening" | "speaking" | "processing";
type ProgressMode = "hidden" | "recording" | "indeterminate" | "complete" | "error";

const assistantLanguage = ref<"Français" | "Fon">("Français");
// La transcription de l'assistant n'est en fon que si la langue parlée est
// « Fon » : si la langue change alors que ce champ a le focus, on ouvre ou on
// ferme le clavier fon en conséquence.
watch(assistantLanguage, (language) => {
  const el = document.getElementById("assistant-transcript") as HTMLTextAreaElement | null;
  if (!el || document.activeElement !== el) return;
  fonKbTarget.value = language === "Fon" ? el : null;
});
const assistantGuideState = ref<GuideState>("idle");
const assistantRecording = ref(false);
const assistantMicDisabled = ref(false);
const assistantMicLabel = ref("Parler");
const assistantStatus = ref("Appuie sur Parler pour commencer.");
const assistantStatusState = ref<"info" | "error">("info");
const assistantProgressMode = ref<ProgressMode>("hidden");
const assistantProgressValue = ref(0);
const assistantTranscript = ref("");
const assistantAnswer = ref("");
const assistantAnswerFrench = ref("");
const assistantResponseAudioUrl = ref<string | null>(null);
const assistantShowReplay = ref(false);
const assistantResponseReady = ref(false);
const assistantAudioEl = ref<HTMLAudioElement | null>(null);

// Le consentement est donné une seule fois à la première connexion (plus de case à chaque enregistrement).
// TODO serveur : le champ `consent: true` des requêtes est toujours envoyé ; voir docs/changelog_design.md.
const assistantRecordConsent = ref(hasConsented());



let assistantCapture: AudioCapture | null = null;
let assistantProgressTimer: ReturnType<typeof setInterval> | null = null;
let assistantStageTimer: ReturnType<typeof setInterval> | null = null;
let assistantLastSpeechAt: number | undefined;
let assistantHasDetectedSpeech = false;
let assistantRecordingStartedAt: number | null = null;
let assistantResponseAudioUrlObject: string | null = null;
let assistantLastInputWav: Blob | undefined;
let assistantRawInputTranscript = "";
let assistantRawAnswer = "";

const conversationId =
  sessionStorage.getItem("fonConversationId") ??
  (() => {
    const id = crypto.randomUUID();
    sessionStorage.setItem("fonConversationId", id);
    return id;
  })();

function stopAssistantStageTimer() {
  if (assistantStageTimer) clearInterval(assistantStageTimer);
  assistantStageTimer = null;
}

function updateAssistantStage(message: string) {
  stopAssistantStageTimer();
  assistantStatus.value = message;
  assistantStatusState.value = "info";
  assistantGuideState.value = "processing";
  const stages: [string, string][] = [
    ["Chargement du modèle de reconnaissance", "Chargement du modèle"],
    ["Chargement de l'adaptateur de langue", "Chargement de l'adaptateur"],
    ["Analyse de la parole en cours", "Analyse de la parole"],
    ["Finalisation du texte reconnu", "Finalisation du texte"],
    ["Génération de la réponse", "Génération de la réponse"],
    ["Synthèse vocale de la réponse", "Synthèse de la voix"],
  ];
  const activeStage = stages.find(([prefix]) => message.startsWith(prefix));
  if (!activeStage) return;
  const startedAt = performance.now();
  assistantStageTimer = setInterval(() => {
    const elapsedSeconds = Math.floor((performance.now() - startedAt) / 1000);
    assistantStatus.value = `${activeStage[1]}… (${elapsedSeconds} s)`;
  }, 1000);
}

async function playAssistantResponse() {
  assistantShowReplay.value = false;
  assistantGuideState.value = "speaking";
  assistantMicLabel.value = "Je parle…";
  try {
    await assistantAudioEl.value?.play();
    assistantStatus.value = "Réponse en fon en cours…";
    assistantStatusState.value = "info";
  } catch {
    assistantGuideState.value = "idle";
    assistantMicLabel.value = "Parler";
    assistantShowReplay.value = true;
    assistantMicDisabled.value = false;
    assistantStatus.value = "La réponse est prête. Clique sur « Écouter la réponse ».";
  }
}

function onAssistantAudioEnded() {
  assistantMicDisabled.value = false;
  assistantMicLabel.value = "Parler";
  assistantGuideState.value = "idle";
  assistantStatus.value = "À toi de parler.";
  assistantStatusState.value = "info";
}

async function startAssistantRecording() {
  assistantMicDisabled.value = true;
  assistantAudioEl.value?.pause();
  assistantGuideState.value = "idle";
  assistantMicLabel.value = "Connexion…";
  assistantResponseReady.value = false;
  assistantLastInputWav = undefined;
  assistantRawInputTranscript = "";
  assistantRawAnswer = "";
  if (assistantResponseAudioUrlObject) URL.revokeObjectURL(assistantResponseAudioUrlObject);
  assistantResponseAudioUrlObject = null;
  assistantResponseAudioUrl.value = null;
  assistantProgressMode.value = "hidden";
  assistantTranscript.value = "";
  assistantAnswer.value = "";
  assistantAnswerFrench.value = "";
  assistantStatus.value = "Connexion au microphone…";
  assistantStatusState.value = "info";
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    const context = new AudioContext();
    await context.resume();
    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(4096, 1, 1);
    const silentOutput = context.createGain();
    silentOutput.gain.value = 0;
    const chunks: Float32Array[] = [];
    processor.onaudioprocess = (event) => {
      const samples = new Float32Array(event.inputBuffer.getChannelData(0));
      chunks.push(samples);
      let energy = 0;
      for (const sample of samples) energy += sample * sample;
      const rms = Math.sqrt(energy / samples.length);
      if (rms >= 0.018) {
        if (!assistantHasDetectedSpeech) {
          assistantStatus.value = "Parole détectée. L'envoi se fera après une courte pause.";
        }
        assistantHasDetectedSpeech = true;
        assistantLastSpeechAt = performance.now();
      }
    };
    source.connect(processor);
    processor.connect(silentOutput);
    silentOutput.connect(context.destination);
    assistantCapture = { stream, context, source, processor, silentOutput, chunks, sampleRate: context.sampleRate };
    const recordingStartedAt = performance.now();
    assistantRecordingStartedAt = recordingStartedAt;
    assistantLastSpeechAt = undefined;
    assistantHasDetectedSpeech = false;
    assistantRecording.value = true;
    assistantProgressMode.value = "recording";
    assistantProgressValue.value = 0;
    assistantGuideState.value = "listening";
    assistantMicLabel.value = "Je t'écoute…";
    assistantMicDisabled.value = false;
    assistantStatus.value = "Parle normalement. J'enverrai après 1,5 seconde de silence.";
    logEvent("recording_start", { screen: "assistant" });
    assistantProgressTimer = setInterval(() => {
      const elapsedSeconds = Math.min(30, (performance.now() - recordingStartedAt) / 1000);
      assistantProgressValue.value = (elapsedSeconds / 30) * 100;
      if (
        assistantHasDetectedSpeech &&
        assistantLastSpeechAt &&
        performance.now() - assistantLastSpeechAt >= 1500
      ) {
        assistantStatus.value = "Silence détecté. Envoi de ta phrase…";
        void stopAssistantRecording();
        return;
      }
      if (elapsedSeconds >= 30) {
        assistantStatus.value = "Limite de 30 secondes atteinte. Envoi de ta phrase…";
        void stopAssistantRecording();
      }
    }, 100);
  } catch (error) {
    if (assistantProgressTimer) clearInterval(assistantProgressTimer);
    assistantProgressTimer = null;
    assistantMicDisabled.value = false;
    assistantMicLabel.value = "Parler";
    assistantGuideState.value = "idle";
    assistantProgressMode.value = "hidden";
    assistantStatus.value = `Impossible d'accéder au micro : ${error instanceof Error ? error.message : "erreur inconnue"}`;
    assistantStatusState.value = "error";
  }
}

async function stopAssistantRecording() {
  if (!assistantCapture) return;
  const active = assistantCapture;
  assistantCapture = null;
  assistantRecording.value = false;
  assistantMicDisabled.value = true;
  if (assistantProgressTimer) clearInterval(assistantProgressTimer);
  assistantProgressTimer = null;
  assistantMicLabel.value = "Envoi…";
  assistantGuideState.value = "processing";
  try {
    active.processor.disconnect();
    active.source.disconnect();
    active.silentOutput.disconnect();
    const sampleRate = active.context.sampleRate;
    await active.context.close();
    active.stream.getTracks().forEach((track) => track.stop());

    if (!assistantHasDetectedSpeech) {
      assistantMicDisabled.value = false;
      assistantMicLabel.value = "Parler";
      assistantGuideState.value = "idle";
      assistantProgressMode.value = "hidden";
      assistantStatus.value = "Je n'ai pas détecté de parole. Réessaie en parlant près du micro.";
      assistantStatusState.value = "error";
      return;
    }

    const wav = encodeWav(active.chunks, sampleRate);
    assistantLastInputWav = wav;
    const durationSeconds = assistantRecordingStartedAt
      ? Math.round((performance.now() - assistantRecordingStartedAt) / 100) / 10
      : null;
    assistantRecordingStartedAt = null;
    logEvent("recording_complete", { screen: "assistant", duration_seconds: durationSeconds });
    assistantProgressMode.value = "indeterminate";
    assistantStatus.value = "Transcription locale en cours…";
    assistantStatusState.value = "info";

    logEvent("assistant_question_asked", { language: assistantLanguage.value });
    const response = await fetch(`/voice-turn?language=${encodeURIComponent(assistantLanguage.value)}`, {
      method: "POST",
      headers: { "Content-Type": "audio/wav", "X-Conversation-Id": conversationId },
      body: wav,
    });
    if (!response.ok) {
      const errorResult = await response.json();
      throw new Error(errorResult.detail || "L'échange vocal a échoué.");
    }
    if (!response.body) throw new Error("Le serveur n'a pas démarré l'échange vocal.");

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    let completedTurn = false;
    const handleEvent = (event: Record<string, unknown>) => {
      if (event.type === "progress") {
        updateAssistantStage(String(event.message));
      } else if (event.type === "transcript") {
        assistantRawInputTranscript = String(event.text);
        assistantTranscript.value = String(event.text);
        updateAssistantStage("Transcription terminée. Envoi au modèle…");
      } else if (event.type === "done") {
        completedTurn = true;
        stopAssistantStageTimer();
        assistantRawAnswer = String(event.fon_answer);
        assistantAnswer.value = String(event.fon_answer);
        const audioBytes = Uint8Array.from(
          atob(String(event.audio)),
          (character) => character.charCodeAt(0),
        );
        if (assistantResponseAudioUrlObject) URL.revokeObjectURL(assistantResponseAudioUrlObject);
        assistantResponseAudioUrlObject = URL.createObjectURL(new Blob([audioBytes], { type: "audio/wav" }));
        assistantResponseAudioUrl.value = assistantResponseAudioUrlObject;
        assistantAnswerFrench.value = String(event.french_answer ?? "");
        assistantProgressMode.value = "complete";
        assistantProgressValue.value = 100;
        assistantResponseReady.value = true;
        logEvent("assistant_answer_received");
        void nextTick(() => void playAssistantResponse());
        if (assistantRecordConsent.value) void silentlySaveAssistantExample();
      } else if (event.type === "error") {
        throw new Error(String(event.message));
      }
    };
    while (true) {
      const { value, done } = await reader.read();
      buffer += decoder.decode(value || new Uint8Array(), { stream: !done });
      const messages = buffer.split("\n\n");
      buffer = messages.pop() || "";
      for (const message of messages) {
        const dataLine = message.split("\n").find((line) => line.startsWith("data:"));
        if (dataLine) handleEvent(JSON.parse(dataLine.slice(5).trim()));
      }
      if (done) break;
    }
    if (buffer.startsWith("data:")) handleEvent(JSON.parse(buffer.slice(5).trim()));
    if (!completedTurn) throw new Error("L'assistant n'a pas terminé sa réponse.");
  } catch (error) {
    stopAssistantStageTimer();
    assistantGuideState.value = "idle";
    assistantMicLabel.value = "Parler";
    assistantProgressMode.value = "error";
    assistantStatus.value = `Erreur : ${error instanceof Error ? error.message : "erreur inconnue"}`;
    assistantStatusState.value = "error";
    assistantMicDisabled.value = false;
  } finally {
    stopAssistantStageTimer();
  }
}

// Logs the raw question (audio + transcript) in the background for ASR research,
// only when the user opted in via assistantRecordConsent. The AI-generated fon
// answer is stored alongside for reference but is never presented to the user
// as "their" contribution — see contributeAssistantAnswer() for that path.
async function silentlySaveAssistantExample() {
  if (!assistantLastInputWav) return;
  try {
    const identity = getSpeakerIdentity();
    await fetch("/training-examples", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        consent: true,
        language: assistantLanguage.value,
        input_audio: await encodeBase64(assistantLastInputWav),
        asr_transcript: assistantRawInputTranscript,
        input_transcript: assistantRawInputTranscript,
        assistant_fon_text_original: assistantRawAnswer,
        assistant_fon_text: assistantRawAnswer,
        speaker_id: identity.speakerId,
        speaker_label: identity.speakerLabel,
      }),
    });
  } catch {
    // Best-effort background logging: failures are not surfaced to the user.
  }
}

function contributeAssistantAnswer() {
  logEvent("assistant_followup_clicked");
  activeScreen.value = "game";
  contributionMode.value = "free";
  contributionFrench.value = assistantAnswerFrench.value.trim();
  contributionFon.value = isAudioOnlyMode.value ? "" : assistantAnswer.value.trim();
  clearContributionRecording();
  contributionStatus.value = "";
  contributionSaved.value = false;
  void nextTick(() => {
    document.querySelector("#contribution")?.scrollIntoView({ behavior: "smooth" });
  });
}

const { canInstall, installed, isIosManualInstall, promptInstall } = usePwaInstall();
const installStatus = ref("");

async function handleInstallClick() {
  const accepted = await promptInstall();
  installStatus.value = accepted
    ? "Application installée."
    : "Installation annulée. Tu peux réessayer à tout moment.";
}

onMounted(() => {
  fetchDomainInfo()
    .then((list) => {
      domainInfo.value = Object.fromEntries(list.map((d) => [d.id, d]));
    })
    .catch(() => {
      // sans serveur de contenu : on garde les totaux embarqués
    });
  window.addEventListener("keydown", onGlobalKeydown);
  logEvent("app_open");
  updateClock();
  clockTimer = setInterval(updateClock, 60_000);
  const params = new URLSearchParams(window.location.search);
  const requestedScreen = params.get("screen");
  if (requestedScreen === "assistant") {
    activeScreen.value = "assistant";
  } else if (requestedScreen === "game" && params.get("mode") === "free") {
    activeScreen.value = "game";
    setContributionMode("free");
  }
  if (!requestedScreen) {
    // Visite normale : l'accueil est la première page, sans onboarding forcé.
    const storedMode = getContributionMode();
    if (storedMode) contributionModeChoice.value = storedMode;
  } else if (!hasOnboarded() || !hasConsented()) {
    appStage.value = "onboarding";
    onboardingSlideIndex.value = 0;
    logEvent("onboarding_step_view", { slide_index: 0 });
  } else {
    const storedMode = getContributionMode();
    if (!storedMode) {
      appStage.value = "writing-check";
    } else {
      contributionModeChoice.value = storedMode;
    }
  }
  if (isIosManualInstall && !installed.value) {
    logEvent("ios_manual_banner_shown");
  }
});

onBeforeUnmount(() => {
  window.removeEventListener("keydown", onGlobalKeydown);
  if (clockTimer) clearInterval(clockTimer);
  if (stopTimer) clearTimeout(stopTimer);
  if (contributionAudioUrl.value) URL.revokeObjectURL(contributionAudioUrl.value);
  if (contributionAiAudioUrl.value) URL.revokeObjectURL(contributionAiAudioUrl.value);
  if (capture) {
    capture.stream.getTracks().forEach((track) => track.stop());
    void capture.context.close();
  }
  stopAssistantStageTimer();
  if (assistantProgressTimer) clearInterval(assistantProgressTimer);
  if (assistantResponseAudioUrlObject) URL.revokeObjectURL(assistantResponseAudioUrlObject);
  if (assistantCapture) {
    assistantCapture.stream.getTracks().forEach((track) => track.stop());
    void assistantCapture.context.close();
  }
});
</script>

<template>
  <div class="shell">
    <div class="phone-status" aria-label="Barre d'état">
      <span>{{ clock }}</span>
      <span class="phone-status-icons" aria-hidden="true">
        <span class="signal-icon">●●●</span>
        <span class="wifi-icon">⌁</span>
        <span class="battery-icon"><span></span></span>
      </span>
    </div>

    <main v-if="appStage === 'onboarding'" class="onboarding-screen xo-stage">
      <div class="xo-zigzag" aria-hidden="true"></div>
      <XoCube />
      <section v-xo-tilt class="card onboarding-card">
        <span class="eyebrow">Avant de commencer</span>
        <h1>{{ onboardingSlides[onboardingSlideIndex].title }}</h1>
        <p v-if="onboardingSlides[onboardingSlideIndex].body" class="story-copy">
          {{ onboardingSlides[onboardingSlideIndex].body }}
        </p>
        <ul v-if="onboardingSlides[onboardingSlideIndex].list" class="onboarding-list">
          <li v-for="item in onboardingSlides[onboardingSlideIndex].list" :key="item.label">
            <strong :class="{ dominant: item.label === 'Ma voix' }">{{ item.label }}</strong>
            <span>{{ item.detail }}</span>
          </li>
        </ul>
        <div class="onboarding-dots" aria-hidden="true">
          <span
            v-for="(slide, index) in onboardingSlides"
            :key="slide.title"
            :class="{ 'is-active': index === onboardingSlideIndex }"
          ></span>
        </div>
        <div class="onboarding-actions">
          <button
            v-if="!isLastOnboardingSlide"
            class="button button-secondary"
            type="button"
            @click="goToIdentify"
          >
            Passer
          </button>
          <button class="button" type="button" @click="nextOnboardingSlide">
            {{ isLastOnboardingSlide ? "Commencer" : "Suivant" }}
          </button>
        </div>
      </section>
    </main>

    <main v-else-if="appStage === 'identify'" class="onboarding-screen xo-stage">
      <div class="xo-zigzag" aria-hidden="true"></div>
      <XoCube />
      <section v-xo-tilt class="card onboarding-card">
        <span class="eyebrow">Avant de commencer</span>
        <h1>Choisis un pseudonyme</h1>
        <p class="story-copy">
          Ce pseudonyme permet de regrouper tes contributions entre elles, sans révéler ton
          identité. Tu peux garder celui proposé ou en choisir un autre.
        </p>
        <label class="prompt-label" for="speaker-label">Ton pseudonyme</label>
        <input
          id="speaker-label"
          v-model="speakerLabelInput"
          type="text"
          maxlength="60"
          placeholder="Voix-0000"
        />
        <fieldset class="xo-consents">
          <legend class="prompt-label">Ton accord, case par case</legend>
          <label class="consent xo-consent">
            <input v-model="consentAge" type="checkbox" />
            <span><b>J'ai 18 ans ou plus.</b> <em>Obligatoire</em></span>
          </label>
          <label class="consent xo-consent">
            <input v-model="onboardingConsent" type="checkbox" />
            <span>
              <b>Ma voix et mes textes.</b> <em>Obligatoire</em><br />
              J'accepte que mes enregistrements et les phrases que j'écris servent à entraîner des
              modèles de reconnaissance et de synthèse vocale du fon. Ils sont gardés sur le serveur
              du prototype et vérifiés par des locuteurs. Je n'enregistre que ma propre voix.
            </span>
          </label>
          <label class="consent xo-consent">
            <input v-model="consentProfile" type="checkbox" />
            <span>
              <b>Mon profil.</b> <em>Facultatif</em><br />
              J'accepte de donner mon âge, ma région et ma variante de fon, pour mieux comprendre les voix.
            </span>
          </label>
          <label class="consent xo-consent">
            <input v-model="consentPublication" type="checkbox" />
            <span>
              <b>Un jeu de données ouvert.</b> <em>Facultatif</em><br />
              J'accepte que mes contributions validées soient publiées dans un jeu de données ouvert.
            </span>
          </label>
          <p class="hint">
            Tu peux retirer ton accord ou supprimer tes enregistrements à tout moment en écrivant au
            responsable du projet. Ces choix valent pour cet appareil.
          </p>
        </fieldset>
        <div class="onboarding-actions">
          <button class="button" type="button" :disabled="!onboardingConsent || !consentAge" @click="confirmIdentity">
            Continuer
          </button>
        </div>
      </section>
    </main>

    <main v-else-if="appStage === 'profile'" class="onboarding-screen xo-stage">
      <div class="xo-zigzag" aria-hidden="true"></div>
      <XoCube />
      <section v-xo-tilt class="card onboarding-card">
        <span class="eyebrow">Profil · facultatif</span>
        <h1>Dis-nous qui tu es</h1>
        <p class="story-copy">Tout est facultatif. Ces infos aident à comprendre les différentes façons de parler le fon.</p>
        <label class="prompt-label" for="profile-age">Ta tranche d'âge</label>
        <select id="profile-age" v-model="profileAge" class="xo-select">
          <option value="">Je préfère ne pas dire</option>
          <option value="18-24">18 à 24 ans</option>
          <option value="25-34">25 à 34 ans</option>
          <option value="35-49">35 à 49 ans</option>
          <option value="50+">50 ans et plus</option>
        </select>
        <label class="prompt-label" for="profile-region">Ta région</label>
        <input id="profile-region" v-model="profileRegion" class="xo-input" type="text" maxlength="60" placeholder="Ex. : Atlantique, Zou, Ouémé…" />
        <label class="prompt-label" for="profile-variant">Ta variante de fon</label>
        <input id="profile-variant" v-model="profileVariant" class="xo-input" type="text" maxlength="60" placeholder="Si tu la connais" />
        <div class="onboarding-actions">
          <button class="button button-secondary" type="button" @click="appStage = 'writing-check'">Passer</button>
          <button class="button" type="button" @click="confirmProfile">Continuer</button>
        </div>
      </section>
    </main>

    <main v-else-if="appStage === 'domains'" class="onboarding-screen xo-stage">
      <div class="xo-zigzag" aria-hidden="true"></div>
      <section v-xo-tilt class="card onboarding-card">
        <span class="eyebrow">Dernière étape</span>
        <h1>Tes domaines préférés</h1>
        <p class="story-copy">Choisis 2 ou 3 sujets qui te parlent. Tu les verras en premier.</p>
        <div class="xo-pick-grid" role="group" aria-label="Domaines préférés, 3 au maximum">
          <button
            v-for="(domain, i) in domains"
            :key="domain.id"
            type="button"
            class="xo-pick"
            :class="{ 'is-picked': preferredDomains.includes(domain.id) }"
            :style="{ '--tilt': ((i % 3) - 1) * 2 + 'deg' }"
            :aria-pressed="preferredDomains.includes(domain.id)"
            :disabled="!preferredDomains.includes(domain.id) && preferredDomains.length >= 3"
            @click="toggleDomainPref(domain.id)"
          >
            <XoIcon v-if="preferredDomains.includes(domain.id)" name="check" />
            <span>{{ domain.label }}</span>
          </button>
        </div>
        <p class="hint" role="status">{{ preferredDomains.length }} sur 3 choisis</p>
        <div class="onboarding-actions">
          <button class="button button-secondary" type="button" @click="domainChoiceSkipped = true; finishDomainChoice(false)">Passer</button>
          <button class="button" type="button" :disabled="preferredDomains.length < 2" @click="finishDomainChoice(true)">C'est parti</button>
        </div>
      </section>
    </main>

    <main v-else-if="appStage === 'writing-check'" class="onboarding-screen xo-stage">
      <div class="xo-zigzag" aria-hidden="true"></div>
      <XoCube />
      <section v-xo-tilt class="card onboarding-card">
        <span class="eyebrow">Avant de commencer</span>
        <h1>Comment veux-tu contribuer ?</h1>
        <p class="story-copy">
          Le fon se parle avant tout à l'oral. Si tu es plus à l'aise pour parler que pour
          écrire, tu peux contribuer uniquement avec ta voix : le champ d'écriture ne te sera
          jamais demandé.
        </p>
        <span class="prompt-label">Essaie d'écrire une traduction</span>
        <p class="locked-text">{{ writingCheckSample }}</p>
        <label class="prompt-label" for="writing-check-input">Essaie d'écrire ta traduction en fon</label>
        <textarea
          id="writing-check-input"
          v-model="writingCheckInput"
          class="xo-fon"
          lang="fon"
          inputmode="none"
          rows="2"
          maxlength="200"
          placeholder="Touche ici pour ouvrir le clavier fon…"
          @focus="openFonKeyboard"
          @blur="closeFonKeyboard"
        ></textarea>
        <p class="hint">
          Ceci n'est pas noté ni corrigé automatiquement : personne ne vérifie l'orthographe,
          c'est juste pour t'aider à savoir ce qui te convient le mieux.
        </p>
        <p v-if="writingCheckNudge" class="hint" role="status">
          Essaie d'abord d'écrire quelque chose ci-dessus, même une tentative.
        </p>
        <div class="onboarding-actions">
          <button class="button button-secondary" type="button" @click="chooseAudioOnly">
            Je préfère parler seulement
          </button>
          <button class="button" type="button" @click="tryChooseAudioText">
            Je préfère parler et écrire
          </button>
        </div>
      </section>
    </main>

    <template v-else>
    <header>
      <div class="brand">
        <span class="brand-mark" aria-hidden="true"><XoLogo :size="44" /></span>
        <div>
          <strong>Le carnet des voix</strong>
          <span>Bénin · une aventure en fon</span>
        </div>
      </div>
    </header>

    <main v-if="activeScreen === 'home'" class="welcome-screen xo-home">
      <button
        v-if="canInstall && !installed"
        class="install-banner"
        type="button"
        @click="handleInstallClick"
      >
        <span class="install-banner-icon" aria-hidden="true">⇩</span>
        <span class="install-banner-copy">
          <strong>Installer Le carnet des voix</strong>
          <small>Ajoute l'application à ton écran d'accueil, utilisable même hors connexion.</small>
        </span>
        <span class="install-banner-arrow" aria-hidden="true">→</span>
      </button>
      <p v-if="installStatus" class="install-status" role="status">{{ installStatus }}</p>
      <div v-if="isIosManualInstall && !installed" class="install-banner install-banner-ios">
        <span class="install-banner-icon" aria-hidden="true">⬆︎</span>
        <span class="install-banner-copy">
          <strong>Installer sur cet iPhone</strong>
          <small>Appuie sur <b>Partager</b> (le carré avec la flèche) en bas de Safari, puis <b>« Sur l'écran d'accueil »</b>.</small>
        </span>
      </div>
      <div class="xo-zigzag xo-home-zz" aria-hidden="true"></div>

      <section class="xo-home-hero">
        <XoLeaf class="xo-leaf-deco xo-leaf-deco--l" />
        <XoLeaf class="xo-leaf-deco xo-leaf-deco--sm xo-leaf-deco--r" />
        <span class="xo-home-kicker">Bénin · langue fon</span>
        <XoCube class="xo-home-cube" />
        <h1 class="xo-home-title">Fais entendre <span>ta voix</span></h1>
        <p class="xo-home-lead">
          Parle, écoute et écris le fon. Chaque phrase que tu donnes aide les ordinateurs à comprendre ta langue.
        </p>
        <button class="xo-home-play" type="button" @click="startChapter">
          <span class="xo-home-play-mic" aria-hidden="true">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>
          </span>
          <span class="xo-home-play-label">Jouer</span>
          <span class="xo-home-play-hint">C'est gratuit · 2 minutes</span>
        </button>
        <button class="xo-home-link" type="button" @click="explainHowItWorks">Comment ça marche ?</button>
      </section>

      <!-- TODO données : compteurs (voix, phrases, Gardiens) à ajouter quand les vraies valeurs existent -->
      <section id="xo-how" class="xo-home-how" aria-labelledby="xo-how-title">
        <h2 id="xo-how-title" class="xo-home-h2">3 gestes, c'est tout</h2>
        <ol class="xo-home-steps">
          <li v-xo-tilt class="xo-home-step" style="--tilt: -2.5deg">
            <span class="xo-home-step-n" aria-hidden="true">1</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 6h16M4 12h10M4 18h13" /></svg>
            <h3>Choisis</h3>
            <p>Un domaine qui te parle : marché, santé, famille…</p>
          </li>
          <li v-xo-tilt class="xo-home-step xo-home-step--yellow" style="--tilt: 2deg">
            <span class="xo-home-step-n" aria-hidden="true">2</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" /></svg>
            <h3>Parle</h3>
            <p>Lis la phrase, appuie sur le micro et dis-la en fon.</p>
          </li>
          <li v-xo-tilt class="xo-home-step xo-home-step--leaf" style="--tilt: -1.5deg">
            <span class="xo-home-step-n" aria-hidden="true">3</span>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z" /></svg>
            <h3>Gagne</h3>
            <p>Des points à chaque voix, puis un niveau de plus.</p>
          </li>
        </ol>
      </section>

      <div class="xo-zigzag xo-zigzag--thin xo-zigzag--leaf xo-home-zz" aria-hidden="true"></div>

      <button class="xo-home-assistant" type="button" @click="enterApp('assistant')">
        <span class="xo-home-assistant-icon" aria-hidden="true">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 5h16v11H9l-5 4z" /></svg>
        </span>
        <span>
          <strong>Une question sur le jeu ?</strong>
          <small>Demande à ton guide.</small>
        </span>
        <span aria-hidden="true">→</span>
      </button>

      <p class="xo-home-note">
        Tes enregistrements restent à vérifier par des locuteurs avant tout usage. Tu peux les retirer à tout moment.
      </p>
    </main>

    <main v-else-if="activeScreen === 'game'">
      <button
        v-if="contributionMode === 'free'"
        class="history-toggle"
        type="button"
        @click="openDomainSelector"
      >
        <span aria-hidden="true">←</span> Retour aux domaines
      </button>

      <template v-if="contributionMode === 'domain'">
      <section v-if="!selectedDomain" class="xo-play">
        <div class="xo-hud" aria-label="Ta progression">
          <div class="xo-hud-top">
            <span class="xo-level"><b>{{ playerLevel.n }}</b> {{ playerLevel.name }}</span>
            <span class="xo-chip"><XoIcon name="flame" /> {{ streakDays }} jour{{ streakDays > 1 ? "s" : "" }}</span>
            <span class="xo-chip"><XoIcon name="star" /> {{ game.points }} pts</span>
          </div>
          <div class="xo-progress" role="progressbar" aria-label="Progression vers le niveau suivant" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="levelProgress">
            <span :style="{ width: levelProgress + '%' }"></span>
          </div>
          <p class="xo-hud-next">
            {{ playerNext ? `Encore ${playerNext.min - game.points} points pour « ${playerNext.name} »` : "Niveau maximum atteint" }}
          </p>
        </div>

        <article v-if="dailyMission" v-xo-tilt class="xo-daily">
          <span class="xo-daily-tag">Mission du jour</span>
          <h2>{{ dailyMission.label }}</h2>
          <p>Dis une phrase en fon. Environ 2 minutes, +{{ POINTS_VOICE }} points.</p>
          <button class="button" type="button" @click="selectDomainCard(dailyMission)">Commencer</button>
        </article>

        <button class="xo-mix" type="button" @click="startRound(null)">
          <span class="xo-mix-icon"><XoIcon name="play" /></span>
          <span>
            <strong>Lancer une partie</strong>
            <small>{{ ROUND_SIZE }} cartes au hasard, tous domaines mélangés.</small>
          </span>
        </button>

        <h2 class="xo-play-h2">Ou choisis un domaine</h2>
        <div class="xo-domain-grid" role="list" aria-label="Domaines à explorer">
          <button
            v-for="(domain, i) in orderedDomains"
            :key="domain.id"
            class="xo-dcard"
            :class="{ 'xo-dcard--leaf': domain.id === 'agriculture' }"
            type="button"
            role="listitem"
            :style="{ '--tilt': ((i % 2) * 2 - 1) * 1.5 + 'deg' }"
            @click="selectDomainCard(domain)"
          >
            <span class="xo-dcard-icon"><XoIcon :name="domainIcons[domain.id] ?? 'star'" /></span>
            <span v-if="preferredDomains.includes(domain.id)" class="xo-foryou">Pour toi</span>
            <span class="xo-dcard-label">{{ domain.label }}</span>
            <span class="xo-dcard-mode">{{ domain.mode === "histoire" ? "Avec une histoire" : "Mots et phrases" }}</span>
            <span class="xo-progress" role="progressbar" :aria-label="`Progression ${domain.label}`" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="domainProgress(domain)">
              <span :style="{ width: domainProgress(domain) + '%' }"></span>
            </span>
          </button>
          <div
            v-for="locked in lockedDomains"
            :key="locked.id"
            class="xo-dcard xo-dcard--locked"
            role="listitem"
            aria-disabled="true"
          >
            <span class="xo-dcard-icon"><XoIcon name="lock" /></span>
            <span class="xo-dcard-label">{{ locked.label }}</span>
            <span class="xo-dcard-mode">{{ playerLevel.n >= locked.level ? "Bientôt disponible" : `Niveau ${locked.level} requis` }}</span>
          </div>
        </div>
        <button class="xo-free" type="button" @click="chooseFreeDomain">
          <span class="xo-dcard-icon"><XoIcon name="pen" /></span>
          <span>
            <strong>Ta propre phrase</strong>
            <small>Propose une phrase qui n'est dans aucun domaine.</small>
          </span>
        </button>
      </section>

      <section
        v-else-if="selectedDomain.mode === 'histoire' && !domainStoryAcknowledged"
        id="mission"
        class="game-screen"
        aria-live="polite"
      >
        <button class="history-toggle" type="button" @click="openDomainSelector">
          <span aria-hidden="true">←</span> Changer de domaine
        </button>
        <div class="dialogue-box">
          <svg class="radio-avatar" viewBox="0 0 64 64" role="img" aria-label="Mina, animatrice béninoise fictive">
            <defs>
              <linearGradient id="mina-skin" x2="1" y2="1">
                <stop stop-color="#805038" />
                <stop offset="1" stop-color="#4a2d24" />
              </linearGradient>
            </defs>
            <rect width="64" height="64" fill="#F5E8C9" />
            <path d="M7 64q2-21 25-23 23 2 26 23Z" fill="#F5B82E" />
            <path d="m22 42 10 10 10-10" fill="none" stroke="#f8dfae" stroke-width="2" />
            <path d="M25 35h14v12H25z" fill="#573627" />
            <ellipse cx="32" cy="27" rx="18" ry="21" fill="url(#mina-skin)" />
            <path d="M14 28Q10 7 28 5q20-3 23 15l-4 12q-4-10-12-12-9 5-19 1Z" fill="#211c20" />
            <path d="M17 18q3-11 13-11m7 0q7 2 10 9" fill="none" stroke="#39292a" stroke-linecap="round" stroke-width="3" />
            <path d="M21 25q4-3 8 0m8 0q4-3 8 0" fill="none" stroke="#21191b" stroke-linecap="round" stroke-width="1.5" />
            <ellipse cx="25" cy="29" rx="1.7" ry="2.1" fill="#f3e5d4" />
            <ellipse cx="39" cy="29" rx="1.7" ry="2.1" fill="#f3e5d4" />
            <circle cx="25" cy="29" r=".9" fill="#181719" />
            <circle cx="39" cy="29" r=".9" fill="#181719" />
            <path d="M31 30q-2 6 1 7" fill="none" stroke="#392924" stroke-width="1.5" stroke-linecap="round" />
            <path d="M27 39q5 4 10 0" fill="none" stroke="#f0b5a2" stroke-width="1.8" stroke-linecap="round" />
            <circle cx="13" cy="33" r="2" fill="#e5b55d" />
            <circle cx="51" cy="33" r="2" fill="#e5b55d" />
          </svg>
          <div class="dialogue-content">
            <div class="dialogue-name">
              <span>Mina</span>
              <span class="speaker-role">{{ selectedDomain.story?.kicker }}</span>
            </div>
            <p>{{ selectedDomain.story?.body }}</p>
          </div>
          <span class="dialogue-caret" aria-hidden="true">▼</span>
        </div>

        <div class="mission-card">
          <div class="mission-heading">
            <div>
              <span class="eyebrow">{{ selectedDomain.label }}</span>
              <h2>{{ selectedDomain.story?.title }}</h2>
            </div>
          </div>
          <div class="actions">
            <button class="button" type="button" @click="acknowledgeDomainStory">
              Continuer →
            </button>
          </div>
        </div>
      </section>

      <section v-else-if="roundSummary" class="card result xo-result xo-round-end" aria-live="polite">
        <div class="xo-result-burst" aria-hidden="true"><XoIcon name="star" /></div>
        <span class="xo-kicker xo-kicker--dark">Manche terminée</span>
        <h2>{{ roundVerdictText.title }}</h2>
        <p class="xo-round-score"><b>{{ roundContributed }}</b> / {{ roundCards.length }} <small>cartes dites</small></p>
        <p class="xo-points">+{{ roundPoints }} <small>points d'effort</small></p>
        <p class="story-copy">{{ roundVerdictText.text }}</p>
        <p class="hint">Les propositions en fon restent à vérifier par des locuteurs.</p>
        <div class="actions">
          <button class="button" type="button" @click="startRound(roundDomainId)">Manche suivante</button>
          <button class="button button-secondary" type="button" @click="openDomainSelector">Autres domaines</button>
        </div>
      </section>

      <section v-else-if="!itemFinished" id="mission" class="game-screen" aria-live="polite">
        <button class="history-toggle" type="button" @click="openDomainSelector">
          <span aria-hidden="true">←</span> Quitter la manche
        </button>
        <div v-if="roundLoading" class="xo-round xo-round--loading" role="status">
          <span class="xo-spinner" aria-hidden="true"></span>
          <strong>Je prépare tes cartes…</strong>
        </div>
        <div v-else-if="roundError" class="xo-round" role="alert">
          <strong>{{ roundError }}</strong>
          <button class="button" type="button" @click="startRound(roundDomainId)">Réessayer</button>
        </div>
        <div v-else-if="currentCard" class="xo-round">
          <div class="xo-round-top">
            <span class="xo-round-count">Carte {{ roundIndex + 1 }} sur {{ roundCards.length }}</span>
            <span v-if="roundStreak >= 2" class="xo-round-streak"><XoIcon name="flame" /> {{ roundStreak }} d'affilée</span>
          </div>
          <ol class="xo-dots" aria-hidden="true">
            <li
              v-for="(card, n) in roundCards"
              :key="card.id"
              :class="{ 'is-done': n < roundIndex, 'is-now': n === roundIndex }"
            ></li>
          </ol>
          <p v-if="roundStreak >= 1" class="xo-round-cheer">{{ roundCheer }}</p>
        </div>
      </section>

      <section v-else class="card result xo-result">
        <div class="xo-result-burst" aria-hidden="true"><XoIcon name="star" /></div>
        <span class="xo-kicker xo-kicker--dark">Carte {{ roundIndex + 1 }} sur {{ roundCards.length }}</span>
        <h2>{{ lastAward ? roundCheer : "Carte passée" }}</h2>
        <template v-if="lastAward">
          <p class="xo-points">+{{ lastAward.points }} <small>points d'effort</small></p>
          <p class="xo-points-note">Points complets après validation par un expert.</p>
        </template>
        <p v-else class="story-copy">Aucune contribution n'a été envoyée cette fois.</p>
        <p class="hint">Les propositions en fon restent à vérifier par des locuteurs.</p>
        <div class="actions">
          <button class="button" type="button" @click="nextPhrase">{{ isLastCard ? "Voir mon bilan" : "Carte suivante" }}</button>
          <button class="button button-secondary" type="button" @click="openDomainSelector">Quitter la manche</button>
        </div>
      </section>
      </template>

      <section v-else class="card free-contribution-intro">
        <span class="eyebrow">Phrase libre</span>
        <h1>Propose ta propre phrase</h1>
        <p>
          Écris une phrase en français, sa traduction en fon, écoute la voix de l'IA si tu le
          souhaites, puis lis ta phrase à voix haute : l'enregistrement est nécessaire pour que
          cette contribution serve à entraîner une voix fon.
        </p>
      </section>

      <section
        v-if="contributionMode === 'free' || (selectedItem && !itemFinished)"
        id="contribution"
        :key="roundIndex"
        class="card task xo-record xo-card-in"
        :class="{ 'is-swipeable': canSwipeSkip }"
        :style="swipeStyle"
        @pointerdown="onSwipeDown"
        @pointermove="onSwipeMove"
        @pointerup="onSwipeEnd"
        @pointercancel="onSwipeEnd"
      >
        <span class="xo-kicker xo-kicker--dark">{{ contributionMode === "domain" ? "Mission · Dire" : "Phrase libre" }}</span>
        <template v-if="contributionMode === 'domain'">
          <p class="xo-context">{{ selectedDomain?.label }}</p>
          <p class="xo-phrase">{{ contributionFrench }}</p>
          <p v-if="canSwipeSkip" class="xo-swipe-hint" aria-hidden="true">
            <span>‹</span> Glisse la carte pour passer cette phrase <span>›</span>
          </p>
        </template>
        <template v-else>
          <label class="prompt-label" for="contribution-french">Ta phrase en français</label>
          <textarea
            id="contribution-french"
            v-model="contributionFrench"
            rows="2"
            maxlength="500"
            placeholder="Exemple : Bonjour, comment vas-tu ?"
            :disabled="contributionRecording || contributionSaving"
          ></textarea>
        </template>
        <p class="xo-instruction">Dis cette phrase en fon, avec tes mots.</p>

        <div class="xo-mic-zone xo-mic-zone--light">
          <button
            class="xo-mic"
            :class="{ 'is-rec': contributionRecording }"
            type="button"
            :disabled="contributionSaving"
            :aria-label="contributionRecording ? 'Terminer l\'enregistrement' : contributionHumanAudio ? 'Recommencer l\'enregistrement' : 'Enregistrer ma voix'"
            @click="contributionRecording ? finishContributionRecording() : startContributionRecording()"
          >
            <XoIcon name="mic" />
          </button>
          <span class="xo-mic-label">{{ contributionRecording ? "Appuie pour terminer" : contributionHumanAudio ? "Appuie pour recommencer" : "Appuie pour parler" }}</span>
          <div v-if="contributionRecording" class="xo-wave" aria-hidden="true">
            <span v-for="n in 12" :key="n"></span>
          </div>
        </div>
        <p class="hint xo-rec-status" role="status">{{ contributionRecordStatus }}</p>

        <div v-if="contributionHumanAudio && contributionAudioUrl" class="xo-review">
          <audio :src="contributionAudioUrl" controls aria-label="Écouter mon enregistrement"></audio>
          <button
            class="button button-secondary"
            type="button"
            :disabled="contributionSaving || contributionRecording"
            @click="startContributionRecording()"
          >
            <XoIcon name="redo" /> Recommencer
          </button>
        </div>

        <div v-if="contributionHumanAudio && !isAudioOnlyMode && !writeSkipped" class="xo-write">
          <template v-if="!writeOpen">
            <p class="xo-write-q">Tu veux aussi l'écrire ? <b>+{{ POINTS_WRITE }} points</b></p>
            <div class="xo-write-actions">
              <button class="button" type="button" @click="writeOpen = true"><XoIcon name="pen" /> Écrire</button>
              <button class="button button-secondary" type="button" @click="writeSkipped = true">Passer</button>
            </div>
          </template>
          <template v-else>
            <label class="prompt-label prompt-label-dominant" for="contribution-fon">Ta traduction en fon</label>
            <div class="xo-fon-field">
              <textarea
                id="contribution-fon"
                v-model="contributionFon"
                class="xo-fon"
                lang="fon"
                inputmode="none"
                rows="3"
                maxlength="500"
                placeholder="Touche ici pour ouvrir le clavier fon…"
                :disabled="contributionRecording || contributionSaving"
                @focus="openFonKeyboard"
                @blur="closeFonKeyboard"
              ></textarea>
              <div class="xo-listen-row">
                <button
                  class="button button-secondary xo-listen"
                  type="button"
                  :disabled="!contributionAudioUrl"
                  :aria-pressed="fonKbListening"
                  aria-label="Réécouter ton enregistrement"
                  @pointerdown.prevent
                  @click="toggleContributionVoice"
                >
                  <XoIcon name="play" /> Ma voix
                </button>
                <button
                  class="button button-secondary xo-listen"
                  type="button"
                  :disabled="contributionPlayingAi || !contributionFon.trim()"
                  aria-label="Écouter ce que tu as écrit"
                  @click="playContributionAiVoice"
                >
                  <XoIcon name="ear" /> Écouter l'écrit
                </button>
              </div>
            </div>
            <audio
              v-if="contributionAiAudioUrl"
              ref="contributionAiAudioEl"
              :src="contributionAiAudioUrl"
              controls
              aria-label="Écouter la voix de l'IA"
            ></audio>
            <button class="button button-secondary" type="button" @click="writeSkipped = true; writeOpen = false; contributionFon = ''">
              Passer
            </button>
          </template>
        </div>
        <p v-else-if="isAudioOnlyMode" class="hint">
          Tu contribues à l'oral : aucune traduction écrite ne te sera demandée.
        </p>

        <p class="hint">
          Aucune donnée n'est envoyée à OpenRouter par ce jeu. N'enregistre que ta propre voix.
        </p>
        <div class="actions">
          <button
            v-if="contributionMode === 'domain'"
            class="button button-secondary"
            type="button"
            :disabled="contributionRecording || contributionSaving"
            @click="finishDomainItem(false)"
          >
            Passer cette phrase
          </button>
          <button class="button" type="button" :disabled="!canSaveContribution" @click="saveContribution">
            {{
              contributionSaving
                ? "Envoi…"
                : contributionSaved && contributionMode === "free"
                  ? "Contribution envoyée"
                  : "Envoyer"
            }}
          </button>
        </div>
      </section>

      <template v-if="contributionMode === 'domain'">
        <p v-if="selectedItem && !itemFinished" class="status" :data-state="gameStatusType" role="status" aria-live="polite">
          {{ gameStatus }}
        </p>
      </template>
      <p v-else class="status" :data-state="contributionStatusState" role="status" aria-live="polite">
        {{ contributionStatus }}
      </p>

      <p class="small-note">
        La radio et ses personnages sont fictifs. Les phrases françaises sont
        des invites, pas des traductions validées ; les contributions libres
        et les contributions de mission restent à vérifier par des locuteurs
        avant tout usage en entraînement. Les données restent sur le serveur
        du prototype. Une collecte publique exige des règles de consentement,
        de retrait et de gouvernance définies avec les communautés concernées.
      </p>
    </main>

    <main v-else-if="activeScreen === 'profile'" class="xo-screen">
      <button class="xo-back" type="button" @click="showHome"><XoIcon name="back" /> Accueil</button>
      <h1 class="xo-screen-title">Mon profil</h1>

      <section class="xo-hud" aria-label="Mon niveau">
        <p class="xo-pseudo"><XoIcon name="user" /> {{ speakerName }}</p>
        <div class="xo-hud-top">
          <span class="xo-level"><b>{{ playerLevel.n }}</b> {{ playerLevel.name }}</span>
          <span class="xo-chip"><XoIcon name="star" /> {{ game.points }} pts</span>
          <span class="xo-chip"><XoIcon name="flame" /> {{ streakDays }} jour{{ streakDays > 1 ? "s" : "" }}</span>
        </div>
        <div class="xo-progress" role="progressbar" aria-label="Progression vers le niveau suivant" aria-valuemin="0" aria-valuemax="100" :aria-valuenow="levelProgress">
          <span :style="{ width: levelProgress + '%' }"></span>
        </div>
        <p class="xo-hud-next">
          {{ playerNext ? `Encore ${playerNext.min - game.points} points pour « ${playerNext.name} »` : "Niveau maximum atteint" }}
        </p>
      </section>

      <section class="card xo-panel">
        <h2>Apparence</h2>
        <div class="xo-segment xo-segment--3" role="group" aria-label="Apparence">
          <button
            v-for="o in themeOptions"
            :key="o.v"
            type="button"
            :class="{ 'is-on': themePref === o.v }"
            :aria-pressed="themePref === o.v"
            @click="setTheme(o.v)"
          >
            <XoIcon :name="o.icon" /> {{ o.label }}
          </button>
        </div>
      </section>

      <section class="card xo-panel">
        <h2>Mon mode</h2>
        <p class="story-copy">Tu peux changer quand tu veux.</p>
        <div class="xo-segment" role="group" aria-label="Mode de contribution">
          <button type="button" :aria-pressed="isAudioOnlyMode" :class="{ 'is-on': isAudioOnlyMode }" @click="setModeChoice('audio_only')">
            <XoIcon name="mic" /> Voix seule
          </button>
          <button type="button" :aria-pressed="!isAudioOnlyMode" :class="{ 'is-on': !isAudioOnlyMode }" @click="setModeChoice('audio_text')">
            <XoIcon name="pen" /> Voix + écrit
          </button>
        </div>
        <button class="button button-secondary" type="button" @click="retakeWritingTest"><XoIcon name="redo" /> Refaire le test d'écriture</button>
      </section>

      <section class="card xo-panel">
        <h2>Mes accords</h2>
        <ul class="xo-consent-list">
          <li><XoIcon name="check" /> J'ai 18 ans ou plus <em>Obligatoire</em></li>
          <li><XoIcon name="check" /> Ma voix et mes textes servent à entraîner des modèles <em>Obligatoire</em></li>
          <li>
            <label>
              <input type="checkbox" :checked="consentView.profile" @change="setOptionalConsent('profile', ($event.target as HTMLInputElement).checked)" />
              Mon profil (âge, région, variante) <em>Facultatif</em>
            </label>
          </li>
          <li>
            <label>
              <input type="checkbox" :checked="consentView.publication" @change="setOptionalConsent('publication', ($event.target as HTMLInputElement).checked)" />
              Publication dans un jeu de données ouvert <em>Facultatif</em>
            </label>
          </li>
        </ul>
        <template v-if="!confirmWithdraw">
          <button class="button button-secondary xo-danger" type="button" @click="confirmWithdraw = true">Retirer mon accord</button>
        </template>
        <div v-else class="xo-confirm" role="alertdialog" aria-label="Confirmer le retrait de l'accord">
          <p>Tu devras redonner ton accord pour rejouer. Tu es sûr·e ?</p>
          <div class="xo-write-actions">
            <button class="button xo-danger-fill" type="button" @click="doWithdrawConsent">Oui, retirer</button>
            <button class="button button-secondary" type="button" @click="confirmWithdraw = false">Annuler</button>
          </div>
        </div>
      </section>

      <section class="card xo-panel">
        <h2>Mes enregistrements</h2>
        <p class="story-copy">
          Pour supprimer les enregistrements déjà envoyés au serveur, écris au responsable du projet.
          <!-- TODO serveur : route de suppression par speaker_id -->
        </p>
        <template v-if="!confirmErase">
          <button class="button button-secondary xo-danger" type="button" @click="confirmErase = true">Effacer mes données sur cet appareil</button>
        </template>
        <div v-else class="xo-confirm" role="alertdialog" aria-label="Confirmer l'effacement">
          <p>Points, historique et réglages seront effacés d'ici. Les enregistrements déjà envoyés restent sur le serveur.</p>
          <div class="xo-write-actions">
            <button class="button xo-danger-fill" type="button" @click="doEraseLocalData">Oui, effacer</button>
            <button class="button button-secondary" type="button" @click="confirmErase = false">Annuler</button>
          </div>
        </div>
      </section>
    </main>

    <main v-else-if="activeScreen === 'contributions'" class="xo-screen">
      <button class="xo-back" type="button" @click="showHome"><XoIcon name="back" /> Accueil</button>
      <h1 class="xo-screen-title">Mes contributions</h1>
      <p class="xo-screen-sub">
        {{ myContributions.length }} envoyée{{ myContributions.length === 1 ? "" : "s" }} depuis cet appareil.
      </p>

      <ul v-if="myContributions.length" class="xo-contribs">
        <li v-for="c in myContributions" :key="c.id" class="xo-contrib">
          <div>
            <strong>{{ c.text }}</strong>
            <small>{{ c.domain }} · {{ formatContribDate(c.at) }}</small>
          </div>
          <span class="xo-status" data-status="recu">Reçu</span>
        </li>
      </ul>
      <section v-else class="card xo-panel xo-empty">
        <XoIcon name="mic" />
        <h2>Rien encore</h2>
        <p class="story-copy">Ta première voix apparaîtra ici.</p>
        <button class="button" type="button" @click="enterApp('game')">Jouer</button>
      </section>

      <details class="xo-legend-box">
        <summary>
          <span>Que veulent dire les statuts ?</span>
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
        </summary>
        <ul class="xo-legend">
          <li v-for="st in statusLegend" :key="st.key">
            <span class="xo-status" :data-status="st.key">{{ st.label }}</span>
            <small>{{ st.help }}</small>
          </li>
        </ul>
        <p class="hint">Pour l'instant, tout s'affiche « Reçu » : le suivi des relectures arrive bientôt.</p>
      </details>
    </main>

    <main v-else-if="activeScreen === 'assistant'" class="assistant-screen">
      <button class="xo-back" type="button" @click="showHome">
        <XoIcon name="back" /> Accueil
      </button>
      <section class="card assistant-card">
        <div class="assistant-head">
          <span class="xo-kicker">Ton guide de jeu</span>
          <h1 class="dominant">Parle, j'écoute.</h1>
          <label class="assistant-language">
            <span>Langue parlée</span>
            <select v-model="assistantLanguage">
              <option value="Français">Français</option>
              <option value="Fon">Fon</option>
            </select>
          </label>
        </div>
        <div class="guide-halo">
          <div
            class="guide"
            :data-state="assistantGuideState"
            role="img"
            aria-label="Guide souriant, un homme en tenue colorée qui vous accueille"
          >
            <svg viewBox="0 0 240 330" aria-hidden="true">
              <ellipse cx="119" cy="317" rx="88" ry="9" fill="#3c352c" opacity=".18"/>
              <path d="M39 319c5-43 19-69 49-82l30-8 31 8c29 11 47 39 53 82Z" fill="#6a3a2e"/>
              <path d="M49 285l17-18 17 18-17 18Zm59-25 13-14 14 14-14 14Zm54 28 17-18 17 18-17 18Z" fill="#d3234b"/>
              <circle cx="92" cy="280" r="7" fill="#f5b800"/><circle cx="145" cy="302" r="7" fill="#0f8a4f"/>
              <circle cx="188" cy="274" r="6" fill="#f5b800"/><circle cx="105" cy="311" r="5" fill="#0f8a4f"/>
              <path d="M97 216h45v38q-21 17-45 0Z" fill="#75482e"/>
              <path d="M55 250q23-19 48-23l17 20 17-20q28 4 52 23l-22 26-9-13v56H57v-56l-10 13-16-16Z" fill="#f5b800"/>
              <path d="M61 253q19-16 40-20l19 20 19-20q23 4 42 20l-19 23-10-12v52H71v-52l-10 12-12-13Z" fill="#6a3a2e"/>
              <path d="m88 244 9 10-10 10-10-10Zm59 24 9 10-10 10-10-10Zm-45 27 7 8-8 8-8-8Z" fill="#d3234b"/>
              <circle cx="125" cy="241" r="4" fill="#f5b800"/><circle cx="174" cy="250" r="4" fill="#f5b800"/>
              <path d="M104 239q21 19 42 0" fill="none" stroke="#f5b800" stroke-width="4" stroke-linecap="round"/>
              <circle cx="125" cy="257" r="4" fill="#f5b800"/>
              <path d="M50 250q-15 18-17 38" fill="none" stroke="#75482e" stroke-width="16" stroke-linecap="round"/>
              <circle cx="32" cy="291" r="9" fill="#75482e"/>
              <g class="guide-arm">
                <path d="M172 246q18-20 21-45l4-29" fill="none" stroke="#75482e" stroke-width="17" stroke-linecap="round" stroke-linejoin="round"/>
                <path d="M197 177q-8-2-8-10l1-17q0-5 4-5t4 5l1 10 2-17q1-5 5-4 4 0 3 6l-1 16 4-12q2-5 6-3 4 2 2 7l-4 15q-3 13-15 14Z" fill="#75482e"/>
                <path d="M193 168q7 5 14 2" fill="none" stroke="#603a28" stroke-width="2" stroke-linecap="round"/>
              </g>
              <path d="M67 143Q56 111 64 84Q70 52 102 53Q144 43 171 64Q190 83 181 143L169 125Q163 100 139 94Q110 85 85 107L77 131Z" fill="#241713"/>
              <ellipse cx="66" cy="157" rx="10" ry="15" fill="#75482e"/>
              <ellipse cx="181" cy="157" rx="10" ry="15" fill="#75482e"/>
              <ellipse cx="124" cy="151" rx="56" ry="67" fill="#8a5635"/>
              <circle cx="66" cy="174" r="8" fill="#f5b800"/><circle cx="182" cy="174" r="8" fill="#f5b800"/>
              <ellipse cx="101" cy="166" rx="13" ry="8" fill="#d96f68" opacity=".48"/>
              <ellipse cx="148" cy="166" rx="13" ry="8" fill="#d96f68" opacity=".48"/>
              <path d="M91 135q12-9 23 0m16 0q12-9 23 0" fill="none" stroke="#241713" stroke-width="5" stroke-linecap="round"/>
              <ellipse cx="104" cy="148" rx="8" ry="10" fill="#fff"/><ellipse cx="141" cy="148" rx="8" ry="10" fill="#fff"/>
              <circle cx="106" cy="149" r="4.5" fill="#241713"/><circle cx="139" cy="149" r="4.5" fill="#241713"/>
              <circle cx="107" cy="147" r="1.5" fill="#fff"/><circle cx="140" cy="147" r="1.5" fill="#fff"/>
              <path d="M123 151q-3 15 3 17" fill="none" stroke="#603a28" stroke-width="3" stroke-linecap="round"/>
              <path d="M101 175q11-8 22 0 6-7 12 0 11-8 22 0l-4 7q-9 4-17-2-7 6-17 2-9 4-17-2Z" fill="#30201c"/>
              <g class="guide-mouth">
                <path d="M108 190q16 13 32 0-4 15-16 15t-16-15Z" fill="#54251f"/>
                <path d="M111 191q13 8 26 0" fill="none" stroke="#f3b4a1" stroke-width="3" stroke-linecap="round"/>
              </g>
              <path d="M75 85q9-22 29-24m8-3 5-1m11 1 5 1m11 4 4 3" fill="none" stroke="#3b241d" stroke-width="5" stroke-linecap="round"/>
              <circle cx="84" cy="71" r="3" fill="#3b241d"/><circle cx="98" cy="61" r="3" fill="#3b241d"/>
            </svg>
          </div>
        </div>
        <div class="xo-mic-zone">
          <button
            class="mic-button"
            type="button"
            :data-state="assistantRecording ? 'listening' : 'idle'"
            :disabled="assistantMicDisabled"
            :aria-label="assistantMicLabel"
            @click="assistantRecording ? stopAssistantRecording() : startAssistantRecording()"
          >
            <XoIcon name="mic" />
          </button>
          <span class="xo-mic-label">{{ assistantMicLabel }}</span>
          <div v-if="assistantRecording" class="xo-wave" aria-hidden="true">
            <span v-for="n in 12" :key="n"></span>
          </div>
        </div>
        <div
          class="progress-track"
          :data-mode="assistantProgressMode"
          role="progressbar"
          aria-label="Progression de l'enregistrement et de la réponse"
          aria-valuemin="0"
          aria-valuemax="100"
        >
          <div
            class="progress-fill"
            :style="{ width: (assistantProgressMode === 'indeterminate' ? 35 : assistantProgressValue) + '%' }"
          ></div>
        </div>
        <p class="status" :data-state="assistantStatusState" role="status" aria-live="polite">
          {{ assistantStatus }}
        </p>
        <button v-if="assistantShowReplay" class="button button-secondary" type="button" @click="playAssistantResponse">
          Écouter la réponse
        </button>
      </section>
      <section class="card assistant-transcript">
        <h2 class="xo-chat-title">La conversation</h2>
        <div class="xo-chat xo-chat--me">
          <label class="xo-chat-who" for="assistant-transcript"><XoIcon name="user" /> Toi · corrige si besoin</label>
          <textarea
            id="assistant-transcript"
            v-model="assistantTranscript"
            :class="{ 'xo-fon': assistantLanguage === 'Fon' }"
            :lang="assistantLanguage === 'Fon' ? 'fon' : 'fr'"
            :inputmode="assistantLanguage === 'Fon' ? 'none' : 'text'"
            rows="3"
            placeholder="Ta phrase apparaîtra ici après la reconnaissance."
            @focus="assistantLanguage === 'Fon' && openFonKeyboard($event)"
            @blur="closeFonKeyboard"
          ></textarea>
        </div>
        <div class="xo-chat xo-chat--guide">
          <label class="xo-chat-who" for="assistant-answer"><XoIcon name="chat" /> Le guide · réponse en fon</label>
          <textarea
            id="assistant-answer"
            v-model="assistantAnswer"
            class="xo-fon"
            lang="fon"
            inputmode="none"
            rows="4"
            placeholder="La réponse en fon apparaîtra ici. Tu peux la corriger."
            @focus="openFonKeyboard"
            @blur="closeFonKeyboard"
          ></textarea>
        </div>
        <audio
          v-if="assistantResponseAudioUrl"
          ref="assistantAudioEl"
          :src="assistantResponseAudioUrl"
          controls
          preload="metadata"
          @ended="onAssistantAudioEnded"
        ></audio>
        <div v-if="assistantResponseReady" class="contribution-box">
          <p class="hint">
            Cette réponse est générée par l'IA, elle n'est pas lue par un humain. Lis-la toi-même à
            voix haute pour qu'elle compte comme une vraie contribution vocale.
          </p>
          <button class="button" type="button" @click="contributeAssistantAnswer">
            Lire cette réponse à voix haute pour contribuer →
          </button>
        </div>
      </section>
    </main>

    <nav v-show="!fonKbTarget" class="phone-nav xo-nav" aria-label="Navigation du jeu">
      <button
        class="phone-nav-item"
        :class="{ 'is-active': activeScreen === 'home' }"
        :aria-current="activeScreen === 'home' ? 'page' : undefined"
        type="button"
        @click="showHome"
      >
        <XoIcon name="home" />
        <span>Accueil</span>
      </button>
      <button
        class="phone-nav-item phone-nav-item-dominant"
        :class="{ 'is-active': activeScreen === 'game' }"
        :aria-current="activeScreen === 'game' ? 'page' : undefined"
        type="button"
        @click="scrollToContribution"
      >
        <XoIcon name="mic" />
        <span>Jouer</span>
      </button>
      <button
        class="phone-nav-item"
        :class="{ 'is-active': activeScreen === 'assistant' }"
        :aria-current="activeScreen === 'assistant' ? 'page' : undefined"
        type="button"
        @click="enterApp('assistant')"
      >
        <XoIcon name="chat" />
        <span>Guide</span>
      </button>
      <button
        class="phone-nav-item"
        type="button"
        aria-haspopup="dialog"
        :aria-expanded="menuOpen"
        aria-controls="xo-drawer"
        @click="openMenu"
      >
        <XoIcon name="menu" />
        <span>Menu</span>
      </button>
    </nav>

    <!-- Menu : accès à toutes les pages depuis n'importe quel écran -->
    <div v-if="menuOpen" class="xo-drawer-scrim" @click.self="closeMenu">
      <div id="xo-drawer" class="xo-drawer" role="dialog" aria-modal="true" aria-label="Menu">
        <div class="xo-zigzag xo-zigzag--thin" aria-hidden="true"></div>
        <div class="xo-drawer-head">
          <span class="xo-drawer-title">Menu</span>
          <button class="xo-drawer-close" type="button" aria-label="Fermer le menu" @click="closeMenu">
            <XoIcon name="close" />
          </button>
        </div>
        <nav class="xo-drawer-list" aria-label="Pages">
          <button class="xo-drawer-item" type="button" :class="{ 'is-active': activeScreen === 'home' }" @click="menuGo('home')">
            <XoIcon name="home" /><span>Accueil</span>
          </button>
          <button class="xo-drawer-item" type="button" :class="{ 'is-active': activeScreen === 'game' }" @click="menuGo('game')">
            <XoIcon name="mic" /><span>Jouer · choisir un domaine</span>
          </button>
          <button class="xo-drawer-item" type="button" :class="{ 'is-active': activeScreen === 'assistant' }" @click="menuGo('assistant')">
            <XoIcon name="chat" /><span>Parler au guide</span>
          </button>
          <button class="xo-drawer-item" type="button" @click="menuGo('how')">
            <XoIcon name="help" /><span>Comment ça marche ?</span>
          </button>
          <button class="xo-drawer-item" type="button" :class="{ 'is-active': activeScreen === 'profile' }" @click="menuGo('profile')">
            <XoIcon name="user" /><span>Mon profil</span>
          </button>
          <button class="xo-drawer-item" type="button" :class="{ 'is-active': activeScreen === 'contributions' }" @click="menuGo('contributions')">
            <XoIcon name="list" /><span>Mes contributions</span>
          </button>
          <button v-if="canInstall && !installed" class="xo-drawer-item" type="button" @click="menuGo('install')">
            <XoIcon name="download" /><span>Installer l'application</span>
          </button>
        </nav>
        <div class="xo-theme">
          <span class="xo-theme-label">Apparence</span>
          <div class="xo-segment xo-segment--3" role="group" aria-label="Apparence">
          <button
            v-for="o in themeOptions"
            :key="o.v"
            type="button"
            :class="{ 'is-on': themePref === o.v }"
            :aria-pressed="themePref === o.v"
            @click="setTheme(o.v)"
          >
            <XoIcon :name="o.icon" /> {{ o.label }}
          </button>
        </div>
        </div>
        <p class="xo-drawer-note">Tes enregistrements restent à vérifier par des locuteurs avant tout usage.</p>
      </div>
    </div>

    <div v-if="levelUp" class="xo-levelup-scrim" role="dialog" aria-modal="true" aria-label="Nouveau niveau" @click.self="dismissLevelUp">
      <div class="xo-levelup">
        <div class="xo-zigzag" aria-hidden="true"></div>
        <p class="xo-levelup-kicker">Nouveau niveau</p>
        <XoCube />
        <span class="xo-level xo-level--xl"><b>{{ levelUp.n }}</b> {{ levelUp.name }}</span>
        <div class="xo-zigzag" aria-hidden="true"></div>
        <button class="button" type="button" @click="dismissLevelUp">Continuer</button>
      </div>
    </div>
    </template>

    <!-- Clavier fon : remplace le clavier du téléphone quand un champ fon a le focus. -->
    <FonKeyboard
      v-if="fonKbTarget"
      docked
      :can-listen="!!fonKbListenUrl"
      :listening="fonKbListening"
      @key="onFonKey"
      @listen="toggleFonKbListen"
    />
  </div>
</template>
