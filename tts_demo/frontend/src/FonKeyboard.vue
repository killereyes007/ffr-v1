<script setup lang="ts">
import { ref } from "vue";

// Clavier fon autonome : lettres propres au fon + tons sur les voyelles.
const emit = defineEmits<{ (e: "insert", char: string): void }>();

const letters = ["Ɖ", "ɖ", "Ɛ", "ɛ", "Ɔ", "ɔ", "Ɣ", "ɣ"];
const vowels = ["a", "e", "ɛ", "i", "o", "ɔ", "u"];
const tones: Record<string, string[]> = {
  a: ["á", "à", "ǎ", "â", "ā"],
  e: ["é", "è", "ě", "ê", "ē"],
  i: ["í", "ì", "ǐ", "î", "ī"],
  o: ["ó", "ò", "ǒ", "ô", "ō"],
  u: ["ú", "ù", "ǔ", "û", "ū"],
  "ɛ": ["ɛ́", "ɛ̀", "ɛ̌", "ɛ̂", "ɛ̄"],
  "ɔ": ["ɔ́", "ɔ̀", "ɔ̌", "ɔ̂", "ɔ̄"],
};
const open = ref<string | null>(null);

function pick(char: string) {
  emit("insert", char.normalize("NFC"));
  open.value = null;
}
</script>

<template>
  <div class="fon-keyboard" role="group" aria-label="Clavier fon">
    <div class="fon-keyboard-row">
      <button v-for="l in letters" :key="l" type="button" class="fon-key" @mousedown.prevent @click="pick(l)">{{ l }}</button>
    </div>
    <div class="fon-keyboard-row">
      <div v-for="v in vowels" :key="v" class="fon-vowel-wrap">
        <button type="button" class="fon-key" :class="{ 'is-open': open === v }" :aria-expanded="open === v" @mousedown.prevent @click="open = open === v ? null : v">{{ v }}</button>
        <div v-if="open === v" class="fon-tone-drawer">
          <button type="button" class="fon-key fon-key-tone" @mousedown.prevent @click="pick(v)">{{ v }}</button>
          <button v-for="t in tones[v]" :key="t" type="button" class="fon-key fon-key-tone" @mousedown.prevent @click="pick(t)">{{ t }}</button>
        </div>
      </div>
    </div>
  </div>
</template>
