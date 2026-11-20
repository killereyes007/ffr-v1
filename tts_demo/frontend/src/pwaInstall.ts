import { ref } from "vue";

interface BeforeInstallPromptEvent extends Event {
  prompt: () => Promise<void>;
  userChoice: Promise<{ outcome: "accepted" | "dismissed"; platform: string }>;
}

const deferredPrompt = ref<BeforeInstallPromptEvent | null>(null);
const installed = ref(false);

export function listenForInstallPrompt() {
  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    deferredPrompt.value = event as BeforeInstallPromptEvent;
  });
  window.addEventListener("appinstalled", () => {
    deferredPrompt.value = null;
    installed.value = true;
  });
}

export function usePwaInstall() {
  return {
    canInstall: deferredPrompt,
    installed,
    async promptInstall() {
      const event = deferredPrompt.value;
      if (!event) return false;
      await event.prompt();
      const choice = await event.userChoice;
      deferredPrompt.value = null;
      return choice.outcome === "accepted";
    },
  };
}
