# Répartition à deux — conforme au cahier des charges

Source : « Xó Jeu — Révision de l'application » (25 novembre 2026), section 08 « Priorités et répartition à deux », complétée par les sections 03 à 07 et 09.
Ce document **remplace** `docs/repartition_taches.md` (conservé, mais ses développeurs A et B y étaient définis autrement).

## Les deux rôles (définis par le cahier)

| | Développeur A | Développeur B |
| --- | --- | --- |
| Domaine | **Première connexion et profil** (consentement, test, niveaux, domaines, assistant) + **espace experts** | **Missions et enregistrement** (textes, images, écrit, clavier) + **contrôle automatique et base de données** |
| Fichiers principaux | écrans d'onboarding / profil / assistant / experts (`Experts.vue`, parties d'`App.vue`) | écrans de mission et d'enregistrement, `FonKeyboard.vue`, `rounds.ts`, `assistant_app.py`, `game_db.py`, `game_content.py` |

Qui est A, qui est B : à décider entre vous (le cahier ne nomme personne). Règle commune : `App.vue` est un fichier unique de ~2 800 lignes ; A modifie les blocs onboarding / profil / assistant, B les blocs mission / enregistrement, et chacun fait `git pull` avant de commencer et pousse après chaque bloc fini.

## Avancement réel par chantier (état au 27 novembre 2026)

Légende : **fait** = marche et testé en navigateur ; **partiel** = existe mais incomplet ; **à faire**.

| Prio | Chantier | Dev A | Dev B | État |
| --- | --- | --- | --- | --- |
| 1 | Circuit de validation | Espace experts, trace des décisions, retrait du consentement | Contrôle automatique, statuts en base, export du corpus validé seulement | **À faire** : `Experts.vue` n'a que des données de démo, sans connexion ; la table `contributions` a une colonne `review_status` mais il n'y a ni zone d'attente séparée, ni contrôle automatique, ni export |
| 1 | Consentement unique | Écran, versions, enregistrement en base, page profil | Retirer la case du flux d'enregistrement | **Partiel** : écran unique à 4 cases, vérification d'âge et page profil faits (stockés **en local seulement**) ; case par enregistrement **supprimée** (fait, B) ; manque version du texte, enregistrement en base, retrait et suppression des enregistrements côté serveur |
| 1 | Écrit facultatif + file « À transcrire » | — | Bouton « Passer », statuts d'écrit, mission « Écris ce que tu entends » | **Partiel** : écrit facultatif et « Passer » faits ; le mode (audio seul / audio + texte) est enregistré ; manque les 4 statuts d'écrit et la mission « Écris ce que tu entends » |
| 1 | Clavier fon | — | Composant, appui long pour les tons, NFC | **Fait** (branche `ursus`) ; reste la validation par un linguiste |
| 2 | Test de placement + choix du mode | Parcours, calcul du résultat, choix du mode | Fournir les contenus du test (audio, phrases) | **À faire** (le choix du mode existe, sans test) |
| 2 | Niveaux de difficulté | Règles de passage, affichage de la progression | Étiqueter les phrases par niveau, sélection des missions | **Partiel** : phrases étiquetées (mot / phrase / paragraphe → facile / moyen / difficile) et manches selon le niveau (fait, B) ; niveaux du joueur et barre de progression faits mais avec des règles différentes du cahier (voir « Écarts ») |
| 2 | Domaines revus | Choix des domaines préférés | Icônes, progression par domaine, tableau admin | **Partiel** : choix, icônes et progression faits ; tableau admin (heures d'audio, phrases par domaine) à faire |
| 3 | Images + « Décris l'image » | — | Banque d'images, nouvelle mission | **À faire** (puce « bientôt » dans l'interface ; 3 images de domaine seulement) |
| 3 | Assistant repositionné | Textes et scénarios | Contrôle audio qui alimente ses messages | **Partiel** : nouveau design de l'assistant ; rôle « guide, pas traducteur » à vérifier dans les textes ; aucun contrôle audio |
| 3 | Design Xó | Écrans de première connexion et profil | Écrans de missions et d'enregistrement | **Fait** (accueil, onboarding, jeu, profil, experts, mode clair / sombre) |

## Tâches par développeur, dans l'ordre

### Développeur A — première connexion, profil, experts

1. **Consentement versionné en base** (prio 1) : table `consents` (locuteur, version du texte, date et heure, cases acceptées) ; redemander une seule fois si le texte change ; l'écran existe déjà (`App.vue`, stage « onboarding »).
2. **Retrait du consentement et suppression des enregistrements** (prio 1) : routes serveur ; « le retrait l'emporte » : les contributions sortent du corpus et des exports, même validées. Le bouton existe côté profil, il ne supprime aujourd'hui que le stockage local.
3. **Espace experts réel** (prio 1) : authentification par jeton, file lue depuis la base, actions Valider / Corriger / Rejeter, **trace de chaque décision** (qui, quand, pourquoi), correction gardée à côté de la version d'origine. Remplace les données de démo.
4. **Test de placement** (prio 2) : 5 étapes du cahier (Écoute, Voix, Lecture, Écrit, Tons) ; règle : étapes 3 à 5 réussies → « Voix + écrit », sinon « Voix seule » ; refaisable après quelques jours.
5. **Règles de passage de niveau** (prio 2) : voir « Écarts ».
6. **Profil** : tranche d'âge, région, variante de fon (facultatifs) enregistrés côté serveur, jamais regroupés avec le pseudo dans le corpus.
7. **Assistant repositionné** (prio 3) : textes et scénarios ; il ne donne jamais la traduction fon d'une mission en cours ; apparitions courtes ; nom fon du personnage à faire valider par un locuteur.
8. **Domaines préférés** : déjà fait ; relier au tableau admin (tâche B 9).

### Développeur B — missions, enregistrement, données

1. **Zone d'attente séparée du corpus validé** (prio 1) : aujourd'hui une seule table `contributions`. Créer deux espaces distincts (table et dossier de fichiers) ; les scripts d'export ne lisent que « Validé ». Statuts du cahier : Reçu, Rejeté automatiquement, En relecture, À valider par un expert, Rejeté par l'expert, Validé.
2. **Contrôle automatique** (prio 1) : durée, silence, volume, saturation pour l'audio ; caractères autorisés et longueur pour le texte. Rejet immédiat avec message clair au joueur (« trop bas », « trop de bruit »). L'IA trie, elle ne valide jamais.
3. **Trace de chaque donnée** : qui, quand, mission, domaine, niveau, statut de validation, version du consentement (voir tâche A 1).
4. **PostgreSQL** : tester avec une vraie `DATABASE_URL` (testé avec SQLite seulement) et déployer (Render a un disque éphémère). Détails : `docs/base_de_donnees.md`.
5. **Écrit facultatif** (prio 1) : les 4 statuts d'écrit (sans texte, écrit par l'auteur, écrit par un autre joueur, validé par un expert) ; file « À transcrire » ; mission « Écris ce que tu entends » pour le mode « Voix + écrit » et les experts. En mode « Voix seule », la proposition d'écrire ne s'affiche pas.
6. **Clavier fon** (prio 1) : fait ; faire valider la liste des lettres, la notation des tons et des voyelles nasales par un linguiste (`docs/clavier-fon-a-valider.md`).
7. **Contenus du test de placement** (prio 2) : audio et phrases pour A 4.
8. **Étiquetage des phrases** (prio 2) : fait par type ; à affiner avec les 3 critères du cahier (longueur, rareté des mots, mots dont le sens change selon le ton). Banque relue par un expert avant d'entrer dans le jeu.
9. **Tableau admin** (prio 2) : heures d'audio et phrases par domaine ; missions bonus pour les domaines en retard.
10. **Images et « Décris l'image »** (prio 3) : banque d'images (photos propres ou illustrations d'artistes béninois, licence vérifiée, pas de visage reconnaissable) et nouvelle mission.
11. **Contrôle audio qui alimente l'assistant** (prio 3) : messages « trop bas », « trop de bruit », « coupé ».

## Écarts entre le cahier des charges et l'application actuelle (à trancher avant de coder)

Je les signale sans les trancher.

1. **Domaines.** Le cahier garde **11 domaines**, dont 6 ouverts au lancement : Salutations, Famille, Nombres et argent, Marché, Santé, Agriculture. L'application a **7 domaines** : Santé, Éducation, Religion et traditions, Agriculture, Commerce et marché, Administration, Métiers (441 éléments), et 4 verrouillés qui ne sont pas ceux du cahier. Manquent : Salutations, Famille, Nombres et argent, Transport (présent en verrouillé), Cérémonies, Proverbes. Ajouter un domaine = ajouter des lignes dans `game_content.py`.
2. **Niveaux.** Cahier : passage par **contributions validées** (50, 150 avec 80 % validées, 400 avec 85 %, puis sélection, puis nomination). Application : passage par **points d'effort** (40, 120, 300, 600), seuils provisoires de ma part. Comme les points complets ne sont donnés qu'après validation (cahier), le niveau doit dépendre du circuit de validation : à reprendre une fois la tâche B 1 faite.
3. **Points.** Le cahier : points d'effort à la réception, points complets + bonus après validation. L'application donne 10 points (+5 si écrit) dès l'envoi, sans distinguer.
4. **Longueur des textes.** Le cahier demande des phrases de 3 à 12 mots avec un contexte (qui parle, à qui, où) ; les paragraphes de la banque actuelle sont plus longs et la plupart des cartes n'ont pas de contexte.
5. **Manche et nom du produit.** Manche de 5 cartes, nom « Le carnet des voix » : choix de ma part, non fixés par le cahier.
6. **Âge.** Le cahier : 18 ans et plus au lancement. L'application demande une case « j'ai 18 ans ou plus » (autodéclaration, sans vérification réelle).
7. **Consentements.** Le cahier : 3 consentements séparés (voix et textes obligatoire, profil facultatif, publication en jeu de données ouvert CC BY 4.0). L'application a 4 cases (âge + 3) ; le texte doit annoncer clairement la publication en licence ouverte et être relu par une personne qui connaît le Code du numérique et l'APDP.

## À valider par des personnes extérieures

- Un **linguiste référent** : alphabet, tons, voyelles nasales, banque de phrases (tout est « à valider »).
- Un **juriste** (Code du numérique, APDP) : texte de consentement.
- Des **locuteurs fon** : nom du guide, relecture des textes de l'interface, voix enregistrée des phrases clés.

## Point de synchronisation

Un quart d'heure en début de journée : qui touche quels blocs de `App.vue`, quelles routes sont prêtes (chaque route est décrite dans `docs/base_de_donnees.md` avant d'être branchée). Cocher l'état dans ce fichier, en le poussant seul.
