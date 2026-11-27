<script setup lang="ts">
// Icônes SVG au trait (pas d'emoji, pas de caractères Unicode décoratifs).
defineProps<{ name: "home" | "mic" | "chat" | "menu" | "close" | "help" | "download" | "back" | "user" | "star" | "check" | "heart" | "book" | "leaf" | "cart" | "building" | "tools" | "drum" | "bus" | "scroll" | "lock" | "flame" | "play" | "pen" | "redo" | "image" | "ear" | "tick" | "list" | "sun" | "moon" | "auto" }>();

const paths: Record<string, string> = {
  home: "M3 11l9-8 9 8M5 10v10h5v-6h4v6h5V10",
  mic: "M12 3a3 3 0 0 0-3 3v5a3 3 0 0 0 6 0V6a3 3 0 0 0-3-3zM5 11a7 7 0 0 0 14 0M12 18v3",
  chat: "M4 5h16v11H9l-5 4z",
  menu: "M4 7h16M4 12h16M4 17h16",
  close: "M6 6l12 12M18 6L6 18",
  help: "M9.5 9a2.5 2.5 0 1 1 3.6 2.2c-.8.5-1.1 1-1.1 1.8M12 17.5v.5M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z",
  download: "M12 4v11m0 0l-4-4m4 4l4-4M5 20h14",
  back: "M15 5l-7 7 7 7",
  user: "M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zM4 21c1-4 4-6 8-6s7 2 8 6",
  star: "M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9z",
  check: "M5 12.5l4.5 4.5L19 7.5",
  heart: "M12 20s-7-4.4-7-10a4 4 0 0 1 7-2.5A4 4 0 0 1 19 10c0 5.6-7 10-7 10z",
  book: "M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2zM4 19V5M9 7h6",
  leaf: "M5 19c0-8 5-14 15-14 0 10-6 15-14 15M5 19l8-8",
  cart: "M3 4h3l2 11h10l2-8H7M10 20v.5M17 20v.5",
  building: "M5 21V4h9v17M14 9h5v12M8 8h3M8 12h3M8 16h3M3 21h18",
  tools: "M14 6a4 4 0 0 0 5 5l-9 9a2 2 0 0 1-3-3zM6 3l3 3-2 2-3-3z",
  drum: "M6 6h12M6 6c1 4 4 6 6 6s5-2 6-6M8 12l-2 8M16 12l2 8M12 12v8",
  bus: "M5 4h14a1 1 0 0 1 1 1v12H4V5a1 1 0 0 1 1-1zM4 11h16M7 20v-3M17 20v-3",
  scroll: "M7 4h12v13a3 3 0 0 1-3 3H5m2-16a3 3 0 0 0-3 3v1h3M9 9h6M9 13h6",
  lock: "M6 11h12v9H6zM8 11V8a4 4 0 0 1 8 0v3",
  flame: "M12 3c1 4 5 5 5 10a5 5 0 0 1-10 0c0-2 1-3 2-4 0 2 1 3 2 3 0-3-1-5 1-9z",
  play: "M8 5l11 7-11 7z",
  pen: "M4 20l1-4L16 5l3 3L8 19zM14 7l3 3",
  redo: "M20 11a8 8 0 1 0-2.3 5.7M20 4v7h-7",
  image: "M4 5h16v14H4zM4 16l5-5 4 4 3-3 4 4M9 9.5v.5",
  ear: "M8 15a4 4 0 0 0 8 0c0-2 2-3 2-6a6 6 0 0 0-12 0M10 9a2 2 0 0 1 4 0c0 2-2 2-2 4",
  tick: "M5 12l4 4 10-10M5 20h14",
  list: "M9 6h11M9 12h11M9 18h11M4 6h.5M4 12h.5M4 18h.5",
  sun: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4",
  moon: "M20 14.5A8 8 0 0 1 9.5 4 8 8 0 1 0 20 14.5z",
  auto: "M12 3a9 9 0 1 0 0 18zM12 3a9 9 0 0 1 0 18",
};
</script>

<template>
  <svg
    class="xo-icon"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="2.2"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
  >
    <path :d="paths[name]" />
  </svg>
</template>
