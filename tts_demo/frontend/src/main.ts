import { createApp } from "vue";
import App from "./App.vue";
import Styleguide from "./Styleguide.vue";
import Experts from "./Experts.vue";
import "./style.css";
import "./xo.css";
import "./xo3d.css";
import "./xo-theme.css";
import "./xo-home.css";
import "./xo-nav.css";
import "./xo-onboard.css";
import "./xo-play.css";
import "./xo-leaf.css";
import "./xo-phase5.css";
import "./xo-modes.css";
import "./xo-rounds.css";
import { initTheme } from "./theme";
import { listenForInstallPrompt } from "./pwaInstall";

initTheme();
listenForInstallPrompt();

if ("serviceWorker" in navigator) {
  window.addEventListener("load", () => {
    navigator.serviceWorker
      .register("/game-sw.js", { scope: "/game" })
      .catch(() => {
        // Installable experience degrades gracefully without a service worker.
      });
  });
}

// Page interne de démonstration de la direction « Xó » : <url>#/styleguide
// Pages internes : <url>#/styleguide et <url>#/experts (hors navigation du jeu)
const hash = window.location.hash;
const standalone = hash === "#/styleguide" || hash === "#/experts";
if (standalone) {
  // Pleine largeur : le jeu est lui contraint à un cadre téléphone.
  document.body.style.padding = "0";
  document.body.style.background = "#161A3D";
  document.body.style.placeItems = "start stretch";
  document.getElementById("app")!.style.width = "100%";
}
createApp(hash === "#/styleguide" ? Styleguide : hash === "#/experts" ? Experts : App).mount("#app");
