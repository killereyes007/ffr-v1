<script setup lang="ts">
import { computed, onBeforeUnmount, ref } from "vue";
import {
  FON_LATIN_ROWS,
  FON_SPECIAL_LETTERS,
  isToneVowel,
  toneVariants,
  type FonKey,
} from "./fonInput";

// Clavier fon : uniquement l'alphabet fon. Les lettres propres au fon ont leur
// rangée ; les tons s'obtiennent par appui long sur une voyelle (ou clic droit
// sur ordinateur). `docked` l'affiche comme un clavier de téléphone en bas de
// l'écran ; `canListen` ajoute un bouton pour réécouter l'audio en écrivant.
const props = defineProps<{ docked?: boolean; canListen?: boolean; listening?: boolean }>();
const emit = defineEmits<{ (e: "key", key: FonKey): void; (e: "listen"): void }>();

const LONG_PRESS_MS = 380;

const root = ref<HTMLElement | null>(null);
const shift = ref(false);
const tonePopup = ref<{ vowel: string; left: number; top: number } | null>(null);
let pressTimer: ReturnType<typeof setTimeout> | null = null;
let suppressClick = false;

const cased = (letter: string) => (shift.value ? letter.toUpperCase() : letter);
const specialRow = computed(() => FON_SPECIAL_LETTERS.map(cased));
const latinRows = computed(() => FON_LATIN_ROWS.map((row) => row.map(cased)));
const variants = computed(() => (tonePopup.value ? toneVariants(tonePopup.value.vowel) : []));

function insert(text: string) {
  emit("key", { kind: "text", text });
  shift.value = false;
  tonePopup.value = null;
}

function openTones(letter: string, keyEl: HTMLElement) {
  const box = root.value?.getBoundingClientRect();
  const key = keyEl.getBoundingClientRect();
  if (!box) return;
  // Bulle de 5 options au-dessus de la touche, gardée dans la largeur du clavier.
  const width = 5 * 50 + 4 * 6 + 12;
  const center = key.left - box.left + key.width / 2;
  const left = Math.min(Math.max(4, center - width / 2), box.width - width - 4);
  tonePopup.value = { vowel: letter, left, top: key.top - box.top - 62 };
}

function clearTimer() {
  if (pressTimer) clearTimeout(pressTimer);
  pressTimer = null;
}

function onKeyDown(event: PointerEvent, letter: string) {
  tonePopup.value = null;
  suppressClick = false;
  if (!isToneVowel(letter) || event.button > 0) return;
  const keyEl = event.currentTarget as HTMLElement;
  clearTimer();
  pressTimer = setTimeout(() => {
    pressTimer = null;
    suppressClick = true;
    openTones(letter, keyEl);
  }, LONG_PRESS_MS);
}

// Écouté sur tout le clavier : avec une souris, le relâchement a lieu sur la
// bulle et non sur la touche. Glisser d'une voyelle vers un ton puis relâcher
// choisit ce ton.
function onRootPointerUp(event: PointerEvent) {
  clearTimer();
  if (!suppressClick || !tonePopup.value) return;
  const under = document.elementFromPoint(event.clientX, event.clientY);
  const option = under?.closest<HTMLElement>("[data-tone]");
  if (option?.dataset.tone) insert(option.dataset.tone);
}

function onKeyClick(letter: string) {
  if (suppressClick) {
    suppressClick = false;
    return;
  }
  insert(letter);
}

function onContextMenu(event: MouseEvent, letter: string) {
  event.preventDefault();
  if (!isToneVowel(letter)) return;
  clearTimer();
  suppressClick = true;
  openTones(letter, event.currentTarget as HTMLElement);
}

function onRootPointerDown(event: PointerEvent) {
  const target = event.target as HTMLElement;
  if (!tonePopup.value) return;
  // Un simple toucher sur un ton est géré par son clic, pas par le glisser.
  if (target.closest(".fkb-tones")) suppressClick = false;
  else tonePopup.value = null;
}

onBeforeUnmount(clearTimer);
</script>

<template>
  <div
    ref="root"
    class="fkb"
    :class="{ 'fkb--docked': props.docked }"
    role="group"
    aria-label="Clavier fon"
    @pointerdown.capture="onRootPointerDown"
    @pointerup="onRootPointerUp"
  >
    <div class="fkb-bar">
      <span class="fkb-title">Clavier fon</span>
      <span class="fkb-tip">Appui long sur une voyelle pour le ton</span>
      <button
        v-if="props.canListen"
        type="button"
        class="fkb-listen"
        :aria-pressed="props.listening"
        @pointerdown.prevent
        @click="emit('listen')"
      >
        <svg v-if="props.listening" viewBox="0 0 24 24" aria-hidden="true"><path d="M8 6v12M16 6v12" /></svg>
        <svg v-else viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5l11 7-11 7z" /></svg>
        {{ props.listening ? "Pause" : "Réécouter" }}
      </button>
      <button
        v-if="props.docked"
        type="button"
        class="fkb-hide"
        aria-label="Fermer le clavier"
        @pointerdown.prevent
        @click="emit('key', { kind: 'close' })"
      >
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
      </button>
    </div>

    <div class="fkb-row fkb-row--special">
      <button
        v-for="char in specialRow"
        :key="char"
        type="button"
        class="fkb-key fkb-key--special"
        :class="{ 'has-tones': isToneVowel(char) }"
        @pointerdown.prevent="onKeyDown($event, char)"
        @pointerleave="clearTimer"
        @pointercancel="clearTimer"
        @contextmenu="onContextMenu($event, char)"
        @click="onKeyClick(char)"
      >{{ char }}</button>
    </div>

    <div v-for="(row, r) in latinRows" :key="r" class="fkb-row">
      <button
        v-if="r === 2"
        type="button"
        class="fkb-key fkb-key--fn"
        :class="{ 'is-on': shift }"
        :aria-pressed="shift"
        aria-label="Majuscule"
        @pointerdown.prevent
        @click="shift = !shift"
      >⇧</button>
      <button
        v-for="char in row"
        :key="char"
        type="button"
        class="fkb-key"
        :class="{ 'has-tones': isToneVowel(char) }"
        @pointerdown.prevent="onKeyDown($event, char)"
        @pointerleave="clearTimer"
        @pointercancel="clearTimer"
        @contextmenu="onContextMenu($event, char)"
        @click="onKeyClick(char)"
      >{{ char }}</button>
      <button
        v-if="r === 2"
        type="button"
        class="fkb-key fkb-key--fn"
        aria-label="Effacer"
        @pointerdown.prevent
        @click="emit('key', { kind: 'backspace' })"
      >⌫</button>
    </div>

    <div class="fkb-row">
      <button type="button" class="fkb-key fkb-key--space" aria-label="Espace" @pointerdown.prevent @click="insert(' ')">espace</button>
      <button type="button" class="fkb-key" @pointerdown.prevent @click="insert(',')">,</button>
      <button type="button" class="fkb-key" @pointerdown.prevent @click="insert('.')">.</button>
      <button type="button" class="fkb-key" @pointerdown.prevent @click="insert('?')">?</button>
    </div>

    <div
      v-if="tonePopup"
      class="fkb-tones"
      role="group"
      :aria-label="`Tons de ${tonePopup.vowel}`"
      :style="{ left: tonePopup.left + 'px', top: tonePopup.top + 'px' }"
    >
      <button
        v-for="v in variants"
        :key="v.text"
        type="button"
        class="fkb-key fkb-key--tone"
        :data-tone="v.text"
        :aria-label="`${v.text}, ${v.name}`"
        :title="v.name"
        @pointerdown.prevent
        @click="insert(v.text)"
      >{{ v.text }}</button>
    </div>
  </div>
</template>

<style scoped>
/* Bloc indigo « autocollant » : identique en mode clair et sombre. */
.fkb {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 6px 10px;
  border: 2px solid #161a3d;
  border-radius: 18px;
  background: #161a3d;
  color: #f6ecd6;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
}
.fkb--docked {
  flex: none;
  margin: 0 -18px;
  padding-bottom: max(10px, env(safe-area-inset-bottom));
  border-radius: 18px 18px 0 0;
  box-shadow: 0 -6px 18px rgba(11, 13, 34, 0.25);
}
.fkb-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 30px;
  padding: 0 4px 2px;
}
.fkb-title {
  color: #f5b82e;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
.fkb-tip {
  flex: 1;
  min-width: 0;
  color: #c9c6e2;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.2;
}
.fkb-listen {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  height: 30px;
  padding: 0 12px;
  border: 0;
  border-radius: 999px;
  background: #e0592a;
  color: #161a3d;
  font-family: inherit;
  font-size: 13px;
  font-weight: 800;
  cursor: pointer;
}
.fkb-listen svg {
  width: 14px;
  height: 14px;
  fill: currentColor;
  stroke: currentColor;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.fkb-hide {
  display: grid;
  place-items: center;
  width: 32px;
  height: 30px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #f6ecd6;
  cursor: pointer;
}
.fkb-hide svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.fkb-row {
  display: flex;
  gap: 5px;
}
.fkb-key {
  position: relative;
  flex: 1 1 0;
  min-width: 0;
  height: 48px;
  padding: 0;
  border: 0;
  border-radius: 9px;
  background: #f6ecd6;
  color: #161a3d;
  box-shadow: 0 3px 0 #0b0d22;
  font-family: var(--xo-font-body, inherit);
  font-size: 20px;
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
}
.fkb-key:active {
  transform: translateY(2px);
  box-shadow: 0 1px 0 #0b0d22;
}
/* Petit repère : cette touche a des tons en appui long. */
.fkb-key.has-tones::after {
  content: "";
  position: absolute;
  top: 5px;
  right: 6px;
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #e0592a;
}
.fkb-key--special {
  background: #f5b82e;
  font-size: 22px;
  font-weight: 700;
}
.fkb-key--special.has-tones::after {
  background: #161a3d;
}
.fkb-key--fn {
  flex-grow: 1.5;
  background: #3a4290;
  color: #f6ecd6;
  font-size: 18px;
}
.fkb-key--fn.is-on {
  background: #f5b82e;
  color: #161a3d;
}
.fkb-key--space {
  flex-grow: 4;
  font-size: 14px;
  font-weight: 700;
  color: #4a4e78;
}
.fkb-tones {
  position: absolute;
  z-index: 3;
  display: flex;
  gap: 6px;
  padding: 6px;
  border: 2px solid #f5b82e;
  border-radius: 14px;
  background: #232a63;
  box-shadow: 0 6px 0 #0b0d22;
}
.fkb-key--tone {
  flex: none;
  width: 50px;
  background: #f6ecd6;
  font-size: 22px;
}
.fkb-key--tone:hover,
.fkb-key--tone:focus-visible {
  background: #f5b82e;
}
.fkb-key:focus-visible,
.fkb-hide:focus-visible,
.fkb-listen:focus-visible {
  outline: 3px solid #f5b82e;
  outline-offset: 2px;
}
@media (prefers-reduced-motion: reduce) {
  .fkb-key:active {
    transform: none;
  }
}
</style>
