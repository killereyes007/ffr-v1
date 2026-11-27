import { ref } from "vue";

// Thème : « auto » (suit le téléphone), « light » ou « dark ».
// Appliqué sur <html data-theme="light|dark"> ; le choix est mémorisé localement.
export type ThemePref = "auto" | "light" | "dark";

const KEY = "fonTheme";
const query = window.matchMedia("(prefers-color-scheme: light)");

function readPref(): ThemePref {
  try {
    const v = localStorage.getItem(KEY);
    return v === "light" || v === "dark" || v === "auto" ? v : "auto";
  } catch {
    return "auto";
  }
}

export const themePref = ref<ThemePref>(readPref());

function resolved(): "light" | "dark" {
  if (themePref.value === "auto") return query.matches ? "light" : "dark";
  return themePref.value;
}

function apply() {
  const mode = resolved();
  document.documentElement.dataset.theme = mode;
  document
    .querySelector('meta[name="theme-color"]')
    ?.setAttribute("content", mode === "light" ? "#F6ECD6" : "#161A3D");
}

export function setTheme(pref: ThemePref) {
  themePref.value = pref;
  try {
    localStorage.setItem(KEY, pref);
  } catch {
    // stockage indisponible : le choix vaut pour cette session seulement
  }
  apply();
}

export function initTheme() {
  apply();
  query.addEventListener("change", () => {
    if (themePref.value === "auto") apply();
  });
}
