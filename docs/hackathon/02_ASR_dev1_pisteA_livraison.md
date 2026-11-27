# Contexte

Projet : BENIN Tonal ASR Challenge pour le fongbé (Zindi). Le dépôt `asr-fongbe/` existe déjà (prompt 01) : normalisation, score local identique à Zindi, jeu de validation, script d'inférence, `experiments.csv`. Lis `README.md`, `reports/00_audit_donnees.md` et `experiments.csv` avant toute chose.

Rappel des limites à l'inférence : 1 thread CPU, facteur temps réel ≤ 1 (cible interne 0,6), RAM ≤ 2 Go (cible 1,5), poids ≤ 1 000 Mo (cible 700), hors ligne. Seules les données fournies par le challenge sont autorisées ; les modèles pré-entraînés ouverts le sont aussi. Graines fixées. Données confidentielles : rien de public.

Je suis le **développeur 1**. Mes responsabilités : la **piste A** (modèle compact) et **toute la livraison** (soumissions, frugalité, Docker, dossier de revue de code). Le développeur 2 travaille en parallèle sur la piste B (MMS-300M) et le décodage avec modèle de langue.

Travaille en **audit d'abord**, par phases. À la fin de chaque phase, arrête-toi, résume, signale les ambiguïtés et attends ma validation.

# Phase A1 — Choix de la boîte à outils (avant le 25 novembre)

Compare brièvement, pour notre cas (CTC, entraînement sur GPU Kaggle T4 ou P100, export ONNX, inférence 1 thread) :

- **NVIDIA NeMo, Conformer-CTC small** : environ 13 M de paramètres ; initialisation possible depuis un modèle anglais ouvert, avec un nouveau tokenizer ;
- **k2 / icefall, Zipformer-CTC** : inférence très rapide avec sherpa-onnx, mais installation plus lourde.

Recommande-en une, en tenant compte de la facilité d'installation sur Kaggle et de l'export vers sherpa-onnx ou ONNX Runtime. Par défaut, je préfère NeMo, sauf blocage.

**Stop.**

# Phase A2 — Notebook d'entraînement piste A

Crée `notebooks/pisteA_train.ipynb`, exécutable sur Kaggle (GPU, sessions limitées) :

1. Chargement des données depuis un jeu de données Kaggle **privé**, à partir des listes de `data/splits/`.
2. Cibles : utilise l'unité de sortie décidée en phase 0. Par défaut, entraîne **deux variantes** :
   - lettres avec accents (Unicode normalisé) ;
   - forme syllabée avec chiffres de ton comme symboles à part (« un nɔ 1 ɖu nu 3 »).
3. Augmentations sans données externes : variation de vitesse (0,9 / 1,0 / 1,1), SpecAugment, bruit gaussien et réverbération synthétiques.
4. Stratégie de données : d'abord tout le corpus, puis un affinage final sur les seuls enregistrements validés ; poids réduit pour la Bible et pour les tons incertains. Ces choix sont paramétrables dans le YAML.
5. Points de sauvegarde réguliers, avec reprise possible après coupure de session Kaggle.
6. Évaluation à chaque époque avec `src/metrics/score.py` sur le jeu de validation ; on garde le meilleur.
7. Commence par un essai court (environ 20 h de données, 1 h de GPU) pour valider la chaîne avant l'entraînement complet.

**Stop après l'essai court : montre le score de validation et la courbe.**

# Phase A3 — Export et frugalité

1. Exporte le meilleur modèle en ONNX, puis quantifie-le en int8 (quantification dynamique d'ONNX Runtime).
2. Branche-le dans `src/infer/predict.py` (décodage glouton CTC), avec découpage des longs audios en morceaux pour limiter la mémoire.
3. Mesure sur 1 thread : score de validation en fp32 et en int8, taille, facteur temps réel, RAM maximale. Lance aussi `measure_frugality.py`.
4. Écris tout dans `experiments.csv` et `reports/pisteA.md`.

**Stop.**

# Phase A4 — Infrastructure de livraison (pour les deux pistes)

1. `src/infer/predict.py` doit accepter n'importe quel modèle ONNX CTC et un décodeur optionnel (glouton, ou faisceau avec KenLM fourni par le développeur 2), via la config.
2. `scripts/make_submission.sh` : inférence → syllabification → contrôle du format (colonnes, nombre de lignes, identifiants, aucune ligne vide) → CSV horodaté dans `submissions/`.
3. `Dockerfile` CPU minimal qui reproduit l'inférence hors ligne, avec 1 thread forcé, et une commande unique documentée dans le README.
4. `docs/revue_de_code/` : liste des ressources externes avec leurs licences, instructions de reproduction de l'entraînement et de l'inférence, sortie de `measure_frugality.py`, emplacement de l'encodeur isolé (exporté à part, comme l'exige la revue de code).
5. Test sur une machine propre (conteneur neuf) : le score doit être identique à celui affiché dans `experiments.csv`.

**Stop.**

# Règles

- Une soumission Zindi ne part que si le score local s'est amélioré et que les mesures de frugalité passent les cibles internes.
- Chaque soumission est notée dans `experiments.csv` avec son score public.
- Ne pousse jamais de données ou de poids sur un dépôt public.
- Date limite interne de la soumission finale : 13 décembre, 18 h.
