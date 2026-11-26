<script setup lang="ts">
// Page interne de démonstration de la direction « Xó » (phase 2).
// Accès : <url du jeu>#/styleguide
const FON_SAMPLE = "Un nɔ́ ɖu nǔ".normalize("NFC"); // TODO données : phrase à valider par un linguiste
const FON_CHARS = "ɖ ɛ ɔ ɣ Ɖ Ɛ Ɔ Ɣ á à ǎ â ɛ́ ɛ̀ ɛ̌ ɛ̂ ɔ́ ɔ̀ ɔ̌ ɔ̂".normalize("NFC");

const colors = [
  ["--xo-indigo", "#161A3D", "Fond principal"],
  ["--xo-surface", "#232A63", "Surface"],
  ["--xo-border", "#3A4290", "Bordures"],
  ["--xo-cream", "#F6ECD6", "Texte / fond crème"],
  ["--xo-text-2", "#D9D3E8", "Texte secondaire"],
  ["--xo-text-3", "#B9B6D3", "Petites mentions"],
  ["--xo-yellow", "#F5B82E", "Accent principal"],
  ["--xo-terracotta", "#E0592A", "Accent secondaire"],
  ["--xo-shadow-color", "#0B0D22", "Ombre dure"],
  ["--xo-leaf", "#8CCB6A", "Vert feuille (extension)"],
  ["--xo-leaf-mid", "#2F7D4F", "Vert moyen (frise)"],
  ["--xo-leaf-deep", "#1F5E3B", "Vert profond (extension)"],
  ["--xo-on-cream-muted", "#4A4E78", "Texte atténué sur crème"],
  ["--xo-on-cream-alert", "#9A3412", "Alerte sur crème"],
];

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5]
    .map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((c) => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4));
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}
function ratio(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x);
  return (hi + 0.05) / (lo + 0.05);
}

// [texte, fond, usage]
const pairs: [string, string, string][] = [
  ["#F6ECD6", "#161A3D", "Texte principal sur indigo"],
  ["#D9D3E8", "#161A3D", "Texte secondaire sur indigo"],
  ["#B9B6D3", "#161A3D", "Petites mentions sur indigo"],
  ["#F6ECD6", "#232A63", "Texte crème sur surface"],
  ["#161A3D", "#F5B82E", "Indigo sur jaune (boutons)"],
  ["#161A3D", "#E0592A", "Indigo sur terre cuite"],
  ["#161A3D", "#F6ECD6", "Indigo sur crème"],
  ["#4A4E78", "#F6ECD6", "Texte atténué sur crème"],
  ["#9A3412", "#F6ECD6", "Alerte sur crème"],
  ["#161A3D", "#8CCB6A", "Indigo sur vert feuille (Validé, progression)"],
  ["#F6ECD6", "#1F5E3B", "Crème sur vert profond"],
  ["#161A3D", "#B9B6D3", "Carte verrouillée"],
];
const rows = pairs.map(([fg, bg, use]) => {
  const r = ratio(fg, bg);
  return { fg, bg, use, r: r.toFixed(2), ok: r >= 4.5 };
});

const statuses = [
  ["recu", "Reçu"],
  ["relecture", "En relecture"],
  ["expert", "À valider par un expert"],
  ["valide", "Validé"],
  ["rejete", "Rejeté"],
] as const;
</script>

<template>
  <div class="xo-page sg">
    <div class="xo-zigzag" aria-hidden="true" />
    <main class="sg-main">
      <div class="sg-head">
        <h1 class="xo-title sg-h1">Xó — styleguide</h1>
        <p class="sg-lead">Fondations de la direction artistique (phase 2). Page interne, non liée à la navigation.</p>
      </div>

      <section>
        <h2 class="xo-title sg-h2">Couleurs</h2>
        <div class="sg-swatches">
          <div v-for="c in colors" :key="c[0]" class="sg-swatch">
            <span class="sg-chip" :style="{ background: c[1] }" />
            <span><b>{{ c[0] }}</b><br />{{ c[1] }} · {{ c[2] }}</span>
          </div>
        </div>
      </section>

      <section>
        <h2 class="xo-title sg-h2">Contrastes (WCAG, seuil 4,5 : 1)</h2>
        <table class="sg-table">
          <thead>
            <tr><th>Aperçu</th><th>Usage</th><th>Ratio</th><th>Résultat</th></tr>
          </thead>
          <tbody>
            <tr v-for="r in rows" :key="r.fg + r.bg">
              <td><span class="sg-sample" :style="{ color: r.fg, background: r.bg }">Aa</span></td>
              <td>{{ r.use }} <small>({{ r.fg }} / {{ r.bg }})</small></td>
              <td>{{ r.r }}</td>
              <td>{{ r.ok ? "OK" : "ÉCHEC" }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <section>
        <h2 class="xo-title sg-h2">Typographie</h2>
        <p class="xo-title sg-h1">Titre en Dela Gothic One</p>
        <p>Corps de texte en Noto Sans : une consigne par écran, au tutoiement.</p>
        <p class="sg-small">Petite mention en <span style="color: var(--xo-text-3)">#B9B6D3</span>.</p>
      </section>

      <section>
        <h2 class="xo-title sg-h2">Test d'affichage du fon (Noto Sans)</h2>
        <p class="xo-fon sg-fon-big" lang="fon">{{ FON_SAMPLE }}</p>
        <p class="xo-fon sg-fon-chars" lang="fon">{{ FON_CHARS }}</p>
        <p class="sg-small">
          À vérifier sur Chrome Android et Safari iOS : aucun carré, aucun diacritique décalé ou remplacé par une autre police.
          Phrase de démonstration, à valider par un linguiste.
        </p>
      </section>

      <section>
        <h2 class="xo-title sg-h2">Frise zigzag</h2>
        <div class="xo-zigzag" aria-hidden="true" />
        <div class="sg-gap" />
        <div class="xo-zigzag xo-zigzag--thin" aria-hidden="true" />
      </section>

      <section>
        <h2 class="xo-title sg-h2">Boutons pilule</h2>
        <div class="sg-row">
          <button class="xo-btn" type="button">Jouer</button>
          <button class="xo-btn xo-btn--secondary" type="button">Passer</button>
          <button class="xo-btn xo-btn--lg" type="button">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
            </svg>
            Enregistrer (64 px)
          </button>
          <button class="xo-btn" type="button" disabled>Désactivé</button>
        </div>
      </section>

      <section>
        <h2 class="xo-title sg-h2">Cartes autocollants</h2>
        <div class="sg-cards">
          <article class="xo-sticker" style="--xo-tilt: -4deg">
            <h3>Marché et commerce</h3>
            <p>Mission du jour ouverte.</p>
            <div class="xo-progress" role="progressbar" aria-valuenow="60" aria-valuemin="0" aria-valuemax="100" aria-label="Progression"><span style="width: 60%" /></div>
          </article>
          <article class="xo-sticker xo-sticker--yellow" style="--xo-tilt: 3deg">
            <h3>Santé</h3>
            <p>3 missions sur 10.</p>
            <div class="xo-progress" role="progressbar" aria-valuenow="30" aria-valuemin="0" aria-valuemax="100" aria-label="Progression"><span style="width: 30%" /></div>
          </article>
          <article class="xo-sticker xo-sticker--locked" style="--xo-tilt: -2deg">
            <h3>Proverbes et contes</h3>
            <p>Verrouillé : niveau 4 requis.</p>
          </article>
        </div>
      </section>

      <section>
        <h2 class="xo-title sg-h2">Badge de niveau, entouré de la frise</h2>
        <div class="xo-level-frame">
          <div class="xo-zigzag xo-zigzag--thin" style="width: 240px" aria-hidden="true" />
          <span class="xo-level"><b>3</b> Confirmé</span>
          <div class="xo-zigzag xo-zigzag--thin" style="width: 240px" aria-hidden="true" />
        </div>
      </section>

      <section>
        <h2 class="xo-title sg-h2">Pastilles de statut</h2>
        <div class="sg-row">
          <span v-for="s in statuses" :key="s[0]" class="xo-status" :data-status="s[0]">{{ s[1] }}</span>
        </div>
      </section>

      <section>
        <h2 class="xo-title sg-h2">Pastilles de syllabes</h2>
        <div class="xo-syllables xo-fon" lang="fon">
          <span class="xo-syllable">Un</span>
          <span class="xo-syllable">nɔ́</span>
          <span class="xo-syllable xo-syllable--uncertain">ɖu<small>à confirmer</small></span>
          <span class="xo-syllable">nǔ</span>
        </div>
      </section>

      <section>
        <h2 class="xo-title sg-h2">Bulle de l'assistant</h2>
        <div class="xo-bubble">
          <span class="xo-bubble-name">Nom du guide (à valider)</span>
          Au marché, tu demandes le prix des tomates. Prêt ?
        </div>
      </section>

      <section>
        <h2 class="xo-title sg-h2">Micro central et ondes sonores</h2>
        <div class="sg-row sg-row--center">
          <button class="xo-mic" type="button" aria-label="Enregistrer ta voix">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
              <rect x="9" y="3" width="6" height="11" rx="3" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3" />
            </svg>
          </button>
          <div class="xo-wave" aria-hidden="true">
            <span v-for="n in 14" :key="n" />
          </div>
        </div>
        <p class="sg-small">Animations coupées avec <code>prefers-reduced-motion: reduce</code>.</p>
      </section>
    </main>
    <div class="xo-zigzag" aria-hidden="true" />
  </div>
</template>

<style scoped>
.sg-head {
  display: block;
}
.sg-main {
  display: grid;
  width: min(960px, 100%);
  gap: 40px;
  margin: 0 auto;
  padding: 32px 16px 56px;
}
.sg-h1 {
  font-size: clamp(28px, 6vw, 44px);
}
.sg-h2 {
  margin-bottom: 16px;
  color: var(--xo-yellow);
  font-size: 20px;
  text-shadow: none;
}
.sg-lead,
.sg-small {
  margin: 8px 0 0;
  color: var(--xo-text-2);
}
.sg-small {
  font-size: 14px;
  color: var(--xo-text-3);
}
.sg-swatches {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
}
.sg-swatch {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 14px;
}
.sg-chip {
  width: 48px;
  height: 48px;
  flex: none;
  border: 2px solid var(--xo-cream);
  border-radius: 12px;
}
.sg-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}
.sg-table th,
.sg-table td {
  padding: 8px;
  border-bottom: 1px solid var(--xo-border);
  text-align: left;
}
.sg-sample {
  display: inline-block;
  min-width: 44px;
  padding: 4px 8px;
  border-radius: 8px;
  text-align: center;
  font-weight: 800;
}
.sg-fon-big {
  margin: 0;
  font-size: 40px;
  font-weight: 700;
}
.sg-fon-chars {
  margin: 8px 0 0;
  font-size: 28px;
  letter-spacing: 0.06em;
}
.sg-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
}
.sg-row--center {
  padding: 24px 24px;
  gap: 40px;
}
.sg-cards {
  display: grid;
  gap: 24px;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  padding: 8px;
}
.sg-gap {
  height: 12px;
}
</style>
