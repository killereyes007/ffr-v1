<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import FonKeyboard from "./FonKeyboard.vue";
import XoIcon from "./XoIcon.vue";
import XoLogo from "./XoLogo.vue";

// Espace experts : file de relecture. Accès : <url du jeu>#/experts
// TODO données : tout ce qui suit est de la DÉMONSTRATION (aucune route serveur
// n'existe encore). Rien n'est envoyé ni enregistré. Le fon ci-dessous n'est pas
// validé : « à valider par un linguiste ».

type Verdict = "valider" | "corriger" | "rejeter" | "attente";
type Status = "a_valider" | "valide" | "corrige" | "rejete";

interface Syllable {
  t: string;
  uncertain: boolean;
}
interface Item {
  id: number;
  contributor: string;
  domain: string;
  french: string;
  syllables: Syllable[];
  correction: string;
  status: Status;
  avis: { name: string; verdict: Verdict; note: string }[];
}

const mk = (s: string[], uncertainIdx: number[] = []): Syllable[] =>
  s.map((t, i) => ({ t: t.normalize("NFC"), uncertain: uncertainIdx.includes(i) }));

const items = ref<Item[]>([
  {
    id: 1,
    contributor: "Voix-4821",
    domain: "Marché et commerce",
    french: "Je mange (démonstration)",
    syllables: mk(["Un", "nɔ́", "ɖu", "nǔ"], [2]),
    correction: "Un nɔ́ ɖu nǔ",
    status: "a_valider",
    avis: [
      { name: "Gardien 1", verdict: "valider", note: "Tons corrects." },
      { name: "Gardien 2", verdict: "corriger", note: "Un doute sur la 3e syllabe." },
      { name: "Gardien 3", verdict: "attente", note: "" },
    ],
  },
  {
    id: 2,
    contributor: "Voix-1093",
    domain: "Santé",
    french: "Phrase de démonstration n° 2",
    syllables: mk(["syl-1", "syl-2", "syl-3"], [1]),
    correction: "",
    status: "a_valider",
    avis: [
      { name: "Gardien 1", verdict: "attente", note: "" },
      { name: "Gardien 2", verdict: "attente", note: "" },
      { name: "Gardien 3", verdict: "attente", note: "" },
    ],
  },
  {
    id: 3,
    contributor: "Voix-7710",
    domain: "Agriculture et élevage",
    french: "Phrase de démonstration n° 3",
    syllables: mk(["syl-1", "syl-2"]),
    correction: "",
    status: "a_valider",
    avis: [
      { name: "Gardien 1", verdict: "rejeter", note: "Audio coupé." },
      { name: "Gardien 2", verdict: "rejeter", note: "Bruit de fond." },
      { name: "Gardien 3", verdict: "attente", note: "" },
    ],
  },
]);

const current = ref(0);
const item = computed(() => items.value[current.value]);
const textarea = ref<HTMLTextAreaElement | null>(null);
const toast = ref("");
let toastTimer: ReturnType<typeof setTimeout> | null = null;

const statusLabel: Record<Status, string> = {
  a_valider: "À valider",
  valide: "Validé",
  corrige: "Corrigé",
  rejete: "Rejeté",
};
const statusKey: Record<Status, string> = { a_valider: "expert", valide: "valide", corrige: "relecture", rejete: "rejete" };
const verdictLabel: Record<Verdict, string> = { valider: "Valide", corriger: "À corriger", rejeter: "Rejette", attente: "En attente" };

const pending = computed(() => items.value.filter((i) => i.status === "a_valider").length);
const consensus = computed(() => {
  const count = (v: Verdict) => item.value.avis.filter((a) => a.verdict === v).length;
  return { valider: count("valider"), corriger: count("corriger"), rejeter: count("rejeter") };
});

function say(message: string) {
  toast.value = message;
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (toast.value = ""), 2200);
}

function decide(status: Status) {
  item.value.status = status;
  say(`${statusLabel[status]} (démonstration : rien n'est enregistré)`);
  const next = items.value.findIndex((i, idx) => idx > current.value && i.status === "a_valider");
  if (next >= 0) current.value = next;
}

function insertChar(char: string) {
  const el = textarea.value;
  const value = item.value.correction;
  if (!el) {
    item.value.correction = value + char;
    return;
  }
  const start = el.selectionStart ?? value.length;
  const end = el.selectionEnd ?? value.length;
  item.value.correction = (value.slice(0, start) + char + value.slice(end)).normalize("NFC");
  requestAnimationFrame(() => {
    el.focus();
    el.setSelectionRange(start + char.length, start + char.length);
  });
}

function toggleUncertain(index: number) {
  item.value.syllables[index].uncertain = !item.value.syllables[index].uncertain;
}

function onKey(e: KeyboardEvent) {
  const tag = (e.target as HTMLElement | null)?.tagName;
  if (tag === "TEXTAREA" || tag === "INPUT" || e.ctrlKey || e.metaKey || e.altKey) return;
  const k = e.key.toLowerCase();
  if (k === "v") decide("valide");
  else if (k === "c") {
    textarea.value?.focus();
    e.preventDefault();
  } else if (k === "r") decide("rejete");
}
onMounted(() => window.addEventListener("keydown", onKey));
onBeforeUnmount(() => window.removeEventListener("keydown", onKey));
</script>

<template>
  <div class="xo-page xo-exp">
    <div class="xo-zigzag" aria-hidden="true"></div>
    <div class="xo-exp-head">
      <XoLogo :size="44" />
      <div>
        <h1 class="xo-title xo-exp-h1">Espace experts</h1>
        <p class="xo-exp-sub">{{ pending }} à relire</p>
      </div>
    </div>
    <p class="xo-exp-demo" role="note">
      Données de démonstration : rien n'est envoyé ni enregistré. Le fon affiché est à valider par un linguiste.
    </p>

    <main class="xo-exp-grid">
      <!-- Colonne 1 : file de relecture -->
      <nav class="xo-exp-col" aria-label="File de relecture">
        <h2 class="xo-exp-h2">File</h2>
        <ul class="xo-exp-queue">
          <li v-for="(it, idx) in items" :key="it.id">
            <button type="button" :class="{ 'is-current': idx === current }" :aria-current="idx === current ? 'true' : undefined" @click="current = idx">
              <strong>{{ it.contributor }}</strong>
              <small>{{ it.domain }}</small>
              <span class="xo-status" :data-status="statusKey[it.status]">{{ statusLabel[it.status] }}</span>
            </button>
          </li>
        </ul>
      </nav>

      <!-- Colonne 2 : revue -->
      <section class="xo-exp-col xo-exp-review" aria-label="Relecture">
        <h2 class="xo-exp-h2">{{ item.domain }}</h2>
        <p class="xo-exp-french">{{ item.french }}</p>

        <div class="xo-exp-audio" role="group" aria-label="Audio">
          <button class="xo-btn xo-btn--secondary" type="button" disabled aria-label="Lecture audio (indisponible en démonstration)">
            <XoIcon name="play" /> Écouter
          </button>
          <span class="xo-exp-wavebar" aria-hidden="true"></span>
          <small>Audio de démonstration</small>
        </div>

        <h3 class="xo-exp-h3">Transcription par syllabes</h3>
        <p class="xo-exp-help">Touche une syllabe pour la marquer « à confirmer ».</p>
        <div class="xo-syllables xo-fon" lang="fon">
          <button
            v-for="(syl, i) in item.syllables"
            :key="i"
            type="button"
            class="xo-syllable"
            :class="{ 'xo-syllable--uncertain': syl.uncertain }"
            :aria-pressed="syl.uncertain"
            @click="toggleUncertain(i)"
          >
            {{ syl.t }}<small v-if="syl.uncertain">à confirmer</small>
          </button>
        </div>

        <h3 class="xo-exp-h3">Correction</h3>
        <textarea ref="textarea" v-model="item.correction" class="xo-fon xo-exp-textarea" lang="fon" rows="3" placeholder="Écris la version corrigée…"></textarea>
        <FonKeyboard @insert="insertChar" />

        <div class="xo-exp-actions" role="group" aria-label="Décision">
          <button class="xo-btn" type="button" @click="decide('valide')"><XoIcon name="check" /> Valider <kbd>V</kbd></button>
          <button class="xo-btn xo-btn--secondary" type="button" @click="decide('corrige')"><XoIcon name="pen" /> Corriger <kbd>C</kbd></button>
          <button class="xo-btn xo-btn--secondary xo-exp-reject" type="button" @click="decide('rejete')"><XoIcon name="close" /> Rejeter <kbd>R</kbd></button>
        </div>
      </section>

      <!-- Colonne 3 : avis des 3 Gardiens -->
      <aside class="xo-exp-col" aria-label="Avis des Gardiens">
        <h2 class="xo-exp-h2">Avis des 3 Gardiens</h2>
        <ul class="xo-exp-avis">
          <li v-for="a in item.avis" :key="a.name" class="xo-sticker" :data-verdict="a.verdict" style="--xo-tilt: 0deg">
            <strong>{{ a.name }}</strong>
            <span class="xo-verdict" :data-verdict="a.verdict">{{ verdictLabel[a.verdict] }}</span>
            <p v-if="a.note">{{ a.note }}</p>
          </li>
        </ul>
        <p class="xo-exp-consensus">
          {{ consensus.valider }} pour valider · {{ consensus.corriger }} pour corriger · {{ consensus.rejeter }} pour rejeter
        </p>
      </aside>
    </main>

    <p v-if="toast" class="xo-exp-toast" role="status">{{ toast }}</p>
    <div class="xo-zigzag" aria-hidden="true"></div>
  </div>
</template>
