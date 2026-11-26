<script setup lang="ts">
// Cube 3D décoratif aux lettres du fon (CSS pur). Masqué des lecteurs d'écran.
const faces = ["ɖ", "ɛ", "ɔ", "ɣ", "Ɖ", "Ɔ"].map((c) => c.normalize("NFC"));
</script>

<template>
  <div class="xo-cube" aria-hidden="true">
    <div class="xo-cube-inner">
      <span v-for="f in faces" :key="f" class="xo-cube-face" lang="fon">{{ f }}</span>
    </div>
  </div>
</template>
