<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";

interface Choice {
  text: string;
  outcome: string;
}

interface Mission {
  id: string;
  kicker: string;
  title: string;
  story: string;
  choices: Choice[];
}

interface HistorySource {
  label: string;
  url: string;
}

interface HistoryNote {
  period: string;
  title: string;
  summary: string;
  sources: HistorySource[];
}

interface AudioCapture {
  stream: MediaStream;
  context: AudioContext;
  source: MediaStreamAudioSourceNode;
  processor: ScriptProcessorNode;
  silentOutput: GainNode;
  chunks: Float32Array[];
  sampleRate: number;
}

const missions: Mission[] = [
  {
    id: "voix-quotidiennes",
    kicker: "Une radio d'aujourd'hui",
    title: "Ouvrir l'antenne",
    story:
      "Mina prépare une émission de proximité. Elle cherche une formule d'accueil que des locuteurs pourront proposer en fon, avec leurs propres mots.",
    choices: [
      {
        text: "Bonjour, merci d'être à l'écoute ce matin.",
        outcome: "L'émission commence par un accueil simple.",
      },
      {
        text: "Bienvenue à notre émission de quartier.",
        outcome: "Mina ouvre le micro à ses auditeurs.",
      },
      {
        text: "Prenons quelques minutes pour échanger.",
        outcome: "L'antenne invite à la conversation.",
      },
    ],
  },
  {
    id: "informations-utiles",
    kicker: "Un message utile",
    title: "Faire circuler l'information",
    story:
      "La radio veut partager des informations pratiques du quotidien. Choisis une annonce claire ; une traduction en fon reste une proposition de son auteur, pas une réponse attendue.",
    choices: [
      {
        text: "Le marché ouvre plus tard aujourd'hui.",
        outcome: "Les auditeurs reçoivent une information pratique.",
      },
      {
        text: "La réunion commence à quinze heures.",
        outcome: "L'horaire de la rencontre est annoncé.",
      },
      {
        text: "Pour un renseignement, adressez-vous à l'accueil.",
        outcome: "Les auditeurs savent où poser leurs questions.",
      },
    ],
  },
  {
    id: "paroles-partagees",
    kicker: "Les voix se répondent",
    title: "Donner rendez-vous",
    story:
      "Pour terminer, Mina prépare une invitation à la prochaine émission. Le fon est une langue vivante, et les mots comme leurs usages peuvent varier selon les locuteurs.",
    choices: [
      {
        text: "Retrouvons-nous la semaine prochaine à la radio.",
        outcome: "L'émission donne rendez-vous aux auditeurs.",
      },
      {
        text: "Vous pouvez nous proposer un sujet.",
        outcome: "La radio invite le public à suggérer un thème.",
      },
      {
        text: "Merci d'avoir partagé ce moment avec nous.",
        outcome: "Mina remercie les personnes à l'écoute.",
      },
    ],
  },
];

const routeStops = [
  {
    city: "Cotonou",
    x: 16,
    y: 70,
    title: "Le studio de quartier",
    detail: "Afi rejoint Mina pour préparer l'ouverture de l'antenne.",
  },
  {
    city: "Porto-Novo",
    x: 50,
    y: 27,
    title: "Le point d'information",
    detail: "Une halte pour préparer un message pratique à partager.",
  },
  {
    city: "Abomey",
    x: 84,
    y: 70,
    title: "Le rendez-vous radio",
    detail: "Dernière étape : inviter les auditeurs à la prochaine émission.",
  },
];

const historyNotes: HistoryNote[] = [
  {
    period: "Avant le XVIIe siècle",
    title: "Des histoires régionales, pas un seul royaume",
    summary:
      "Avant la colonisation, le territoire du Bénin actuel rassemblait plusieurs sociétés et pouvoirs. Au sud se trouvaient notamment Allada, Ouidah et Porto-Novo ; au nord, le royaume bariba de Nikki. Le royaume du Dahomey ne représente donc pas à lui seul toute l'histoire de ce territoire.",
    sources: [
      {
        label: "Encyclopaedia Britannica · Benin: History",
        url: "https://www.britannica.com/place/Benin/History",
      },
    ],
  },
  {
    period: "À partir du XVIIe siècle",
    title: "Le royaume du Dahomey et Abomey",
    summary:
      "Le royaume du Dahomey se développe au sud, autour d'Abomey, dans une histoire étroitement liée aux Fon. Les dates de fondation varient selon les sources et les traditions : mieux vaut parler d'un développement à partir du milieu du XVIIe siècle que d'une année certaine.",
    sources: [
      {
        label: "UNESCO · Palais royaux d'Abomey",
        url: "https://whc.unesco.org/en/list/323/",
      },
      {
        label: "Encyclopaedia Britannica · Kingdom of Dahomey",
        url: "https://www.britannica.com/place/Dahomey-historical-kingdom-Africa",
      },
    ],
  },
  {
    period: "1724–1727 et siècles suivants",
    title: "Ouidah, commerce atlantique et mémoire",
    summary:
      "Le roi Agaja étend le pouvoir du Dahomey vers Allada en 1724, puis Ouidah en 1727. Le royaume s'enrichit ensuite de la vente de personnes réduites en esclavage à des négociants européens. La traite transatlantique mobilise des acteurs aux rôles et pouvoirs différents ; au cœur de cette histoire se trouvent les personnes capturées, leurs familles et leurs descendants. Ce n'est pas un défi de jeu.",
    sources: [
      {
        label: "Encyclopaedia Britannica · Ouidah",
        url: "https://www.britannica.com/place/Ouidah",
      },
      {
        label: "Encyclopaedia Britannica · Benin: History",
        url: "https://www.britannica.com/place/Benin/History",
      },
    ],
  },
  {
    period: "1892–1899",
    title: "Conquête française et période coloniale",
    summary:
      "La France mène la conquête du Dahomey entre 1892 et 1894. Le territoire colonial est ensuite intégré à l'Afrique-Occidentale française. Les frontières et l'État du Bénin actuel ne sont pas simplement la continuation d'un ancien royaume.",
    sources: [
      {
        label: "Encyclopaedia Britannica · Benin: History",
        url: "https://www.britannica.com/place/Benin/History",
      },
    ],
  },
  {
    period: "1960–aujourd'hui",
    title: "Indépendance et République du Bénin",
    summary:
      "Le Dahomey devient indépendant en 1960. Le pays prend le nom de Bénin en 1975 ; après le changement de régime de 1990, il devient la République du Bénin. Aujourd'hui, le fon est une langue vivante parmi les langues du pays ; le fon, l'éwé et les autres langues ne sont pas interchangeables.",
    sources: [
      {
        label: "Encyclopaedia Britannica · Benin",
        url: "https://www.britannica.com/place/Benin",
      },
      {
        label: "Encyclopaedia Britannica · Fon people",
        url: "https://www.britannica.com/topic/Fon-people",
      },
    ],
  },
  {
    period: "Des héritages qui ne se confondent pas",
    title: "Une tradition a sa communauté et son contexte",
    summary:
      "Le patrimoine du Bénin ne se résume pas à une culture unique. Par exemple, l'UNESCO attribue le patrimoine oral du Gelede aux communautés Yoruba-Nago du Bénin, du Nigeria et du Togo : ce n'est pas un contenu Fon générique. Le jeu ne l'utilise donc pas comme décor ou comme quête.",
    sources: [
      {
        label: "UNESCO · Patrimoine oral du Gelede",
        url: "https://ich.unesco.org/en/RL/oral-heritage-of-gelede-00002",
      },
    ],
  },
];

const missionNumber = ref(0);
const activeScreen = ref<"home" | "game">("game");
const routeStop = computed(
  () => routeStops[Math.min(missionNumber.value, routeStops.length - 1)],
);
const historyOpen = ref(false);
const selectedChoice = ref<Choice | null>(null);
const fonText = ref("");
const consent = ref(false);
const humanAudio = ref<string | null>(null);
const audioUrl = ref<string | null>(null);
const recording = ref(false);
const recordingStatus = ref("Enregistrement facultatif, 30 secondes maximum.");
const gameStatus = ref("");
const gameStatusType = ref<"info" | "error" | "success">("info");
const missionFinished = ref(false);
const savedContributions = ref(0);
const saving = ref(false);
const clock = ref("");
const mission = computed(() => missions[missionNumber.value]);
const isComplete = computed(() => missionNumber.value >= missions.length);
const episodesPrepared = computed(() => missionNumber.value);
const canSave = computed(
  () =>
    Boolean(
      selectedChoice.value &&
        fonText.value.trim() &&
        humanAudio.value &&
        consent.value &&
        !recording.value &&
        !saving.value,
    ),
);

let capture: AudioCapture | null = null;
let stopTimer: ReturnType<typeof setTimeout> | null = null;
let clockTimer: ReturnType<typeof setInterval> | null = null;

function updateClock() {
  clock.value = new Intl.DateTimeFormat("fr-FR", {
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date());
}

function openHistoryNotebook() {
  activeScreen.value = "game";
  if (isComplete.value) restartChapter();
  historyOpen.value = true;
  void nextTick(() => {
    document.querySelector("#history-notebook")?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    });
  });
}

function scrollToMission() {
  activeScreen.value = "game";
  void nextTick(() => {
    document.querySelector("#mission")?.scrollIntoView({ behavior: "smooth" });
  });
}

function scrollToContribution() {
  activeScreen.value = "game";
  if (!selectedChoice.value) {
    setGameStatus("Choisis d'abord une réplique pour contribuer.");
    scrollToMission();
    return;
  }
  void nextTick(() => {
    document.querySelector("#contribution")?.scrollIntoView({ behavior: "smooth" });
  });
}

function showHome() {
  activeScreen.value = "home";
  historyOpen.value = false;
  void nextTick(() => {
    document.querySelector(".shell main")?.scrollTo({ top: 0 });
  });
}

function startChapter() {
  activeScreen.value = "game";
  void nextTick(() => {
    document.querySelector(".shell main")?.scrollTo({ top: 0 });
  });
}

function setGameStatus(message: string, type: "info" | "error" | "success" = "info") {
  gameStatus.value = message;
  gameStatusType.value = type;
}

function clearRecording() {
  humanAudio.value = null;
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value);
  audioUrl.value = null;
}

watch(fonText, clearRecording);

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

async function finishRecording() {
  if (!capture) return;
  if (stopTimer) clearTimeout(stopTimer);
  stopTimer = null;
  const activeCapture = capture;
  capture = null;
  recording.value = false;
  try {
    activeCapture.processor.disconnect();
    activeCapture.source.disconnect();
    activeCapture.silentOutput.disconnect();
    activeCapture.stream.getTracks().forEach((track) => track.stop());
    await activeCapture.context.close();
    if (!activeCapture.chunks.length) {
      recordingStatus.value =
        "Aucun son capturé. Réessaie ou continue sans contribuer.";
      return;
    }
    const blob = encodeWav(activeCapture.chunks, activeCapture.sampleRate);
    humanAudio.value = await encodeBase64(blob);
    audioUrl.value = URL.createObjectURL(blob);
    recordingStatus.value = "Enregistrement prêt. Écoute-le avant de l'envoyer.";
  } catch (error) {
    recordingStatus.value = `Impossible de finaliser l'enregistrement : ${error instanceof Error ? error.message : "erreur inconnue"}`;
  }
}

async function startRecording() {
  if (!fonText.value.trim()) {
    recordingStatus.value = "Écris d'abord la phrase en fon que tu vas lire.";
    return;
  }
  if (!navigator.mediaDevices?.getUserMedia) {
    recordingStatus.value = "L'accès au micro n'est pas disponible dans ce navigateur.";
    return;
  }
  recordingStatus.value = "Demande d'accès au microphone…";
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
    clearRecording();
    recording.value = true;
    recordingStatus.value = "Enregistrement… lis la phrase en fon.";
    stopTimer = setTimeout(() => void finishRecording(), 30_000);
  } catch (error) {
    stream?.getTracks().forEach((track) => track.stop());
    if (context && context.state !== "closed") await context.close();
    recordingStatus.value = `Impossible d'accéder au microphone : ${error instanceof Error ? error.message : "erreur inconnue"}`;
  }
}

function chooseReply(choice: Choice) {
  selectedChoice.value = choice;
  missionFinished.value = false;
  fonText.value = "";
  consent.value = false;
  clearRecording();
  setGameStatus(
    "Réplique choisie. Tu peux la traduire et l'enregistrer, ou poursuivre sans contribuer.",
  );
}

function finishMission(contributed: boolean) {
  const currentMission = mission.value;
  if (!currentMission || !selectedChoice.value) return;
  missionFinished.value = true;
  setGameStatus(
    contributed
      ? `Contribution reçue pour « ${currentMission.title} » ; elle reste à vérifier.`
      : `Mission accomplie : ${selectedChoice.value.outcome} Aucun texte ni audio n'a été enregistré.`,
    contributed ? "success" : "info",
  );
}

async function saveContribution() {
  if (!canSave.value || !selectedChoice.value || !mission.value) return;
  saving.value = true;
  setGameStatus("Envoi de la contribution au serveur du prototype…");
  try {
    const response = await fetch("/training-phrases", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        consent: true,
        source: "game",
        mission_id: mission.value.id,
        mission_title: mission.value.title,
        french_text: selectedChoice.value.text,
        fon_text: fonText.value.trim(),
        human_audio: humanAudio.value,
        synthesized_audio: null,
      }),
    });
    const data: unknown = await response.json();
    if (!response.ok) {
      const detail =
        typeof data === "object" && data !== null && "detail" in data
          ? String(data.detail)
          : "La contribution n'a pas pu être enregistrée.";
      throw new Error(detail);
    }
    savedContributions.value += 1;
    finishMission(true);
  } catch (error) {
    setGameStatus(
      `Échec de l'enregistrement : ${error instanceof Error ? error.message : "erreur inconnue"}`,
      "error",
    );
  } finally {
    saving.value = false;
  }
}

function nextMission() {
  if (missionNumber.value >= missions.length - 1) {
    missionNumber.value = missions.length;
    return;
  }
  missionNumber.value += 1;
  selectedChoice.value = null;
  missionFinished.value = false;
  fonText.value = "";
  consent.value = false;
  clearRecording();
  setGameStatus("");
  recordingStatus.value = "Enregistrement facultatif, 30 secondes maximum.";
}

function restartChapter() {
  missionNumber.value = 0;
  selectedChoice.value = null;
  missionFinished.value = false;
  fonText.value = "";
  consent.value = false;
  clearRecording();
  setGameStatus("");
  recordingStatus.value = "Enregistrement facultatif, 30 secondes maximum.";
}

onMounted(() => {
  updateClock();
  clockTimer = setInterval(updateClock, 60_000);
});

onBeforeUnmount(() => {
  if (clockTimer) clearInterval(clockTimer);
  if (stopTimer) clearTimeout(stopTimer);
  if (audioUrl.value) URL.revokeObjectURL(audioUrl.value);
  if (capture) {
    capture.stream.getTracks().forEach((track) => track.stop());
    void capture.context.close();
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
    <header>
      <div class="brand">
        <span class="brand-mark" aria-hidden="true">F</span>
        <div>
          <strong>Le carnet des voix</strong>
          <span>Bénin · une aventure en fon</span>
        </div>
      </div>
      <button class="home-link" type="button" aria-label="Accueil" @click="showHome">⌂</button>
    </header>

    <main v-if="activeScreen === 'home'" class="welcome-screen">
      <section class="welcome-hero">
        <span class="eyebrow">Une aventure à travers le Bénin</span>
        <h1>Fais entendre ta voix.</h1>
        <p>
          Suis Afi, messagère d'une radio fictive, de Cotonou à Porto-Novo puis
          Abomey. Rencontre des habitants et prépare des messages en fon.
        </p>
        <div class="welcome-radio" aria-hidden="true">
          <span class="welcome-radio-sun"></span>
          <span class="welcome-radio-sign">FON FM</span>
          <span class="welcome-radio-caption">UN SIGNAL · TOUT UN QUARTIER</span>
          <span class="welcome-radio-bars">▂ ▅ ▇ ▄ ▆ ▃</span>
        </div>
      </section>
      <div class="welcome-heading">
        <span class="eyebrow">À toi de choisir</span>
        <h2>Choisis ton parcours</h2>
      </div>
      <button class="welcome-action welcome-action-primary" type="button" @click="startChapter">
        <span class="welcome-action-icon" aria-hidden="true">♫</span>
        <span class="welcome-action-copy">
          <strong>Explorer Le carnet des voix</strong>
          <small>Joue le chapitre pilote et prépare des phrases pour une radio fictive.</small>
          <b>Lancer l'aventure <span aria-hidden="true">→</span></b>
        </span>
      </button>
      <button class="welcome-action" type="button" @click="openHistoryNotebook">
        <span class="welcome-action-icon" aria-hidden="true">▤</span>
        <span class="welcome-action-copy">
          <strong>Découvrir l'histoire du Bénin</strong>
          <small>Consulte les six repères historiques et leurs sources.</small>
          <b>Ouvrir le carnet <span aria-hidden="true">→</span></b>
        </span>
      </button>
      <button class="welcome-action" type="button" @click="scrollToContribution">
        <span class="welcome-action-icon" aria-hidden="true">◉</span>
        <span class="welcome-action-copy">
          <strong>Faire entendre ma voix</strong>
          <small>Propose une formulation en fon et choisis si tu veux contribuer.</small>
          <b>Participer <span aria-hidden="true">→</span></b>
        </span>
      </button>
      <p class="welcome-note">Tes propositions restent facultatives et ne sont pas automatiquement vérifiées.</p>
    </main>

    <main v-else>
      <section v-if="!isComplete" class="chapter-intro">
        <div class="chapter-title-row">
          <div>
            <span class="eyebrow">Chronique interactive · Chapitre 1</span>
            <h1>Le carnet des voix</h1>
          </div>
          <div class="signal-count" :aria-label="`${episodesPrepared} épisodes préparés sur trois`">
            <span aria-hidden="true">♫</span>
            <strong>{{ episodesPrepared }}/3</strong>
          </div>
        </div>
        <p class="intro">
          Afi traverse trois villes pour aider une radio de proximité à faire
          circuler les voix du quotidien.
        </p>
        <section class="route-card" aria-label="Itinéraire fictif d'Afi">
          <div class="route-heading">
            <div>
              <span class="eyebrow">Le carnet de route d'Afi</span>
              <h2>{{ routeStop.city }}</h2>
            </div>
            <span class="route-step">Étape {{ Math.min(missionNumber + 1, routeStops.length) }}/{{ routeStops.length }}</span>
          </div>
          <p class="route-location">{{ routeStop.title }} · {{ routeStop.detail }}</p>
          <div class="route-map" role="img" :aria-label="`Afi est à ${routeStop.city}. Itinéraire fictif de Cotonou à Abomey.`">
            <svg class="route-road" viewBox="0 0 360 138" preserveAspectRatio="none" aria-hidden="true">
              <path class="route-road-shadow" d="M58 101 C105 101 111 42 180 38 S258 49 302 101" />
              <path class="route-road-line" d="M58 101 C105 101 111 42 180 38 S258 49 302 101" />
            </svg>
            <span
              v-for="(stop, index) in routeStops"
              :key="stop.city"
              class="route-stop"
              :class="{
                'is-visited': index < missionNumber,
                'is-current': index === Math.min(missionNumber, routeStops.length - 1),
              }"
              :style="{ left: `${stop.x}%`, top: `${stop.y}%` }"
            >
              <span class="route-stop-dot">{{ index < missionNumber ? "✓" : String(index + 1).padStart(2, "0") }}</span>
              <span class="route-stop-name">{{ stop.city }}</span>
            </span>
            <span
              class="route-player"
              :style="{ left: `${routeStop.x}%`, top: `${routeStop.y}%` }"
              aria-label="Afi, personnage fictif en déplacement"
            >
              <svg viewBox="0 0 32 40" aria-hidden="true">
                <circle cx="16" cy="7" r="5" />
                <path d="M10 15 Q16 11 22 15 L24 25 L20 26 L22 38 L17 38 L15 28 L12 38 L7 38 L11 25 L8 24Z" />
                <path class="route-player-arm" d="M10 17 L5 24 M21 17 L27 21" />
              </svg>
              <span>Afi</span>
            </span>
          </div>
          <p class="route-note">Parcours de fiction, pas une carte routière. Les lieux et rencontres sont imaginaires ; ils ne représentent pas toutes les langues ni les réalités de ces villes.</p>
        </section>
        <div class="mission-track" aria-label="Progression des missions">
          <span
            v-for="(chapterMission, index) in missions"
            :key="chapterMission.id"
            class="track-node"
            :class="{
              'is-complete': index < missionNumber,
              'is-current': index === missionNumber,
            }"
            :aria-label="`${chapterMission.title}${index < missionNumber ? ', terminée' : index === missionNumber ? ', en cours' : ', à venir'}`"
          >
            <span>{{ index < missionNumber ? "✓" : String(index + 1).padStart(2, "0") }}</span>
            <span class="track-line" aria-hidden="true"></span>
          </span>
        </div>
        <button
          class="history-toggle"
          type="button"
          :aria-expanded="historyOpen"
          aria-controls="history-notebook"
          @click="historyOpen = !historyOpen"
        >
          <span aria-hidden="true">▤</span>
          {{ historyOpen ? "Refermer le carnet historique" : "Ouvrir le carnet historique" }}
          <span class="history-toggle-count">6 repères</span>
        </button>
        <section v-if="historyOpen" id="history-notebook" class="history-notebook" aria-label="Repères historiques du Bénin">
          <div class="history-notebook-heading">
            <span class="eyebrow">Lire avant de jouer</span>
            <h2>Une histoire, plusieurs territoires et plusieurs voix</h2>
            <p>
              Ce survol n'est pas une histoire complète. Ces repères ont des
              sources consultables ; ils ne remplacent ni les historiens
              béninois ni les récits des communautés.
            </p>
          </div>
          <article v-for="note in historyNotes" :key="note.title" class="history-note">
            <span class="history-period">{{ note.period }}</span>
            <h3>{{ note.title }}</h3>
            <p>{{ note.summary }}</p>
            <div class="history-sources" aria-label="Sources">
              <a
                v-for="source in note.sources"
                :key="source.url"
                :href="source.url"
                target="_blank"
                rel="noopener noreferrer"
              >
                {{ source.label }} ↗
              </a>
            </div>
          </article>
          <p class="history-editorial-note">
            Le jeu n'utilise pas de chants, proverbes, récits familiaux ou
            pratiques religieuses comme énigmes ou récompenses. Ces contenus
            demandent le contexte, l'accord et la validation des personnes
            concernées.
          </p>
        </section>
      </section>

      <section v-if="!isComplete && mission" id="mission" class="game-screen" aria-live="polite">
        <div class="radio-scene" :class="`scene-${missionNumber + 1}`">
          <svg
            class="scene-illustration"
            viewBox="0 0 560 320"
            preserveAspectRatio="xMidYMid slice"
            role="img"
            :aria-label="`Illustration fictive d'une rue à ${routeStop.city}, avec Afi devant un studio radio de quartier.`"
            xmlns="http://www.w3.org/2000/svg"
          >
            <defs>
              <linearGradient id="city-sky" x2="0" y2="1">
                <stop offset="0" stop-color="#6e6c89" />
                <stop offset=".48" stop-color="#e9a47f" />
                <stop offset="1" stop-color="#f4c27e" />
              </linearGradient>
              <linearGradient id="city-wall" x2=".8" y2="1">
                <stop stop-color="#e9c398" />
                <stop offset="1" stop-color="#ad785e" />
              </linearGradient>
              <linearGradient id="afi-skin" x2=".9" y2="1">
                <stop stop-color="#75452f" />
                <stop offset=".5" stop-color="#573323" />
                <stop offset="1" stop-color="#38251f" />
              </linearGradient>
              <linearGradient id="afi-shirt" x2="1" y2="1">
                <stop stop-color="#2c7680" />
                <stop offset="1" stop-color="#174958" />
              </linearGradient>
              <linearGradient id="street" x2="0" y2="1">
                <stop stop-color="#68606a" />
                <stop offset="1" stop-color="#343644" />
              </linearGradient>
              <pattern id="wall-grain" width="18" height="18" patternUnits="userSpaceOnUse">
                <path d="M2 5h4M11 14h3" stroke="#fff4dd" stroke-opacity=".1" stroke-width="1" />
              </pattern>
              <filter id="soft-shadow" x="-30%" y="-30%" width="160%" height="180%">
                <feGaussianBlur in="SourceAlpha" stdDeviation="4" />
                <feOffset dy="4" />
                <feComponentTransfer><feFuncA type="linear" slope=".28" /></feComponentTransfer>
                <feMerge><feMergeNode /><feMergeNode in="SourceGraphic" /></feMerge>
              </filter>
            </defs>
            <rect width="560" height="320" fill="url(#city-sky)" />
            <circle cx="428" cy="72" r="31" fill="#ffe2a5" opacity=".8" />
            <path d="M0 148 72 127 129 143 193 111 250 137 312 116 375 140 446 112 560 143v73H0Z" fill="#64677a" opacity=".56" />
            <path d="M0 161h104V88H0Zm112-27h72V69h-72Zm80 25h75V104h-75Zm190-15h58V92h-58Zm65 12h113V73H447Z" fill="#4a5266" opacity=".7" />
            <path d="M0 190h560v130H0Z" fill="url(#street)" />
            <path d="M0 190h560v20H0Z" fill="#e1bd91" />
            <path d="M0 208h560" stroke="#fff0d6" stroke-opacity=".3" stroke-width="2" />
            <path d="m337 320 61-112h32l-31 112Z" fill="#252a38" opacity=".38" />
            <path d="M0 276q102-28 195 0t194 0q83-24 171-1v45H0Z" fill="#272b36" opacity=".58" />
            <path d="M45 178V64h221v114Z" fill="url(#city-wall)" />
            <path d="M45 178V64h221v114Z" fill="url(#wall-grain)" />
            <path d="M37 67h236v12H37z" fill="#785949" />
            <path d="M37 178h236v12H37z" fill="#80614d" />
            <rect x="61" y="96" width="77" height="58" rx="3" fill="#315266" />
            <rect x="68" y="103" width="63" height="44" fill="#f3cb8b" />
            <path d="M99 103v44M68 125h63" stroke="#315266" stroke-width="4" />
            <rect x="157" y="101" width="62" height="46" rx="3" fill="#26394e" />
            <rect x="162" y="106" width="52" height="36" fill="#f8d59b" opacity=".8" />
            <path d="M158 101h61v8h-61z" fill="#59616d" />
            <rect x="227" y="121" width="8" height="57" fill="#f0c47f" opacity=".75" />
            <rect x="53" y="78" width="118" height="24" rx="5" fill="#20354b" />
            <text x="66" y="95" fill="#ffe0a0" font-size="12" font-weight="800" letter-spacing="2">FON FM</text>
            <path d="M286 190V87h4v103M288 90l-21 25m22-27 21 24m-40 1h38" fill="none" stroke="#354557" stroke-linecap="round" stroke-width="3" />
            <path d="M289 83q18-20 0-38m0 38q-18-20 0-38m0 47q30-31 0-62m0 62q-30-31 0-62" fill="none" stroke="#f8d99a" stroke-opacity=".62" stroke-width="2" />
            <path d="M0 218h560" stroke="#f4ce98" stroke-opacity=".5" stroke-width="3" />
            <path d="M21 221h110m282 0h105" stroke="#fff1d2" stroke-opacity=".28" stroke-width="2" stroke-dasharray="3 11" />
            <g opacity=".78">
              <path d="M451 191v-53m0 16q-26-18-27-40 27 3 35 27m-8 12q21-19 39-16-5 25-39 33" fill="#354a43" />
              <path d="M451 181v-42" stroke="#604b3d" stroke-width="5" />
            </g>
            <ellipse cx="371" cy="287" rx="66" ry="12" fill="#111a28" opacity=".4" />
            <g class="city-extra-person" transform="translate(95 179)">
              <path d="M5 53q3-24 24-27 22 3 26 27v33H5Z" fill="#d58c43" />
              <path d="M14 30q-2-24 15-27 18 2 17 26l-7 11H19Z" fill="#261d1e" />
              <ellipse cx="30" cy="19" rx="13" ry="16" fill="#68412f" />
              <path d="M17 16q1-17 14-16 13 1 14 15-8-7-15-6-5 5-13 7" fill="#251e20" />
              <path d="M25 35h10v13H25z" fill="#62402d" />
              <path d="m17 43 12 7 12-7" fill="none" stroke="#efc7a2" stroke-width="2" />
            </g>
            <g class="afi-figure" filter="url(#soft-shadow)">
              <path d="M327 303q3-57 22-83 12-14 40-17 32 5 46 22 14 24 18 78Z" fill="url(#afi-shirt)" />
              <path d="M355 212q11-12 21-12l13 17 14-17q11 1 22 12l-12 15-8-5v80h-43v-80l-8 6Z" fill="#f0b84c" />
              <path d="m376 217 13 16 13-16v83h-26Z" fill="url(#afi-shirt)" />
              <path d="M359 298h59v6h-59z" fill="#e8b65f" opacity=".8" />
              <path d="M365 167h31v48h-31z" fill="url(#afi-skin)" />
              <ellipse cx="380" cy="143" rx="39" ry="48" fill="url(#afi-skin)" />
              <path d="M340 145q-12-52 29-65 41-9 58 24 7 16 1 42-7-23-23-31-22 8-53-5l-9 38Z" fill="#241d20" />
              <path d="M344 127q7-36 37-41m7-1q17 3 27 17" fill="none" stroke="#38292a" stroke-linecap="round" stroke-width="7" />
              <path d="M350 137q9-7 18 0m22 0q9-7 18 0" fill="none" stroke="#21191b" stroke-linecap="round" stroke-width="3" />
              <ellipse cx="360" cy="144" rx="4" ry="5" fill="#f1dfca" />
              <ellipse cx="398" cy="144" rx="4" ry="5" fill="#f1dfca" />
              <circle cx="361" cy="145" r="2" fill="#17181a" />
              <circle cx="397" cy="145" r="2" fill="#17181a" />
              <path d="M379 145q-4 12 2 14" fill="none" stroke="#3a2926" stroke-linecap="round" stroke-width="2" />
              <path d="M367 166q12 8 24 0" fill="none" stroke="#3d2020" stroke-linecap="round" stroke-width="3" />
              <path d="M343 157q3 35 37 39 34-4 39-39" fill="none" stroke="#442b27" stroke-opacity=".48" stroke-width="2" />
              <circle cx="340" cy="151" r="6" fill="#d9a95e" />
              <circle cx="420" cy="151" r="6" fill="#d9a95e" />
              <path d="M337 230q-17 11-27 35" fill="none" stroke="url(#afi-skin)" stroke-linecap="round" stroke-width="13" />
              <path d="M442 231q15 9 23 25" fill="none" stroke="url(#afi-skin)" stroke-linecap="round" stroke-width="13" />
              <path d="M462 252v-17q0-5 4-5t4 5v10l3-14q1-5 5-3 4 1 2 6l-4 20q-3 10-13 8l-8-5q-5-4-1-8 3-3 8 3Z" fill="#573323" />
              <path d="m368 213 12 14m28-14-12 14" stroke="#f8d49b" stroke-width="2" opacity=".9" />
            </g>
          </svg>
          <div class="scene-caption">
            <span class="live-dot"></span>
            <span>{{ routeStop.city }} · {{ mission.kicker }}</span>
          </div>
          <div class="scene-frequency" :class="{ 'has-signal': missionNumber > 0 }" aria-label="État de la diffusion">
            <span v-for="bar in 5" :key="bar"></span>
            <span class="frequency-label">DIRECT</span>
          </div>
        </div>

        <div class="dialogue-box">
          <svg class="radio-avatar" viewBox="0 0 64 64" role="img" aria-label="Mina, animatrice béninoise fictive">
            <defs>
              <linearGradient id="mina-background" x2="0" y2="1">
                <stop stop-color="#d79879" />
                <stop offset="1" stop-color="#385168" />
              </linearGradient>
              <linearGradient id="mina-skin" x2="1" y2="1">
                <stop stop-color="#805038" />
                <stop offset="1" stop-color="#4a2d24" />
              </linearGradient>
              <linearGradient id="mina-shirt" x2="1" y2="1">
                <stop stop-color="#e7b54b" />
                <stop offset="1" stop-color="#2c6e70" />
              </linearGradient>
            </defs>
            <rect width="64" height="64" fill="url(#mina-background)" />
            <path d="M7 64q2-21 25-23 23 2 26 23Z" fill="url(#mina-shirt)" />
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
              <span class="speaker-role">Animatrice radio</span>
            </div>
            <p>{{ mission.story }}</p>
          </div>
          <span class="dialogue-caret" aria-hidden="true">▼</span>
        </div>

        <div class="mission-card">
          <div class="mission-heading">
            <div>
              <span class="eyebrow">Objectif de mission</span>
              <h2>{{ mission.title }}</h2>
            </div>
            <span class="mission-index" aria-hidden="true">
              {{ String(missionNumber + 1).padStart(2, "0") }}
            </span>
          </div>
          <span class="prompt-label">Quelle annonce aimerais-tu proposer en fon ?</span>
          <div class="choices">
            <button
              v-for="(choice, index) in mission.choices"
              :key="choice.text"
              class="choice"
              type="button"
              :aria-pressed="selectedChoice?.text === choice.text"
              :class="{ 'is-selected': selectedChoice?.text === choice.text }"
              :disabled="missionFinished || recording || saving"
              @click="chooseReply(choice)"
            >
              <span class="choice-index">{{ ["A", "B", "C"][index] }}</span>
              <span class="choice-text">{{ choice.text }}</span>
              <span class="choice-arrow" aria-hidden="true">↗</span>
            </button>
          </div>

          <section v-if="selectedChoice && !missionFinished" id="contribution" class="task">
            <div class="task-questline">
              <span class="task-badge" aria-hidden="true">✦</span>
              <div>
                <span class="eyebrow">Quête facultative</span>
                <h3>Prêter sa voix à la radio</h3>
              </div>
            </div>
            <p>
              Si tu parles fon, propose une formulation dont tu connais l'usage,
              puis lis exactement ta phrase. Il n'y a pas de traduction attendue :
              ta proposition devra être vérifiée par des locuteurs.
            </p>
            <label class="prompt-label" for="fon-text">Ta formulation en fon</label>
            <textarea
              id="fon-text"
              v-model="fonText"
              maxlength="500"
              placeholder="Écris la phrase telle que tu la prononceras…"
              :disabled="recording || saving"
            ></textarea>
            <div class="record-row">
              <button
                class="button button-secondary"
                type="button"
                :disabled="saving"
                @click="recording ? finishRecording() : startRecording()"
              >
                {{ recording ? "■ Terminer l'enregistrement" : humanAudio ? "● Refaire mon enregistrement" : "● Enregistrer ma voix" }}
              </button>
              <span class="hint" role="status">{{ recordingStatus }}</span>
            </div>
            <audio
              v-if="audioUrl"
              ref="previewAudio"
              :src="audioUrl"
              controls
              aria-label="Écouter mon enregistrement"
            ></audio>
            <label class="consent">
              <input v-model="consent" type="checkbox" :disabled="recording || saving" />
              <span>
                Je suis majeur·e, je maîtrise suffisamment le fon pour proposer
                cette phrase et j'enregistre uniquement ma voix. J'autorise la
                conservation de ce texte et de cet enregistrement sur le serveur
                qui héberge le prototype, pour l'évaluation et l'amélioration des
                outils du projet. Je comprends que la contribution restera à
                vérifier, ne sera pas publiée automatiquement et que je peux jouer
                sans contribuer. Pour demander sa suppression, je contacterai le
                responsable du projet.
              </span>
            </label>
            <p class="hint">
              Aucune donnée n'est envoyée à OpenRouter par ce jeu. N'enregistre
              pas la voix d'une autre personne. La formulation et l'audio seront
              conservés ensemble et marqués « à vérifier ».
            </p>
            <div class="actions">
              <button
                class="button button-secondary"
                type="button"
                :disabled="recording || saving"
                @click="finishMission(false)"
              >
                Continuer sans contribuer
              </button>
              <button
                class="button"
                type="button"
                :disabled="!canSave"
                @click="saveContribution"
              >
                {{ saving ? "Enregistrement…" : "Enregistrer ma contribution" }}
              </button>
            </div>
          </section>

          <p class="status" :data-state="gameStatusType" role="status" aria-live="polite">
            {{ gameStatus }}
          </p>
          <div v-if="missionFinished" class="mission-reward">
            <span class="reward-star" aria-hidden="true">✦</span>
            <div>
              <strong>Épisode prêt pour la radio fictive</strong>
              <span>{{ selectedChoice?.outcome }}</span>
            </div>
          </div>
          <div v-if="missionFinished" class="actions">
            <button class="button" type="button" @click="nextMission">
              {{ missionNumber === missions.length - 1 ? "Terminer le chapitre" : "Mission suivante →" }}
            </button>
          </div>
        </div>
      </section>

      <section v-else class="card result">
        <div class="ending-art" aria-hidden="true">
          <span class="ending-signal signal-one"></span>
          <span class="ending-signal signal-two"></span>
          <span class="ending-signal signal-three"></span>
          <span class="ending-star">♫</span>
        </div>
        <span class="eyebrow">Chapitre terminé</span>
        <h2>Le carnet d'émission est prêt.</h2>
        <p>
          Tu as préparé les trois épisodes de la radio.
          {{ savedContributions }} contribution{{ savedContributions === 1 ? "" : "s" }}
          enregistrée{{ savedContributions === 1 ? "" : "s" }} avec consentement.
          Les propositions en fon restent à vérifier par des locuteurs et ne
          représentent pas toutes les voix du Bénin.
        </p>
        <button class="button" type="button" @click="restartChapter">
          Rejouer le chapitre
        </button>
      </section>

      <p class="small-note">
        La radio et ses personnages sont fictifs. Les phrases françaises sont
        des invites, pas des traductions validées ; les contributions ne sont
        pas automatiquement vérifiées ni utilisées pour entraîner un modèle.
        Les données restent sur le serveur du prototype. Une collecte publique
        exige des règles de consentement, de retrait et de gouvernance définies
        avec les communautés concernées.
      </p>
    </main>
    <nav class="phone-nav" aria-label="Navigation du jeu">
      <button
        class="phone-nav-item"
        :class="{ 'is-active': activeScreen === 'game' && historyOpen }"
        type="button"
        @click="openHistoryNotebook"
      >
        <span aria-hidden="true">◇</span>
        <span>Histoire</span>
      </button>
      <button
        class="phone-nav-item"
        :class="{ 'is-active': activeScreen === 'game' && !historyOpen }"
        type="button"
        @click="scrollToContribution"
      >
        <span aria-hidden="true">◉</span>
        <span>Ma voix</span>
      </button>
      <button
        class="phone-nav-item"
        :class="{ 'is-active': activeScreen === 'home' }"
        type="button"
        @click="showHome"
      >
        <span aria-hidden="true">⌂</span>
        <span>Accueil</span>
      </button>
    </nav>
  </div>
</template>
