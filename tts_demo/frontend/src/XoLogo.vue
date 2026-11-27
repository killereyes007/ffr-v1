<script setup lang="ts">
// Logo « Carnet des voix » : tambour (dundun) indigo sur pastille jaune,
// ondes sonores terre cuite. SVG pur, couleurs de la charte Xó.
defineProps<{ size?: number }>();
</script>

<template>
  <svg
    class="xo-logo"
    :width="size ?? 48"
    :height="size ?? 48"
    viewBox="0 0 64 64"
    role="img"
    aria-label="Logo Le carnet des voix"
  >
    <rect width="64" height="64" rx="18" fill="#F5B82E" />
    <rect x="1.5" y="1.5" width="61" height="61" rx="16.5" fill="none" stroke="#0B0D22" stroke-width="3" />
    <!-- corps du tambour en sablier -->
    <path d="M17 17c2 8 6 12 7 15-1 3-5 7-7 15h26c-2-8-6-12-7-15 1-3 5-7 7-15Z" fill="#161A3D" />
    <!-- peaux -->
    <ellipse cx="30" cy="17" rx="13" ry="4.5" fill="#E0592A" stroke="#161A3D" stroke-width="2.4" />
    <ellipse cx="30" cy="47" rx="13" ry="4.5" fill="#F6ECD6" stroke="#161A3D" stroke-width="2.4" />
    <!-- cordage en zigzag -->
    <path d="M19 19l7 5-7 5 8 4-8 4 7 5-7 5" fill="none" stroke="#F5B82E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
    <path d="M41 19l-7 5 7 5-8 4 8 4-7 5 7 5" fill="none" stroke="#F5B82E" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
    <!-- pousse (feuille) -->
    <path d="M30 13c0-6 2-9 7-10 1 5-1 9-7 10Z" fill="#1F5E3B" stroke="#161A3D" stroke-width="1.6" stroke-linejoin="round" />
    <!-- ondes sonores -->
    <path d="M49 25q4 7 0 14" fill="none" stroke="#E0592A" stroke-width="3.4" stroke-linecap="round" />
    <path d="M54 20q7 12 0 24" fill="none" stroke="#161A3D" stroke-width="3.4" stroke-linecap="round" />
  </svg>
</template>
