# Audit du design — jeu « Le carnet des voix » (FonNLP Xó)

Phase 1 (lecture seule) du document `04_Design_Xo_integration_ffr-v1.md`.
Aucun fichier du front n'a été modifié. **En attente de validation de la matrice (section 4).**

Périmètre audité : `tts_demo/frontend/` (branche `Rabiatou_baic`).

## 1. Stack

| Élément | Constat |
| --- | --- |
| Langage / framework | TypeScript, **Vue 3.5** (composition API, `<script setup>`) |
| Build | **Vite 6**, `vue-tsc` pour les types (`package.json`) |
| CSS | **CSS pur** dans un seul fichier `src/style.css` (~1650 lignes) : pas de Tailwind, Bootstrap ni SCSS |
| Composants | **Un seul composant** `src/App.vue` (~1890 lignes) : tous les écrans y sont |
| Routage | Aucun routeur. Écrans pilotés par des variables : `appStage` (onboarding, identify, writing-check) puis `activeScreen` (`home`, `game`, `assistant`) (`App.vue` l.1197–1818) |
| Assets | `public/` : polices locales (Fraunces, DM Sans), icônes PWA, images de domaines et du héros |
| PWA | `manifest.webmanifest`, `game-sw.js`, `pwaInstall.ts` (installation, hors-ligne) |
| Autres modules | `identity.ts`, `analytics.ts`, `main.ts` |
| Backend | FastAPI (`assistant_app.py`, port 7861) ; proxy Vite `/training-phrases` ; `base` Vite = `/game-assets/` |

## 2. Design existant

Identité actuelle : **« carnet » chaleureux** (crème, terre cuite, ocre, vert), claire, éditoriale.

| Composant | Valeur actuelle | Où |
| --- | --- | --- |
| Fond | `#FAF5EC`, `#F5EBDD` ; surface `#FFFDF8` ; carte `#F0E5D5` | `style.css` l.67–71 |
| Primaire | terre cuite `#A9472D` (hover `#873A27`) | l.74–76 |
| Accent | ocre `#D5A044` | l.77–78 |
| Textes | `#38251D` titres, `#2B241F` corps, `#75685B` secondaire | l.81–84 |
| États | succès `#426348`, alerte `#A56B17`, erreur `#B64035` | l.91–95 |
| Titres | **Fraunces** (serif), locale | l.98, `@font-face` l.11–42 |
| Corps | **DM Sans**, locale | l.99, l.43–57 |
| Rayons | carte 20 px, bouton 12 px, champ 12 px | l.102–104 |
| Ombre | `0 3px 12px` douce | l.107 |
| Bouton | `.button`, hauteur mini 48 px | l.960 |
| Navigation | barre basse `.phone-nav` (3 entrées : Ma voix, Accueil, Assistant) + bouton « ⌂ » en en-tête | `App.vue` l.1957–1985 ; `style.css` l.1083–1130 |
| En-tête / logo | SVG de tambour inline, texte « Le carnet des voix » | `App.vue` l.1342–1384 |
| Cadre téléphone | Cadre arrondi 38 px sur ordinateur | `style.css` l.161 |
| Focus | `:focus-visible` global | l.1130 |

## 3. Écrans présents et manquants (par rapport à FonNLP Xó)

| Besoin Xó | État |
| --- | --- |
| Accueil mobile | **Présent** (`welcome-screen`), mais ton « aventure », sans compteurs, sans « comment ça marche », sans citation |
| Mission Tons (écoute et choix de l'écriture) | **Manquant** : le jeu actuel demande de *traduire* une phrase et de l'*enregistrer* |
| Mission Traduire / Dire | **Présent** (écran `game`) |
| Mission Valider (valider le travail d'autrui) | **Manquant** |
| Assistant vocal | Présent (hors périmètre Xó) |
| Onboarding, identification, test d'écriture | Présents (3 étapes avant l'accueil) |
| Espace experts (files de relecture, validation, raccourcis V/C/R) | **Manquant** |
| Points, séries de jours, progression « Mission 3 sur 10 » | Partiel (à vérifier dans `App.vue`) |
| Clavier fon (ɖ ɛ ɔ ɣ, tons) | **À vérifier** : pas de composant dédié repéré |
| Consentement / retrait des données | Mention à confirmer en pied de page : **manquant** |
| `/styleguide` | **Manquant** |

## 4. Matrice de fusion (à valider)

| Garder | Adapter (direction Xó) | Ajouter |
| --- | --- | --- |
| Stack Vue 3 + Vite + CSS pur : aucune raison de migrer | Palette : passer du crème/terre cuite à indigo + jaune + terre cuite, via de **nouveaux** tokens `--xo-*` (sans renommer `--color-*`) | Frise zigzag CSS, boutons pilule, cartes autocollants |
| PWA (hors-ligne, installation) : atout pour le Bénin | Titres : Fraunces → **Dela Gothic One** (français uniquement) | Micro pulsé, barres d'ondes (coupées si `prefers-reduced-motion`) |
| Polices locales (pas de dépendance externe) : héberger aussi Dela Gothic One et Noto Sans | Corps et **tout le fon** : DM Sans → **Noto Sans** (DM Sans ne garantit pas ɖ ɛ ɔ ɣ avec tons combinés) | Pastilles de syllabes (incertaine = bordure pointillée + « à confirmer ») |
| Parcours onboarding + identification + test d'écriture | Rayons : 12 px → 24 px (cartes) et 999 px (pilules) | Clavier fon (touches ≥ 48 px) |
| Missions Traduire et Dire (cœur de la collecte) | Navigation : passer à **Missions, Comment ça marche, Experts, Communauté** + bouton JOUER ; la barre basse mobile reste, avec libellés clairs | Mission Tons et mission Valider |
| Assistant vocal (bonus) | Hauteur des boutons : 48 px → 64 px pour les choix de jeu | Espace experts (3 colonnes bureau, empilé en mobile) |
| Hauteur tactile ≥ 48 px, focus visible | Icônes : caractères Unicode (◉ ⌂ ◈ ⇩) → **SVG au trait** (pas d'emoji) | Compteurs `[X]`, bandeau citation, consentement et retrait des données |
| | Découpage de `App.vue` (1890 lignes) en composants réutilisables | Page `/styleguide` |

Justifications : on conserve ce qui est technique (stack, PWA, parcours), on adapte ce qui est visuel (tokens, polices, rayons) pour obtenir l'ambiance festive voulue, et on ajoute ce qui manque au produit (missions Tons et Valider, espace experts, consentement).

## 5. Conflits et risques

1. **Marque déjà en place** : « Le carnet des voix » (titre, manifeste, texte iOS) contre « FonNLP Xó ». À trancher : renommer, ou garder un sous-titre.
2. **Palette opposée** : fond clair actuel contre fond indigo sombre Xó. Choisir un mode par écran pour éviter un mélange incohérent.
3. **Polices** : Fraunces et DM Sans sont chargées via `@font-face` local. Si on remplace les polices, retirer les anciennes pour ne pas alourdir la PWA.
4. **Poids** : `home-hero.png` et les images de domaines pèsent de l'ordre de centaines de lignes de binaire. Objectif Xó : accueil < 500 Ko hors polices. À mesurer.
5. **Classes CSS** : un seul fichier global, donc risque de chevauchement. Préfixer les nouvelles classes `xo-`.
6. **Accessibilité** : contraste 4,5:1 à vérifier (le jaune et la terre cuite exigent du texte indigo) ; le texte fon est à tester sur Chrome Android et Safari iOS ; `aria-label` à ajouter aux boutons icônes.
7. **Collecte de données** : le consentement explicite et le retrait des données sont requis avant toute publication d'un corpus. À placer dans le parcours, pas seulement en pied de page.
8. **Contenu en fon** : toute phrase fon hors « Un nɔ́ ɖu nǔ » doit être marquée « à valider par un linguiste ».
9. **Maintenabilité** : le fichier monolithique `App.vue` freine la refonte. À découper avant d'ajouter les nouveaux écrans.

## 6. Proposition d'enchaînement (après validation)

1. Phase 2 : tokens `--xo-*`, polices, composants et `/styleguide`.
2. Phase 3 : accueil, mission Tons, puis espace experts (avec données fictives isolées).
3. Phase 4 : contrôle qualité (360 / 768 / 1440 px, contrastes, poids) et `docs/changelog_design.md`.
