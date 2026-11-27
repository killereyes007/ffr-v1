# Vérification du design — direction « Xó » (phase 6)

Date : 2026-11-26. Build de production (`vite preview`), Chromium sans écran (patchright).
Ce qui a été **mesuré** est séparé de ce qui **reste à tester sur appareil réel**.

## 1. Contrastes (WCAG, seuil 4,5 : 1) — mesuré

Calcul par script sur les 21 couples texte / fond effectivement utilisés. **0 échec.**

| Usage | Couple | Ratio | |
| --- | --- | --- | --- |
| Texte principal sur indigo | `#F6ECD6` / `#161A3D` | 14,32 | OK |
| Texte secondaire sur indigo | `#D9D3E8` / `#161A3D` | 11,55 | OK |
| Petites mentions sur indigo | `#B9B6D3` / `#161A3D` | 8,56 | OK |
| Crème sur surface (HUD, assistant) | `#F6ECD6` / `#232A63` | 11,30 | OK |
| Secondaire sur surface | `#D9D3E8` / `#232A63` | 9,12 | OK |
| Mentions sur surface | `#B9B6D3` / `#232A63` | 6,76 | OK |
| Jaune sur indigo (kicker, titres) | `#F5B82E` / `#161A3D` | 9,43 | OK |
| Jaune sur surface | `#F5B82E` / `#232A63` | 7,44 | OK |
| Indigo sur jaune (boutons, mission du jour) | `#161A3D` / `#F5B82E` | 9,43 | OK |
| Indigo sur terre cuite (micro, À valider) | `#161A3D` / `#E0592A` | **4,51** | OK (le plus juste) |
| Terre cuite sur indigo (Rejeter, experts) | `#E0592A` / `#161A3D` | **4,51** | OK |
| Indigo sur crème (cartes) | `#161A3D` / `#F6ECD6` | 14,32 | OK |
| Texte atténué sur crème | `#4A4E78` / `#F6ECD6` | 6,74 | OK |
| Alerte sur crème | `#9A3412` / `#F6ECD6` | 6,22 | OK |
| Indigo sur lavande (Reçu, bulle guide) | `#161A3D` / `#D9D3E8` | 11,55 | OK |
| Atténué sur lavande (légende) | `#4A4E78` / `#D9D3E8` | 5,44 | OK |
| Indigo sur carte verrouillée | `#161A3D` / `#B9B6D3` | 8,56 | OK |
| Indigo sur vert feuille (Validé, 3e carte) | `#161A3D` / `#8CCB6A` | 8,70 | OK |
| Vert feuille sur indigo (progression) | `#8CCB6A` / `#161A3D` | 8,70 | OK |
| Crème sur vert profond | `#F6ECD6` / `#1F5E3B` | 6,57 | OK |
| Crème sur indigo (bouton Commencer) | `#F6ECD6` / `#161A3D` | 14,32 | OK |

Limite : seuls les couples listés sont vérifiés ; l'état désactivé des boutons (opacité réduite) n'est pas évalué, comme le veut WCAG pour les éléments inactifs.

## 2. Rendu à 360, 768 et 1280 px — mesuré (absence de débordement) + captures

6 écrans × 3 largeurs = **18 combinaisons, aucun défilement horizontal** : accueil, Jouer, mission (enregistrement), assistant, profil, mes contributions.
Espace experts : contrôlé à 1280 px (3 colonnes) et 390 px (empilé), sans débordement.
Le jeu reste dans un cadre « téléphone » de 430 px sur bureau (comportement d'origine conservé).

Non couverts par ce passage : l'écran d'onboarding complet à 768 / 1280 px (vérifié à 390 px seulement), la fin de mission et le passage de niveau à 360 px (vérifiés à 390 px).

## 3. Cibles tactiles (≥ 48 px) — mesuré, 3 défauts corrigés

Le contrôle a trouvé et fait corriger : les puces de difficulté (33 px), le bouton « Changer de domaine » (43 px) et l'étiquette « PHRASE » qui chevauchait le texte à 360 px. Restant : les cases à cocher du profil font 26 px, mais leur libellé cliquable fait ≥ 48 px de haut.

## 4. `prefers-reduced-motion: reduce` — mesuré

Avec la préférence activée : le cube 3D, les anneaux du micro et les feuilles ont `animation-name: none`. Les inclinaisons au toucher (`v-xo-tilt`) ne s'installent pas. Les ondes, anneaux de l'enregistrement et animations de fin de mission ont une règle `reduce` dans le CSS, **non mesurée à l'écran** (nécessitent un enregistrement réel).

## 5. Navigation au clavier et focus visible — mesuré

Tab parcourt dans l'ordre : menu, JOUER, Comment ça marche, assistant, barre du bas. Chaque élément a un contour de 3 px (`outline: solid 3px`). Menu : focus placé sur le premier élément, Échap ferme. Espace experts : raccourcis V / C / R (inactifs quand on tape dans un champ).

## 6. Poids de la page d'accueil — mesuré (transfert, gzip)

| Fichier | Transfert |
| --- | --- |
| JavaScript | 57,2 Ko |
| CSS | 13,9 Ko |
| HTML, logo SVG, icône | 2,4 Ko |
| **Total hors polices** | **73,6 Ko** (objectif < 500 Ko : atteint) |
| Polices au premier affichage (Dela Gothic One latin + Noto Sans) | 162,7 Ko |

Les illustrations PNG des domaines ne sont plus chargées sur l'accueil.

## 7. Affichage du fon — **non vérifié sur appareil**

Vérifié seulement sur Chromium de bureau : « Un nɔ́ ɖu nǔ » et « ɖ ɛ ɔ ɣ Ɖ Ɛ Ɔ Ɣ á à ǎ â ɛ́ ɛ̀ ɛ̌ ɛ̂ ɔ́ ɔ̀ ɔ̌ ɔ̂ » s'affichent sans carré ni repli. Le sous-ensemble Noto Sans embarqué contient tous ces caractères et les 4 diacritiques combinants (contrôlé par script).
**À faire par l'équipe** : ouvrir `#/styleguide` sur Chrome Android et Safari iOS et regarder la section « Test d'affichage du fon » (aucun carré, aucun ton décalé).

## 8. Reste à faire / recommandations

- Tester l'enregistrement réel (le micro était simulé) et le fon sur téléphones.
- Les polices DM Sans et Fraunces ne sont plus utilisées mais leurs fichiers et `@font-face` sont toujours dans le projet (non supprimés, règle « ne supprime aucun fichier ») : à retirer pour alléger la PWA.
- Icônes PWA (PNG) à régénérer depuis `public/icons/logo.svg`.
- Pas de contrôle qualité d'enregistrement (« trop bas, trop de bruit ») : fonctionnalité absente.
- Espace experts : sans authentification, données de démonstration.
- Les points restants côté serveur sont dans `docs/changelog_design.md`.

## Fichiers modifiés et créés

Liste complète avec résumé par fichier : voir `docs/changelog_design.md`.
Ajouts de cette phase : `src/xo-phase5.css` (cibles tactiles, étiquettes), `docs/verification_design.md`.
