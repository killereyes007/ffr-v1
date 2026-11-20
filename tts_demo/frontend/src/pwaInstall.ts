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

// iOS Safari never fires beforeinstallprompt — there is no API to trigger
// "Add to Home Screen" from script there. The only thing we can do is detect
// it and show instructions for the manual Share-sheet flow instead of a
// button that would otherwise just silently never appear.
function isIosSafari(): boolean {
  const ua = window.navigator.userAgent;
  const isIos = /iPad|iPhone|iPod/.test(ua) && !(window as unknown as { MSStream?: unknown }).MSStream;
  const isStandalone =
    (window.navigator as unknown as { standalone?: boolean }).standalone === true ||
    window.matchMedia?.("(display-mode: standalone)").matches;
  return isIos && !isStandalone;
}

export function usePwaInstall() {
  return {
    canInstall: deferredPrompt,
    installed,
    isIosManualInstall: isIosSafari(),
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
