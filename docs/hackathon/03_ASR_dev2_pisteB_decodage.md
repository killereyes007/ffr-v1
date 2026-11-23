# Contexte

Projet : BENIN Tonal ASR Challenge pour le fongbé (Zindi). Le dépôt `asr-fongbe/` existe déjà (prompt 01) : normalisation, score local identique à Zindi, jeu de validation, script d'inférence, `experiments.csv`. Lis `README.md`, `reports/00_audit_donnees.md` et `experiments.csv` avant toute chose.

Rappel des limites à l'inférence : 1 thread CPU, facteur temps réel ≤ 1 (cible interne 0,6), RAM ≤ 2 Go (cible 1,5), poids ≤ 1 000 Mo **modèle de langue compris** (cible 700), hors ligne. Seules les données fournies par le challenge sont autorisées ; les modèles pré-entraînés ouverts le sont aussi. Graines fixées. Données confidentielles : rien de public.

Je suis le **développeur 2**. Mes responsabilités : la **piste B** (modèle pré-entraîné affiné), les **vocabulaires de sortie** et le **décodage avec modèle de langue**. Le développeur 1 gère la piste A (Conformer-CTC compact) et l'infrastructure de livraison ; mon décodeur doit se brancher dans son `src/infer/predict.py`.

Travaille en **audit d'abord**, par phases. À la fin de chaque phase, arrête-toi, résume, signale les ambiguïtés et attends ma validation.

# Phase B1 — Test de vitesse avant tout entraînement (au plus tard le 26 novembre)

Avant d'investir des heures de GPU, vérifie que la piste B peut tenir les limites :

1. Charge `facebook/mms-300m` (et `facebook/wav2vec2-xls-r-300m` pour comparer) avec une tête CTC non entraînée.
2. Exporte en ONNX, quantifie en int8 (quantification dynamique d'ONNX Runtime).
3. Mesure sur **1 thread**, sur 10 minutes d'audio réel : facteur temps réel, RAM maximale, taille sur disque.
4. Si le facteur temps réel dépasse 0,6, teste le retrait de couches de l'encodeur (garder 12, 16 ou 18 couches sur 24) et donne le compromis.

Rapport dans `reports/pisteB_vitesse.md`.

**Stop : on décide ensemble si la piste B continue.**

# Phase B2 — Notebook d'affinage CTC

Crée `notebooks/pisteB_finetune.ipynb`, exécutable sur Kaggle (GPU T4 ou P100, fp16, sessions limitées) :

1. `Wav2Vec2ForCTC` depuis le modèle retenu en B1, avec le nombre de couches retenu.
2. Trois vocabulaires de sortie à comparer, chacun dans sa config YAML :
   - **V1** : lettres avec accents (Unicode normalisé) ;
   - **V2** : lettres sans accents + chiffres de ton comme symboles séparés, après chaque syllabe (forme syllabée) ;
   - **V3** : comme V2, avec une deuxième tête de sortie dédiée aux tons (expérimental, seulement si V1 et V2 sont terminés).
3. Encodeur de caractéristiques gelé, taux d'apprentissage avec échauffement, points de sauvegarde réguliers et reprise après coupure de session.
4. Commence par un essai court (environ 20 h de données) pour V1 et V2. Ensuite seulement, l'entraînement complet du meilleur vocabulaire.
5. Stratégie de données identique à la piste A : tout le corpus d'abord, affinage final sur les seuls enregistrements validés ; poids réduit pour la Bible et pour les tons incertains (paramétrable).
6. Évaluation avec `src/metrics/score.py` sur le jeu de validation ; on garde le meilleur point.

**Stop après les essais courts : compare V1 et V2 dans `experiments.csv`.**

# Phase B3 — Modèle de langue et décodage

1. Construis un modèle de langue n-gramme (KenLM, ordre 3 à 5) **uniquement** à partir des transcriptions d'entraînement, jamais à partir du jeu de validation. Il doit utiliser les mêmes unités que la sortie du modèle (syllabes et tons si V2).
2. Décodage en faisceau avec `pyctcdecode`. Règle `alpha`, `beta` et la largeur du faisceau sur le jeu de validation, en mesurant à chaque fois le facteur temps réel sur 1 thread.
3. Quantifie ou élague le modèle de langue (format binaire KenLM, élagage) pour rester dans le budget de taille total.
4. Livre un module `src/infer/decoders/beam_kenlm.py` compatible avec l'interface du développeur 1. Il doit aussi marcher avec les sorties de la piste A.

**Stop : tableau glouton contre faisceau, pour chaque piste, avec score, facteur temps réel et taille.**

# Phase B4 — Si le temps le permet (après le 4 décembre)

- Distillation : le meilleur modèle de la piste B sert de professeur au modèle compact de la piste A, sur les données d'entraînement uniquement.
- Moyenne des derniers points de sauvegarde.
- Vérifie que la quantification int8 dégrade le score de moins de quelques dixièmes de point.

# Règles

- Chaque essai est noté dans `experiments.csv`.
- Aucune soumission Zindi sans accord du développeur 1, qui gère la file de soumissions (5 par jour).
- Ne pousse jamais de données ou de poids sur un dépôt public.
- Gel du code le 12 décembre au soir ; soumission finale le 13 décembre avant 18 h.
