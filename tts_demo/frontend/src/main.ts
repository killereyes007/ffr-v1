import { createApp } from "vue";
import App from "./App.vue";
import "./style.css";
import { listenForInstallPrompt } from "./pwaInstall";

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

createApp(App).mount("#app");
