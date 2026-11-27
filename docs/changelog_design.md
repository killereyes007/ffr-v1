# Changelog design — direction « Xó » (phases 2 à 4)

Dossier : `tts_demo/frontend/`. Branche `Rabiatou_baic`. Aucune logique serveur modifiée.

## Fichiers créés

| Fichier | Rôle |
| --- | --- |
| `src/xo.css` | Tokens `--xo-*` et composants de base (boutons pilule, cartes autocollants, frise zigzag, badge de niveau, pastilles de statut et de syllabe, bulle, micro, ondes) |
| `src/xo3d.css` | Couche 3D (cube, inclinaison) et habillage des écrans de première connexion |
| `src/xo-theme.css` | Remappe les variables `--color-*` existantes vers la palette exacte du prompt ; deux contextes de couleur (sur indigo / sur crème) |
| `src/xo-home.css` | Page d'accueil |
| `src/xo-nav.css` | Barre du bas, menu tiroir, bouton retour, refonte de l'assistant |
| `src/xo-onboard.css` | Consentements séparés, profil, choix des domaines |
| `src/xo-play.css` | Page Jouer, enregistrement, fin de mission, passage de niveau, logo |
| `src/Styleguide.vue` | Page `#/styleguide` (couleurs, contrastes calculés, test du fon, composants) |
| `src/XoCube.vue`, `src/XoIcon.vue`, `src/XoLogo.vue`, `src/xoTilt.ts` | Cube 3D, icônes SVG au trait, logo, directive d'inclinaison |
| `src/gamification.ts` | Points d'effort, série, niveaux, progression par domaine (localStorage) |
| `public/fonts/dela-gothic-one/`, `public/fonts/noto-sans/` | Polices locales (Noto Sans : sous-ensemble maison avec diacritiques combinants des tons) |
| `public/icons/logo.svg` | Nouveau logo (tambour + ondes) |

## Fichiers modifiés

| Fichier | Résumé |
| --- | --- |
| `src/App.vue` | Accueil en première page ; porte d'entrée `enterApp` (onboarding au premier JOUER) ; menu et navigation ; consentement en 4 cases, profil, domaines préférés ; page Jouer ; enregistrement voix d'abord, écriture facultative ; fin de mission ; passage de niveau ; assistant refait ; clavier fon avec Ɣ/ɣ |
| `src/identity.ts` | Consentements détaillés, profil, domaines préférés (localStorage) |
| `src/style.css` | Polices et couleurs en dur remplacées (DM Sans/Fraunces → Noto Sans) |
| `src/main.ts` | Import des feuilles `xo-*`, routage `#/styleguide` |
| `index.html`, `public/manifest.webmanifest` | Couleur de thème indigo |

## Phase 5 et extension « feuilles »

- **Vert feuille** (`src/xo-leaf.css`, `XoLeaf.vue`) : extension de la charte demandée par l'équipe, hors du prompt d'origine. `#8CCB6A` (texte toujours indigo, 8,9:1), `#2F7D4F`, `#1F5E3B` (texte crème, 6,5:1). Utilisé pour la réussite, la progression, le statut « Validé », les feuilles de l'accueil, la pousse du logo.
- **Profil** : mode voix / voix + écrit modifiable, refaire le test, accords relus et retirables, effacement des données locales.
- **Mes contributions** : liste locale + légende des 5 statuts (seul « Reçu » est réel).
- **Espace experts** (`#/experts`, `Experts.vue`, `FonKeyboard.vue`) : file, transcription en pastilles de syllabes, clavier fon, avis des 3 Gardiens, Valider / Corriger / Rejeter avec raccourcis V / C / R. **Données de démonstration**, rien n'est envoyé.
- Nouveaux fichiers : `xo-leaf.css`, `xo-phase5.css`, `XoLeaf.vue`, `FonKeyboard.vue`, `Experts.vue`.

## Mode clair / sombre

- **Sombre** = design de base ; **Clair** = fond crème `#F6ECD6`, cartes `#FFFBF2` avec contour indigo, textes `#161A3D` / `#4A4E78`, accent `#9A3412`. Les blocs indigo (progression, assistant, menu, passage de niveau) restent indigo.
- **Auto** (par défaut) suit le réglage du téléphone en direct. Choix mémorisé (`fonTheme`) ; sélecteur dans le menu ☰ et dans le profil.
- Fichiers : `src/theme.ts`, `src/xo-modes.css`, icônes `sun` / `moon` / `auto` dans `XoIcon.vue`.
- Limite : l'espace experts (`#/experts`) et le styleguide restent en sombre. Les contrastes du mode clair n'ont pas encore été recalculés dans `verification_design.md` (couples texte / fond clairs à ajouter).

## À changer côté serveur

1. **Consentement par enregistrement** : l'interface n'affiche plus de case par enregistrement (ni dans la contribution, ni dans l'assistant). Le client envoie toujours `consent: true`, et `assistant_app.py` exige ce champ (l. 1130, 1267). Il faut, côté serveur, vérifier le consentement **enregistré une fois** (par `speaker_id`) au lieu du booléen par requête.
2. **Consentements détaillés** (profil, publication) et **profil** (âge, région, variante) : stockés seulement dans le navigateur. À transmettre avec chaque contribution.
3. **Écriture facultative** : sans texte fon, le client envoie `contribution_mode: "audio_only"`. Aucun changement requis (déjà accepté).
4. **Points et niveaux** : calculés localement et provisoires. Les points complets doivent venir de la validation experte.
5. **Suppression des enregistrements** : aucune route. Le profil renvoie vers le responsable du projet. À créer : suppression par `speaker_id`.
6. **Statuts des contributions** et **espace experts** : aucune route (file de relecture, avis des Gardiens, décisions). L'écran experts n'a aucune authentification : à protéger avant toute mise en ligne.
7. **Nouvelles missions** (Tons, Valider, Décris l'image) : il faut des routes et des données. Elles sont affichées « bientôt ».

## Contradictions et choix à valider

- Le prompt liste 11 domaines ; le code en a 7 avec du contenu. Les 7 sont gardés ouverts, 4 domaines du prompt sont ajoutés verrouillés (contenu à fournir).
- Seuils de niveau (40, 120, 300, 600 points) : inventés, à confirmer.
- Marque : « Le carnet des voix » conservé en attendant la décision.
- Illustrations PNG des domaines et du personnage de l'assistant : palette d'origine.
- Icônes PWA (PNG) : non régénérées avec le nouveau logo.
