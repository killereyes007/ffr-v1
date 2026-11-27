# Contexte

Projet : plateforme **FonNLP Xó** (Benin AI Community). C'est une plateforme culturelle et ludique pour collecter et valider des données en langue fon :

1. des joueurs réalisent des missions (traduire, dire une phrase à voix haute, choisir les bons tons, valider le travail des autres) ;
2. l'IA pré-note chaque contribution et envoie les cas douteux en relecture ;
3. des experts de la langue (linguistes, enseignants, locuteurs confirmés) valident les tons et l'orthographe ;
4. seules les données validées, avec le consentement du contributeur, entrent dans le corpus ouvert.

Le projet existant se trouve dans ce dossier (`ffr-v1`) et **possède déjà un design**. Une nouvelle direction artistique (décrite plus bas) a été validée comme inspiration : ambiance festive et culturelle béninoise, dans l'esprit d'un site de festival afro-urbain. Elle doit **enrichir** le design existant, pas l'écraser sans accord.

Travaille en **audit d'abord**, par phases. À la fin de chaque phase, arrête-toi, résume, signale explicitement chaque ambiguïté et attends ma validation. Ne supprime aucun fichier existant. Ne modifie rien avant la fin de la phase 1.

# Direction artistique de référence (« Xó »)

## Couleurs

| Rôle | Valeur |
| --- | --- |
| Fond principal (indigo) | `#161A3D` |
| Surface (cartes, bandeaux) | `#232A63` |
| Bordures sur fond sombre | `#3A4290` |
| Texte principal sur fond sombre (crème) | `#F6ECD6` |
| Texte secondaire sur fond sombre | `#D9D3E8`, et `#B9B6D3` pour les petites mentions |
| Accent principal (jaune soleil) | `#F5B82E` |
| Accent secondaire (terre cuite) | `#E0592A` |
| Ombre dure des boutons et cartes | `#0B0D22` |
| Texte sur fond crème | `#161A3D` ; texte atténué `#4A4E78` ; texte d'alerte `#9A3412` |

Règles de contraste :
- sur le jaune et sur la terre cuite, le texte est **toujours** indigo `#161A3D`, jamais crème ;
- tout texte respecte un contraste de 4,5:1.

## Typographie

- Titres en français : **Dela Gothic One** (Google Fonts), en capitales, avec une ombre portée dure (`text-shadow: 0 6px 0 #0B0D22`).
- Corps de texte **et tout texte en fon** : **Noto Sans** (400, 600, 700, 800).
- Ne jamais écrire du fon en Dela Gothic One : elle n'affiche pas correctement ɖ, ɛ, ɔ, ɣ et les tons combinés.
- Teste l'affichage de « Un nɔ́ ɖu nǔ » et de « ɖ ɛ ɔ ɣ á à ǎ â » sur Chrome Android et Safari iOS.

## Signature visuelle

- **Frise zigzag** jaune sur terre cuite (motif inspiré des tentures d'Abomey), en haut de page, en bas de page et autour du bandeau citation. Faite en CSS, sans image.
- **Boutons en pilule** : fond jaune, texte indigo en Dela Gothic One, `box-shadow: 0 5px 0 #0B0D22`. Les boutons secondaires ont un contour crème de 2 px.
- **Cartes autocollants** inclinées de −6° à +6°, ombre dure, sur fond crème ou jaune.
- **Micro central** rond en terre cuite avec deux anneaux pulsés (jaune et terre cuite).
- **Barres d'ondes sonores** animées en jaune.
- Ces deux animations sont coupées si `prefers-reduced-motion: reduce`.
- **Pastilles de syllabes** : fond indigo, texte crème. Une syllabe incertaine a une bordure pointillée terre cuite, un fond crème et la mention « à confirmer ».
- **Clavier fon** : touches ɖ, ɛ, ɔ, ɣ, á, à, ǎ, â, chacune de 48 px minimum.
- Coins arrondis : 24 px pour les cartes, 999 px pour les pilules.
- Pas de dégradé décoratif, pas d'emoji : icônes SVG au trait.

# Phase 1 — Audit (lecture seule)

Produis `docs/audit_design.md` avec :

1. La stack : langage, framework, moteur de templates, CSS (Tailwind, Bootstrap, SCSS, CSS pur), outil de build, gestion des assets, routes et pages existantes.
2. Le design existant : couleurs, polices, tailles, espacements, rayons, ombres, composants (boutons, cartes, formulaires, navigation, pied de page), logo et images. Pour chacun, indique où il est défini (fichier et ligne).
3. Les pages ou écrans déjà présents qui correspondent aux besoins de FonNLP Xó, et ceux qui manquent.
4. Une **matrice de fusion** en trois colonnes : ce que l'on **garde** du design existant, ce que l'on **adapte** avec la direction Xó, ce que l'on **ajoute**. Justifie chaque ligne en une phrase.
5. Les conflits possibles : couleurs de marque imposées, polices déjà chargées, classes CSS qui se chevauchent, accessibilité.

**Stop : je valide la matrice avant toute modification.**

# Phase 2 — Fondations

1. Ajoute les tokens validés à l'endroit où le projet définit déjà ses styles : variables CSS `--xo-*`, configuration Tailwind ou variables SCSS selon l'audit. Ne renomme pas les tokens existants.
2. Charge Dela Gothic One et Noto Sans de la façon déjà utilisée par le projet, avec `display=swap`.
3. Crée les composants réutilisables, dans le système de composants ou de partials existant : bouton pilule (principal et secondaire), carte, carte autocollant, frise zigzag, micro animé, barres d'ondes, pastille de syllabe, clavier fon, bandeau de retour (réussite ou erreur).
4. Crée une page interne `/styleguide` (ou équivalent) qui montre chaque composant, pour validation.

**Stop : je vérifie le styleguide.**

# Phase 3 — Écrans

Réalise ces écrans avec des données fictives (mock) clairement isolées, prêtes à être remplacées par l'API. **N'invente aucun chiffre** : les compteurs affichent `[X]`, les logos partenaires `[Logo partenaire]`, les noms `[Pseudo]`. Tout texte en fon autre que « Un nɔ́ ɖu nǔ » est marqué « à valider par un linguiste ».

## 3.1 Accueil (mobile d'abord)

1. Frise, en-tête (logo rond « Xó » + « FonNLP Xó / La voix du fon »), navigation (Missions, Comment ça marche, Experts, Communauté) et bouton « JOUER ».
2. Héros : pastille « Benin AI Community · projet FonNLP », titre « TA VOIX FAIT VIVRE LE FON. » (« le fon. » en jaune), texte d'accroche, boutons « COMMENCER UNE MISSION » et « Je suis expert de la langue ». À droite : un disque indigo avec le micro pulsé, les ondes sonores et trois cartes autocollants (« MISSION TONS · Un nɔ́ ɖu nǔ », « +10 pts · Série de 3 jours », « Validé par un expert »).
3. Bandeau crème avec 4 compteurs `[X]` : phrases traduites, heures de voix, contributeurs et contributrices, experts. Mention « chiffres réels au lancement ».
4. « Du jeu au corpus, en trois temps » : Tu joues, L'IA fait le tri, Les experts valident (cette troisième carte est en terre cuite). Mention de consentement en dessous.
5. « Quatre façons de jouer » : Traduire (+15 pts), Dire (+10), Tons (+10), Valider (+5).
6. Bandeau terre cuite encadré de frises, avec la citation « En Afrique, quand un vieillard meurt, c'est une bibliothèque qui brûle. » — Amadou Hampâté Bâ, puis « Avec Xó, chaque voix enregistrée sauve une page de cette bibliothèque. »
7. « Les gardiens des tons » : texte pour les experts, 3 points cochés, bouton « REJOINDRE LA RELECTURE », et une carte de validation inclinée (pastilles un · nɔ1 · ɖu · nu3 ?, boutons Valider et Corriger).
8. « Porté par la Benin AI Community » : logos partenaires, bouton « REJOINDRE LE PROJET ».
9. Pied de page : Confidentialité et consentement, Retirer mes données, Contact.

## 3.2 Jeu — Mission Tons (mobile 390 px, interactif)

- Barre du haut : retour, barre de progression « Mission 3 sur 10 », série de jours, points.
- Étiquette « MISSION TONS · +10 PTS », titre « ÉCOUTE ET CHOISIS LA BONNE ÉCRITURE ».
- Carte d'écoute : bouton lecture jaune de 84 px, ondes, « 5 s · Domaine : vie quotidienne ».
- Trois choix en gros boutons de 64 px. Après un choix : la bonne réponse passe en jaune et le mauvais choix prend une bordure pointillée terre cuite. Bandeau « Bravo ! +10 points pour la langue. » ou « Presque ! La bonne écriture est en jaune. »
- Bouton « MISSION SUIVANTE » et lien « Signaler un problème avec cette phrase ».
- Prévois les mêmes gabarits pour les missions Traduire, Dire (enregistrement au micro avec permission) et Valider.

## 3.3 Espace experts (bureau, s'adapte au mobile)

- En-tête : logo, « Espace experts », nom et rôle de l'expert connecté.
- Colonne gauche : files de relecture (Tons douteux, Enregistrements vocaux, Traductions, Signalements) avec compteurs `[n]`, et « Validées aujourd'hui ».
- Centre, carte crème : lecteur audio avec forme d'onde (zone incertaine en terre cuite), transcription proposée en grand, pastilles syllabes et tons, avis de l'IA (jauge de confiance), clavier fon, boutons VALIDER, Corriger et Rejeter, raccourcis clavier V, C et R.
- Colonne droite : contributeur (pseudo, niveau, fiabilité, consentement), historique de la contribution, guide d'orthographe.

**Stop après chaque écran.**

# Phase 4 — Contrôle qualité

- Affichage correct à 360 px, 768 px et 1440 px ; aucun débordement horizontal.
- Contrastes vérifiés ; vrais `<button>`, `<a>`, `<label>` ; `aria-label` sur les boutons qui n'ont qu'une icône ; focus visible.
- Poids de la page d'accueil sous 500 Ko hors polices ; images optimisées.
- Fon affiché correctement sur Android et iOS.
- Liste des fichiers modifiés et créés, avec un résumé par fichier dans `docs/changelog_design.md`.
