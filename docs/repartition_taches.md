# Répartition des tâches entre deux développeurs

> **Remplacé par `docs/repartition_cahier_des_charges.md`**, qui suit la section 08 du cahier des charges (Dev A : première connexion et profil ; Dev B : missions et enregistrement). Conservé pour mémoire.

Projet : « Le carnet des voix » (FonNLP Xó). Deux branches : `Rabiatou_baic` et `ursus`.
Proposition : **Dev A = serveur et données**, **Dev B = jeu et interface**. À vous de décider qui prend quoi ; ce qui compte, c'est de ne pas travailler sur les mêmes fichiers en même temps.

## Règles pour ne pas se marcher dessus

1. `tts_demo/frontend/src/App.vue` (≈ 2 700 lignes) est le point de conflit n°1. **Seul Dev B le modifie.** Dev A n'y touche que pour brancher une route, et prévient avant.
2. Dev A possède : `assistant_app.py`, `game_db.py`, `game_content.py`, `requirements.txt`, `render.yaml`, `docs/base_de_donnees.md`.
3. Dev B possède : `src/*.vue`, `src/*.css`, `src/*.ts`, `public/`, `docs/changelog_design.md`, `docs/verification_design.md`.
4. Avant de commencer : `git pull`. Après chaque bloc fini : commit + push. Ne jamais pousser un build cassé (`npm run build` doit passer).
5. Un contrat entre les deux : toute nouvelle route API est décrite dans `docs/base_de_donnees.md` (URL, paramètres, réponse) **avant** que Dev B la branche.
6. Règles du projet à respecter : ne supprimer aucun fichier, ne pas inventer de fon présenté comme correct, tutoiement et français simple, texte sur jaune/terre cuite toujours en indigo.

## Dev A — Serveur, base de données, contenu

| # | Tâche | Détail | Prêt quand |
| --- | --- | --- | --- |
| A1 | **Tester PostgreSQL** | Créer la base `xo_game`, renseigner `DATABASE_URL`, lancer le serveur. Jamais testé : seul SQLite l'a été. | Les 441 éléments sont en base, une manche se joue |
| A2 | **Déployer sur Render** | Ajouter une base PostgreSQL gérée, la variable `DATABASE_URL` dans `render.yaml`, vérifier que le disque éphémère ne perd plus rien d'important. | Le jeu en ligne tire ses cartes de la base |
| A3 | **Migrer les anciennes contributions** | Script qui lit `phrase-pairs/*/metadata.json` et remplit la table `contributions` (idempotent). | Même total fichiers / base |
| A4 | **Consentement vérifié côté serveur** | Aujourd'hui le client envoie toujours `consent: true`. Enregistrer le consentement par locuteur (une fois) et le contrôler à chaque envoi. | Envoi refusé sans consentement enregistré |
| A5 | **Suppression des enregistrements** | Route pour retirer les contributions d'un locuteur (promesse faite dans l'interface : « tu peux les retirer à tout moment »). | Fichiers et lignes supprimés |
| A6 | **Statuts des contributions** | Route de lecture : Reçu → Relecture → Expert → Validé / Rejeté (colonne `review_status` déjà prête). | Le profil du joueur affiche le vrai statut |
| A7 | **Espace experts réel** | Authentification (jeton), file de contributions à valider tirée de la base, actions Valider / Corriger / Rejeter. Remplace les données de démonstration. | Un expert valide une vraie contribution |
| A8 | **Contrôle qualité audio** | Rejeter ou signaler les enregistrements trop courts, silencieux ou saturés (durée, volume) avec un message clair. | Message renvoyé au client |
| A9 | **Profil et consentements détaillés** | Stocker côté serveur les 4 consentements et le profil (âge, langue…), aujourd'hui seulement en local. | Données présentes en base |
| A10 | **Contenu : relire et enrichir** | Faire relire `game_content.py` (vocabulaire du quotidien béninois, niveaux). Ajouter les 4 domaines verrouillés (Transport et ville, École et numérique, Cérémonies et culture, Proverbes et contes). | Relecture validée par un locuteur |
| A11 | **Statistiques** | Faire lire `/admin/stats` depuis la base (aujourd'hui lecture des fichiers). | Chiffres identiques |

## Dev B — Jeu et interface

| # | Tâche | Détail | Prêt quand |
| --- | --- | --- | --- |
| B1 | **Tests sur téléphone** | Ouvrir `#/styleguide` sur Chrome Android et Safari iOS : aucun carré, aucun ton décalé dans le fon. Tester un vrai enregistrement au micro (jusqu'ici simulé). | Compte rendu dans `docs/verification_design.md` |
| B2 | **Bouton « Écouter en fon »** | Lecture audio d'une phrase déjà validée, sur les cartes concernées. Dépend de A6/A7 pour savoir ce qui est validé. | Bouton visible seulement si audio validé |
| B3 | **Nouvelles missions** | Tons, Valider (réécouter et noter la contribution d'un autre), Décris l'image. Les puces « bientôt » existent déjà dans l'interface. | Chaque type jouable dans une manche |
| B4 | **Test de placement** | 5 étapes puis écran de résultat pour fixer le niveau de départ. | Niveau initial enregistré |
| B5 | **Messages en cas d'échec d'enregistrement** | « Trop bas », « trop de bruit », micro refusé : messages simples avec marche à suivre. S'appuie sur A8. | Cas testés |
| B6 | **Éclater `App.vue`** | Le découper en composants (Accueil, Jouer, Manche, Profil, Assistant). À faire **en dernier ou en accord avec A**, pour éviter les conflits. | Build identique, comportement inchangé |
| B7 | **Nettoyage** | Supprimer les polices DM Sans et Fraunces (non utilisées), régénérer les icônes PWA depuis `public/icons/logo.svg`. | Poids de l'application réduit |
| B8 | **Mode clair** | Ajouter les contrastes du mode clair à `docs/verification_design.md` ; passer Experts et Styleguide en mode clair si souhaité. | 6 couples ≥ 4,5 : 1 documentés |
| B9 | **Manches : améliorations** | Sons discrets, vibration, confettis à la fin, série de jours, affichage des domaines verrouillés quand le niveau est atteint. Respecter `prefers-reduced-motion`. | Validé sur téléphone |
| B10 | **Clavier fon** | Poursuivre selon `docs/clavier-fon-a-valider.md` (à faire valider par des locuteurs). | Retours des locuteurs intégrés |

## Décisions à prendre ensemble (avant de coder)

- **Nom du produit** : « Le carnet des voix » ou « FonNLP Xó ».
- **Nom du guide** (le personnage) : à proposer puis à faire valider par un locuteur fon.
- **Seuils de niveaux** (Découverte 0, Apprenti 40, Confirmé 120, Maître 300, Gardien 600) : provisoires, inventés.
- **Taille d'une manche** (5 cartes) et points par carte (10 à l'oral, +5 si écrit).

## Ordre conseillé

1. **Semaine 1** : A1, A2 (base en ligne) et B1, B7 (tests téléphone, nettoyage). Aucune dépendance entre eux.
2. **Semaine 2** : A4, A5, A6, A8 (serveur) et B3, B5 (missions, messages).
3. **Semaine 3** : A7, A9, A10 (experts, contenu) et B2, B4, B9.
4. **Fin** : A3, A11, puis B6 (découpage d'`App.vue`) quand plus personne n'a de changement en cours.

## Point de synchronisation

Un quart d'heure en début de journée : qui touche quoi aujourd'hui, quelles routes sont prêtes. Mettre à jour ce tableau (cocher les tâches faites) dans ce fichier lui-même, en le poussant seul dans un commit.
