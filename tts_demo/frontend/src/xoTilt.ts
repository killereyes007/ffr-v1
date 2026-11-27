import type { Directive } from "vue";

// Directive v-xo-tilt : incline l'élément en 3D vers le pointeur (±6°).
// Sans effet si l'utilisateur demande moins d'animations.
const MAX = 6;

export const vXoTilt: Directive<HTMLElement> = {
  mounted(el) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    el.classList.add("xo-tilt");
    const move = (e: PointerEvent) => {
      const r = el.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      el.classList.add("is-tilting");
      el.style.setProperty("--ry", `${(x * MAX * 2).toFixed(2)}deg`);
      el.style.setProperty("--rx", `${(-y * MAX * 2).toFixed(2)}deg`);
    };
    const reset = () => {
      el.classList.remove("is-tilting");
      el.style.setProperty("--rx", "0deg");
      el.style.setProperty("--ry", "0deg");
    };
    el.addEventListener("pointermove", move);
    el.addEventListener("pointerleave", reset);
    el.addEventListener("pointerup", reset);
  },
};
