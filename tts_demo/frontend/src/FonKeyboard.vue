<script setup lang="ts">
import { computed, ref } from "vue";
import { FON_TONES, type FonKey } from "./fonInput";

// Clavier fon : uniquement les lettres de l'alphabet fon (pas de q), les tons
// à poser après la voyelle, et la ponctuation de base. `docked` l'affiche
// comme un clavier de téléphone en bas de l'écran.
defineProps<{ docked?: boolean }>();
const emit = defineEmits<{ (e: "key", key: FonKey): void }>();

const ROWS = [
  ["a", "b", "c", "d", "ɖ", "e", "ɛ", "f", "g", "h"],
  ["i", "j", "k", "l", "m", "n", "o", "ɔ", "p", "r"],
  ["s", "t", "u", "v", "w", "x", "y", "z"],
];

const shift = ref(false);
const rows = computed(() =>
  ROWS.map((row) => row.map((letter) => (shift.value ? letter.toUpperCase() : letter))),
);

function press(key: FonKey) {
  emit("key", key);
}
function letter(char: string) {
  press({ kind: "text", text: char });
  shift.value = false;
}
</script>

<template>
  <div class="fkb" :class="{ 'fkb--docked': docked }" role="group" aria-label="Clavier fon">
    <div class="fkb-bar">
      <span class="fkb-title">Clavier fon</span>
      <span class="fkb-tip">Tape la voyelle, puis son ton</span>
      <button v-if="docked" type="button" class="fkb-hide" aria-label="Fermer le clavier" @pointerdown.prevent @click="press({ kind: 'close' })">
        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6" /></svg>
      </button>
    </div>

    <div v-for="(row, r) in rows" :key="r" class="fkb-row">
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
        @pointerdown.prevent
        @click="letter(char)"
      >{{ char }}</button>
      <button
        v-if="r === 2"
        type="button"
        class="fkb-key fkb-key--fn"
        aria-label="Effacer"
        @pointerdown.prevent
        @click="press({ kind: 'backspace' })"
      >⌫</button>
    </div>

    <div class="fkb-row">
      <button
        v-for="tone in FON_TONES"
        :key="tone.mark"
        type="button"
        class="fkb-key fkb-key--tone"
        :aria-label="`${tone.name} (${tone.sample})`"
        :title="`${tone.name} : ${tone.sample}`"
        @pointerdown.prevent
        @click="press({ kind: 'tone', mark: tone.mark })"
      >{{ tone.label }}</button>
      <button type="button" class="fkb-key fkb-key--space" aria-label="Espace" @pointerdown.prevent @click="press({ kind: 'text', text: ' ' })">espace</button>
      <button type="button" class="fkb-key" @pointerdown.prevent @click="press({ kind: 'text', text: ',' })">,</button>
      <button type="button" class="fkb-key" @pointerdown.prevent @click="press({ kind: 'text', text: '.' })">.</button>
      <button type="button" class="fkb-key" @pointerdown.prevent @click="press({ kind: 'text', text: '?' })">?</button>
    </div>
  </div>
</template>

<style scoped>
/* Bloc indigo « autocollant » : identique en mode clair et sombre. */
.fkb {
  display: flex;
  flex-direction: column;
  gap: 7px;
  padding: 8px 6px 10px;
  border: 2px solid #161a3d;
  border-radius: 18px;
  background: #161a3d;
  color: #f6ecd6;
  user-select: none;
  -webkit-user-select: none;
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
  color: #c9c6e2;
  font-size: 12px;
  font-weight: 600;
}
.fkb-hide {
  display: grid;
  place-items: center;
  width: 32px;
  height: 28px;
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
  flex: 1 1 0;
  min-width: 0;
  height: 44px;
  padding: 0;
  border: 0;
  border-radius: 9px;
  background: #f6ecd6;
  color: #161a3d;
  box-shadow: 0 3px 0 #0b0d22;
  font-family: inherit;
  font-size: 19px;
  font-weight: 600;
  line-height: 1;
  cursor: pointer;
}
.fkb-key:active {
  transform: translateY(2px);
  box-shadow: 0 1px 0 #0b0d22;
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
.fkb-key--tone {
  background: #f5b82e;
  font-size: 22px;
  font-weight: 800;
}
.fkb-key--space {
  flex-grow: 3.5;
  font-size: 14px;
  font-weight: 700;
  color: #4a4e78;
}
.fkb-key:focus-visible,
.fkb-hide:focus-visible {
  outline: 3px solid #f5b82e;
  outline-offset: 2px;
}
</style>
