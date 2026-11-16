# Prototype local d'assistant vocal en fon

Le projet contient trois interfaces :

- `app.py` : démo de synthèse vocale, pour saisir du texte en fon et écouter
  le modèle TTS.
- `assistant_app.py` : assistant texte et vocal, décrit plus bas.
- `assistant_app.py`, route `/game` : chapitre pilote du jeu narratif **Le
  carnet des voix**, où les missions peuvent être jouées sans fournir de
  données. Son interface est construite avec Vue 3, TypeScript et Vite.

## Lancer sur macOS

Depuis le dossier `tts_demo` :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Ouvre ensuite l'adresse locale affichée dans le terminal, généralement
`http://127.0.0.1:7860`. Au premier essai, le modèle et ses poids sont
téléchargés depuis Hugging Face ; une connexion Internet est nécessaire.
La page n'est pas publiée sur Internet et n'active pas le partage Gradio.

Le code utilise le GPU CUDA ou Apple Metal (MPS) s'il est disponible,
sinon le processeur. Le chargement initial peut prendre un moment.

## Modèle et licence

Le modèle est distribué sous licence
[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/).
Cette licence comporte une restriction d'usage commercial. Consulte sa
[fiche Hugging Face](https://huggingface.co/facebook/mms-tts-fon) et
vérifie que la licence convient à ton projet avant toute utilisation.

La qualité de prononciation du fon doit être évaluée par des locuteurs.

## Assistant vocal : discuter ou contribuer

L'interface de l'assistant s'ouvre sur deux parcours :

- **Discuter avec l'IA** ouvre l'assistant vocal existant. Le bouton Accueil
  permet de revenir au choix des parcours.
- **Contribuer à l'entraînement** permet d'écrire une phrase française et sa
  traduction en fon, d'écouter la synthèse vocale actuelle et, si tu le
  souhaites, d'enregistrer une lecture humaine en fon.

Chaque contribution est sauvegardée uniquement après avoir coché son
consentement. Les paires de phrases sont stockées dans
`~/fon-assistant-training-data/phrase-pairs/<identifiant>/`, avec les deux
textes, `fon_synthesized.wav`, un éventuel `fon_human_reading.wav` et
`metadata.json`. L'audio synthétique est identifié comme tel et ne doit pas
servir de cible vocale humaine ; la lecture humaine consentie peut servir à
l'évaluation ou à l'entraînement du TTS. La paire textuelle reste utile même
si aucun audio humain n'est enregistré.

### Développer le front Vue

Le code source du jeu se trouve dans `frontend/`. Pour installer ses
dépendances et créer le bundle servi par FastAPI :

```bash
cd frontend
npm ci
npm run build
cd ..
python assistant_app.py
```

Le jeu est alors disponible à `http://127.0.0.1:7861/game`. Pendant le
développement, démarre FastAPI sur le port 7861 puis, dans `frontend/`, lance
`npm run dev`. Vite sert le front sur `http://127.0.0.1:5173` et transmet
`/training-phrases` à FastAPI. Pour un autre port backend, définis
`VITE_API_PROXY_TARGET`, par exemple
`VITE_API_PROXY_TARGET=http://127.0.0.1:7862 npm run dev`.

Le jeu adopte une mise en page mobile : plein écran sur téléphone et cadre de
téléphone centré sur les écrans plus larges, avec navigation tactile fixe en
bas de l'écran.

### Chapitre jeu : Le carnet des voix

Depuis l'écran d'accueil, choisis **Explorer Le carnet des voix**, ou ouvre
`http://127.0.0.1:7861/game`. L'accueil, le chapitre, l'histoire et les
contributions restent dans cette même application mobile. Le chapitre suit
Afi, messagère fictive d'une radio de quartier, sur un itinéraire illustratif
entre Cotonou, Porto-Novo et Abomey. À chaque étape, une rencontre fictive
amène une situation de parole quotidienne ; le carnet présente six repères
allant des sociétés précoloniales à la République du Bénin actuelle.

L'itinéraire n'est pas une carte routière et les scènes ne prétendent pas
documenter des lieux ou les usages linguistiques d'une ville entière. Les
personnages et rencontres sont imaginaires. Les illustrations vectorielles
originales ne sont ni des photographies ni des portraits de personnes réelles ;
elles ne prétendent pas représenter tous les Béninois. Toute représentation
culturelle plus précise devra être validée par les communautés et locuteurs
concernés.

Le carnet distingue les pouvoirs régionaux d'avant les frontières coloniales,
le royaume du Dahomey centré sur Abomey, l'histoire de la traite à Ouidah, la
conquête et la période coloniales, puis l'indépendance et les changements de nom
du pays. Il cite des sources consultables et signale les incertitudes de
datation. Le royaume du Dahomey n'est pas présenté comme toute l'histoire du
Bénin, et le fon comme une langue vivante parmi les langues du pays.

Les étapes ludiques portent sur des phrases françaises de la vie quotidienne.
Une personne qui connaît le fon peut en proposer une formulation et enregistrer
sa voix avec consentement explicite, ou terminer sans contribuer. Il n'y a pas
de traduction attendue, de score linguistique, de classement ni de publication
des contributions. Les missions ne demandent pas d'interpréter des événements
historiques, des rites ou des contenus sacrés. Toute collecte de chants,
proverbes, récits ou savoirs culturels demanderait un travail distinct avec les
personnes concernées, leur accord et leur validation.

Pour les contributions au jeu, le texte français de la mission, le texte en
fon et le WAV humain sont enregistrés ensemble dans
`~/fon-assistant-training-data/phrase-pairs/<identifiant>/`. Les métadonnées
indiquent `contribution_source: game`, la mission et
`review_status: unreviewed`. Aucune voix synthétique n'est créée ou envoyée
pour ce parcours. Les contributions ne doivent pas être considérées comme
validées ni utilisées pour entraîner un modèle avant une vérification par des
locuteurs et des règles de gouvernance convenues avec la communauté. La
suppression individuelle se fait en supprimant le dossier de l'exemple sur le
serveur ; sur une instance hébergée, le contributeur doit pouvoir contacter
le responsable qui administre les données.

Ce chapitre est un prototype, pas un service public de collecte. Il n'y a pas
encore de compte utilisateur, d'outil de retrait en libre-service, de
validation communautaire, de filtre anti-abus ni de politique formelle de
conservation. Ne l'expose pas sur un serveur public avant de définir ces
mesures et les conditions de réutilisation avec les locuteurs et responsables
communautaires. Les repères historiques sont une introduction sourcée, pas une
histoire exhaustive ni un substitut à l'expertise des historiens béninois.
Le carnet rappelle aussi que des traditions reconnues au Bénin, comme le
Gelede, appartiennent à des communautés précises et ne doivent pas être
présentées comme un héritage fon générique.

#### Sources historiques et principes éditoriaux

- [Encyclopaedia Britannica — Benin: History](https://www.britannica.com/place/Benin/History)
- [Encyclopaedia Britannica — Kingdom of Dahomey](https://www.britannica.com/place/Dahomey-historical-kingdom-Africa)
- [Encyclopaedia Britannica — Ouidah](https://www.britannica.com/place/Ouidah)
- [Encyclopaedia Britannica — Benin](https://www.britannica.com/place/Benin)
- [Encyclopaedia Britannica — Fon people](https://www.britannica.com/topic/Fon-people)
- [UNESCO — Palais royaux d'Abomey](https://whc.unesco.org/en/list/323/)
- [UNESCO — Principes éthiques pour le patrimoine culturel immatériel](https://ich.unesco.org/en/ethics-and-intangible-cultural-heritage-00866)
- [UNESCO — Patrimoine oral du Gelede](https://ich.unesco.org/en/RL/oral-heritage-of-gelede-00002)

Les sources encyclopédiques fournissent des repères généraux, pas une
validation par la communauté. Avant d'ajouter des personnages historiques, des
expressions fon, des récits oraux, de la musique ou des pratiques culturelles,
faire relire le contenu par des locuteurs fon et des historiens béninois et
définir la rémunération, l'attribution, le consentement et le droit de retrait.

## Assistant : entrée texte ou audio, réponse audio en fon

L'assistant sépare les étapes suivantes :

1. En option, transcription locale d'un enregistrement en français ou fon.
   L'utilisateur vérifie et peut corriger le texte reconnu.
2. Pour un message en fon, traduction Fon vers français. Un message français
   est utilisé directement.
3. Envoi du texte français et des derniers échanges à un LLM via OpenRouter.
4. Traduction de la réponse française vers le fon.
5. Synthèse de la réponse en fon en audio par le modèle TTS local.

La réponse est toujours destinée à être en fon. Le LLM produit d'abord le
contenu en français ; l'étape de traduction est séparée. Le choix du modèle
OpenRouter et la qualité de la traduction peuvent affecter le résultat.

### Entrée vocale

Dans l'interface, sélectionne Français ou Fon puis clique **Parler** et autorise
l'accès au micro. L'enregistrement s'arrête et s'envoie automatiquement après
1,5 seconde de silence détecté, avec une limite de sécurité de 30 secondes.
Tu peux aussi recliquer sur le même bouton pour envoyer sans attendre. L'audio
est transcrit localement ; la carte de droite affiche la transcription de ta
parole et la réponse de l'assistant en fon. Les deux textes sont modifiables.
La réponse est ensuite prononcée automatiquement en fon.
Un personnage-guide masculin salue au repos et pendant l'enregistrement, puis
anime sa bouche pendant la lecture de la réponse.
Clique à nouveau sur **Parler** après la réponse pour continuer la conversation.
Si le navigateur bloque la lecture automatique, un bouton permet de lancer la
réponse manuellement.

La barre affiche le temps d'enregistrement jusqu'à 30 secondes, puis s'anime
pendant la transcription. Le message indique les étapes (chargement du modèle,
chargement de l'adaptateur de langue, analyse et finalisation) avec le temps
écoulé. Les durées de chargement, d'analyse et de finalisation sont affichées
séparément. Sur Apple MPS, le calcul est synchronisé avant l'étape de
finalisation afin que son attente ne soit pas attribuée à tort au décodage du
texte. Il ne s'agit pas d'un pourcentage précis du calcul.
En cas d'erreur, le message s'affiche en rouge sous la barre ; les détails
inattendus restent également dans le terminal du serveur.

L'enregistrement au micro est capturé comme WAV PCM dans le navigateur, puis
transmis au serveur local pour la transcription. L'interface limite l'audio à
30 secondes. L'audio n'est pas envoyé à OpenRouter ; seul le texte est utilisé
pour la conversation. Par défaut, les audios ne sont pas conservés.

Après une réponse, tu peux corriger la transcription reconnue et la réponse en
fon. Pour enregistrer une contribution, coche le consentement de cette
contribution puis clique **Enregistrer ma contribution**. Sans cette action,
aucun fichier d'exemple n'est écrit. Les fichiers sont stockés hors du projet,
dans `~/fon-assistant-training-data/<identifiant>/` : `input_audio.wav` est
l'audio original de la personne, `assistant_audio.wav` est la réponse régénérée
avec le texte corrigé, et `metadata.json` contient les transcriptions d'origine
et corrigées, les modèles utilisés et le type de chaque audio. Tu peux supprimer
une contribution en supprimant son dossier local.

L'audio original associé à la transcription corrigée est destiné à améliorer
et évaluer l'ASR. L'audio de réponse est généré par le TTS actuel ; il est
conservé pour contrôler la paire texte/audio, mais ne constitue pas un
enregistrement humain de référence et ne doit pas servir de cible d'adaptation
TTS. Pour entraîner une voix TTS, il faudra collecter séparément des
enregistrements humains autorisés lisant les textes en fon. Les contributions
de voix sont des données personnelles : recueille le consentement des personnes
et ne partage pas les dossiers sans autorisation.

La reconnaissance utilise
[`facebook/mms-1b-all`](https://huggingface.co/facebook/mms-1b-all), qui prend
en charge les codes de langue `fra` et `fon`. Ce modèle compte un milliard de
paramètres ; son téléchargement initial est volumineux et nécessite Internet.
Il reste en mémoire tant que le serveur fonctionne, mais un redémarrage du
serveur nécessite de le recharger. Chaque enregistrement est limité
à 30 secondes. Une couverture de langue ne garantit pas une bonne précision :
la reconnaissance du fon doit être évaluée et corrigée avec des locuteurs.
Le modèle est sous licence
[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/), avec une
restriction d'usage commercial.

Pour la configuration locale la plus simple, copie `.env.example` vers `.env`,
ouvre `.env`, puis remplace la valeur d'exemple par ta nouvelle clé OpenRouter :

```bash
cp .env.example .env
# Edite ensuite .env et remplace replace_with_your_new_key.
python assistant_app.py
```

Le fichier `.env` est chargé automatiquement et exclu de Git par `.gitignore`.
Ne partage pas ce fichier et ne colle pas son contenu dans une conversation.
Les variables déjà définies dans l'environnement ont priorité sur `.env`.
Si tu préfères ne pas créer ce fichier, tu peux aussi définir
`OPENROUTER_API_KEY` dans le terminal avant de lancer l'application.

L'interface de l'assistant s'ouvre sur `http://127.0.0.1:7861`, afin de ne pas
remplacer la démo TTS existante sur le port 7860.

Le prototype détecte automatiquement le modèle adapté dans
`models/inference_model-speaker4-20261029` lorsqu'il contient un `config.json`.
Sinon, il utilise `facebook/mms-tts-fon`. Pour choisir un autre dossier, ajoute
`FON_TTS_MODEL` à ton `.env` ou définis la variable dans le terminal :

```bash
export FON_TTS_MODEL="/chemin/vers/le/dossier/inference_model"
python assistant_app.py
```

Les textes français ou fon, les traductions et l'historique de conversation
sont transmis à OpenRouter pour générer la réponse. Ne saisis pas de données
sensibles. La clé reste dans l'environnement local et n'est pas affichée dans
l'interface. L'audio entrant est transcrit localement et n'est pas transmis.

Si une traduction revient vide, le message d'erreur indique maintenant
l'étape concernée, le motif de fin et le modèle renvoyé par OpenRouter, sans
afficher la clé ni le texte de la requête. Si l'erreur se produit pendant la
traduction vers le fon, essaie un modèle OpenRouter différent, sélectionné
dans ton compte et capable de produire du texte dans cette langue, puis
remplace `OPENROUTER_MODEL=openrouter/auto` dans ton `.env`. La limite de
génération par requête est de 2 048 tokens afin de réduire le risque que les
tokens de raisonnement du modèle consomment tout le budget avant le texte de
traduction ; un modèle choisi explicitement peut rester nécessaire.

Les erreurs réseau et OpenRouter affichent des conseils adaptés (clé ou accès,
crédits, limite de requêtes, délai d'attente ou indisponibilité temporaire).
Les logs du terminal indiquent le code HTTP et les codes techniques du
fournisseur, sans enregistrer la clé ni le contenu des messages.

### Déployer une démo de l'assistant sur Render

Le fichier `render.yaml` prépare un service Render gratuit pour des essais.
Le dossier `tts_demo` doit être la racine d'un dépôt GitHub connecté à Render ;
ce dossier de travail n'est pas lui-même un dépôt Git. Pour éviter d'envoyer les
corpus, poids de modèles et données d'expérimentation, crée un dépôt séparé avec
uniquement le contenu de `tts_demo`. `.env`, `models/` et `experiments/` sont
exclus de Git par `.gitignore`.

Dans Render, crée un Blueprint depuis ce dépôt, puis renseigne
`OPENROUTER_API_KEY` dans les variables d'environnement du service. Ne mets pas
la clé dans le dépôt. Render fournit l'URL HTTPS et le port d'écoute.

**Limite importante de l'offre gratuite :** l'instance Render Free a 512 Mo de
RAM et son système de fichiers est éphémère. Le modèle ASR MMS 1B, puis le modèle
TTS, nécessitent beaucoup plus de mémoire ; la page peut s'ouvrir mais la
transcription risque d'échouer par manque de mémoire. Les modèles devront aussi
être téléchargés à nouveau après un redémarrage ou une mise en veille. Cette
configuration gratuite sert uniquement à vérifier le déploiement web, pas à
garantir un essai vocal fonctionnel. Pour tester l'audio, choisis une instance
avec davantage de mémoire dans Render ; cela peut entraîner des frais.

L'URL Render est publique. Partage-la uniquement avec des testeurs de confiance :
les requêtes peuvent utiliser la clé OpenRouter du service et entraîner des
coûts côté fournisseur. Les modèles vocaux actuels sont sous licence
CC BY-NC 4.0 et ne doivent pas être utilisés commercialement.

Vérifier le pipeline texte sans lancer l'interface ni appeler OpenRouter :

```bash
python -m unittest discover -s tests -v
```

## Préparer un essai d'adaptation sur une voix autorisée

L'outil ci-dessous valide les fichiers d'un seul locuteur adulte, contrôle les
WAV et les transcriptions avec le tokenizer MMS, puis crée une séparation
entraînement/validation par phrase afin que les prises répétées d'une même
phrase ne se retrouvent pas des deux côtés.

Après avoir confirmé l'autorisation explicite du locuteur pour l'entraînement
TTS et la génération de nouvelles phrases avec sa voix :

```bash
python prepare_speaker_dataset.py --speaker-id 4 --consent-confirmed
```

Le résultat est écrit dans `experiments/speaker_4/` : `train.csv`,
`validation.csv` et `quality_report.json`. Les fichiers audio sources ne sont
pas copiés ni modifiés. Le script exclut les mineurs, refuse les paires
manquantes ou mal formées et échoue plutôt que de normaliser automatiquement
des caractères de la langue.

Une fois un modèle adapté exporté, on peut synthétiser les mêmes phrases
réservées et comparer le modèle original, le modèle adapté et les véritables
enregistrements de validation :

```bash
python compare_models.py \
  --validation-csv experiments/speaker_4/validation.csv \
  --output-dir experiments/speaker_4/comparison

python compare_models.py \
  --validation-csv experiments/speaker_4/validation.csv \
  --adapted-model chemin/vers/modele-adapte \
  --output-dir experiments/speaker_4/comparison
```

La première commande crée le jeu de phrases et les audios de référence du
modèle original. La seconde réutilise exactement les mêmes phrases et ajoute
les audios du modèle adapté.

L'inférence est prise en charge par Transformers, mais son implémentation VITS
actuelle ne prend pas en charge l'entraînement (`Training of VITS is not
supported yet`). L'adaptation requiert donc un pipeline d'entraînement VITS
distinct, ainsi qu'une configuration matérielle suffisante. Ne pas lancer un
entraînement avant d'avoir choisi et validé ce pipeline.

## Essai pilote sur Google Colab

Le paquet portable et le notebook permettent de faire un essai limité avec un
GPU Colab. Le paquet ne contient que les paires train/validation du locuteur 4
et huit audios de référence du modèle MMS original. Il omet les autres
locuteurs et les métadonnées personnelles.

Après vérification de l'autorisation du locuteur pour l'entraînement et la
génération avec sa voix, crée le paquet depuis `tts_demo` :

```bash
python package_speaker_dataset.py
```

Le résultat est écrit dans
`experiments/speaker_4/speaker_4_colab_bundle.zip`. Téléverse ce fichier dans
`Mon Drive/fon_tts/`, ouvre
[`colab_fon_tts_pilot.ipynb`](colab_fon_tts_pilot.ipynb) dans Google Colab et
choisis un runtime GPU. Le notebook vérifie les données, utilise le pipeline
communautaire VITS/MMS à un commit précis, puis limite l'essai à 64 exemples
d'entraînement et 16 de validation. Le modèle adapté et les comparaisons sont
sauvegardés dans Drive; rien n'est envoyé sur le Hub.

Le notebook compile automatiquement l'extension Cython `monotonic_align`
requise par ce pipeline et vérifie qu'elle est importable avant de lancer
l'entraînement. La configuration du chargement des données locales est
idempotente : si la cellule est relancée dans le même runtime, elle reconnaît
le remplacement déjà effectué au lieu de s'arrêter.

Le notebook utilise `datasets==3.6.0` pour éviter l'incompatibilité entre
NumPy 2 et `datasets==2.17.1` rencontrée pendant le prétraitement des données.
Après une mise à jour des dépendances, redémarre le runtime Colab et relance
les cellules depuis le début afin que le noyau recharge la nouvelle version.
La cellule de configuration du fine-tuner adapte également la lecture des
graphiques à Matplotlib récent (`buffer_rgba` au lieu de `tostring_rgb`) et
peut être relancée sans appliquer le changement deux fois. Chaque tentative
d'entraînement écrit dans un nouveau dossier temporaire, pour ne pas entrer en
collision avec les sorties partielles d'un essai échoué.

Ce pilote vérifie le fonctionnement technique, pas l'amélioration de qualité.
Les audios et le checkpoint contiennent une voix identifiable : garde-les
privés, respecte le périmètre du consentement confirmé et vérifie la licence
CC BY-NC 4.0 du modèle MMS avant toute utilisation ou diffusion.
