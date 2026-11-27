# Base de données du jeu

## Choix : PostgreSQL (SQLite en secours local)

- Le déploiement (`render.yaml`, offre gratuite) a un disque **éphémère** : les contributions écrites en fichiers peuvent disparaître. Une base PostgreSQL gérée règle cela.
- Le code passe par SQLAlchemy : MySQL (`mysql+pymysql://…`) fonctionne aussi, il suffit de changer `DATABASE_URL`.
- Sans `DATABASE_URL`, le serveur crée un fichier SQLite `xo_game.db` dans le dossier des données : le jeu marche sans rien installer.

```
DATABASE_URL=postgresql://utilisateur:motdepasse@localhost:5432/xo_game
```

La base `xo_game` doit exister (`CREATE DATABASE xo_game;`). Les tables et le contenu sont créés au démarrage, sans doublon si on relance.

## Tables

| Table | Rôle |
| --- | --- |
| `domains` | 7 domaines (id, libellé, mode histoire/phrases, histoire d'introduction) |
| `items` | mots, phrases et paragraphes **en français** à dire / traduire (441 éléments : 40 mots, 20 phrases, 3 paragraphes par domaine, plus les éléments d'origine) |
| `contributions` | copie des métadonnées de chaque contribution (le son reste en fichiers) ; liée à l'élément joué |

Les identifiants d'éléments sont stables (même texte = même id), donc ajouter du contenu ne casse rien.

## Contenu : `tts_demo/game_content.py`

Une ligne = un élément. Pour ajouter des mots : ajouter des lignes puis relancer le serveur. **Aucune traduction fon n'y figure** : elle vient des contributeurs puis des experts (règle du projet : ne pas inventer de fon).
Le niveau découle du type : mot = facile, phrase = moyen, paragraphe = difficile.

## Fonctionnement du jeu

- `GET /game/round?domain=&level=&size=5&exclude=ids` : tire 5 cartes au hasard sans répéter celles déjà vues. `domain` vide = tous domaines mélangés.
- La difficulté monte avec le niveau du joueur (niveau 1 : 5 mots ; niveau 5 : phrases + 1 paragraphe). Dans une manche, les cartes vont du plus court au plus long.
- `GET /game/domains` : totaux par domaine (barres de progression).
- Le joueur ne choisit plus : il lance une partie (mélangée) ou un domaine, les cartes défilent une à une, avec série, encouragements et bilan.
- Hors ligne ou serveur sans base : le jeu retombe sur les éléments embarqués dans l'application.

## À faire / limites

- **Non testé sur PostgreSQL** : essayé avec SQLite uniquement (aucun identifiant PostgreSQL à disposition). À tester par l'équipe avec la vraie `DATABASE_URL`.
- Le contenu est du français rédigé à la main pour le jeu ; à faire relire (vocabulaire du quotidien béninois, niveaux).
- Les statuts de validation par les experts ne sont pas encore reliés à la table `contributions` (colonne `review_status` prête).
