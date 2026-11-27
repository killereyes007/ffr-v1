# Contexte

Nous participons au **BENIN Tonal ASR Challenge pour le fongbé** (Zindi) :
https://zindi.world/competitions/frugal-tonal-asr-challenge-for-fongbe

Objectif : un modèle de reconnaissance vocale qui transcrit le fongbé parlé en texte correctement écrit, avec tous ses tons.
Équipe : 2 développeurs. Clôture : **13 décembre 2026, 22 h 30 (heure du Bénin)**. Résultats privés : 14 décembre.

## Règles non négociables

- **Score** : WER pondéré calculé sur les **syllabes**. Chaque transcription passe par la fonction publique `syllabify()`, qui normalise, découpe en syllabes et écrit chaque ton en chiffre (« Un nɔ́ ɖu nǔ » → « un nɔ1 ɖu nu3 »). Chaque phrase pèse la racine carrée de son nombre de syllabes de référence. Score = somme des erreurs pondérées / somme des poids. 0 = parfait. Une soumission non syllabée obtient un très mauvais score.
- **Inférence (audio → texte syllabé)** : 1 seul thread CPU, aucun GPU, facteur temps réel ≤ 1 sur tout le jeu de test, mémoire vive ≤ 2 Go, taille totale des poids (modèle de langue compris, après quantification) ≤ 1 000 Mo, hors ligne. Outil officiel : `measure_frugality.py`.
- **Nos cibles internes avec marge** : facteur temps réel ≤ 0,6, RAM ≤ 1,5 Go, taille ≤ 700 Mo.
- **Entraînement** : libre, GPU autorisés (Kaggle et Colab gratuits).
- **Données** : uniquement celles fournies par le challenge (environ 350 h, qualité mélangée : enregistrements validés, tons incertains, lectures de la Bible). Aucun corpus externe, y compris pour l'augmentation (pas de MUSAN, pas de FFSTC).
- **Modèles pré-entraînés** : autorisés s'ils sont ouverts à tous. Outils open source uniquement. Pas d'AutoML. Pas de service payant.
- **Reproductibilité** : graines fixées partout.
- **Confidentialité** : les données ne sortent jamais de l'équipe. Dépôt Git **privé**. `data/`, `models/`, `*.wav`, `*.flac`, `*.mp3` et `*.arrow` dans `.gitignore`. Rien de public sur Kaggle, Hugging Face ou GitHub.
- **Soumissions** : 5 par jour, 100 au total.

# Ta mission (commune aux 2 développeurs, à faire en premier)

Travaille en **audit d'abord**, par phases. À la fin de chaque phase, arrête-toi, résume ce que tu as fait et trouvé, signale explicitement toute ambiguïté, puis attends ma validation avant de continuer. N'invente jamais un format, un chemin ou une colonne : lis les fichiers réels.

## Phase 0 — Audit des données et du kit officiel

1. Inspecte le dossier de données téléchargé depuis Zindi (je te donne son chemin). Liste les fichiers, les formats audio (fréquence d'échantillonnage, canaux, durée), les colonnes des CSV ou métadonnées, le format exact du fichier de soumission (`SampleSubmission` ou équivalent) et le kit fourni (`syllabify()`, `measure_frugality.py`, script de score s'il existe).
2. Produis `reports/00_audit_donnees.md` avec :
   - les heures totales et le nombre de fichiers par sous-ensemble (validé, tons incertains, Bible, ou ce que les métadonnées permettent de distinguer) ;
   - le nombre de locuteurs, s'il est disponible ;
   - la distribution des durées et des longueurs en syllabes ;
   - l'inventaire des caractères (lettres, diacritiques, formes NFC et NFD) ;
   - les anomalies : audio vide ou tronqué, transcription vide, caractères étranges.
3. Teste `syllabify()` :
   - sur 20 transcriptions réelles, affiche avant et après ;
   - vérifie si `syllabify(syllabify(x)) == syllabify(x)` (idempotence) ;
   - vérifie si l'on peut reconstruire le texte accentué à partir de la forme syllabée.
   Écris les conclusions dans le rapport. Elles décident de l'unité de sortie des modèles.

**Stop : attends ma validation.**

## Phase 1 — Squelette du dépôt

Crée cette structure :

```
asr-fongbe/
  README.md            # comment tout relancer, de zéro
  requirements.txt     # versions figées
  .gitignore
  configs/             # un YAML par expérience
  src/
    data/              # chargement, normalisation, découpage train/valid
    text/              # normalisation Unicode, wrapper syllabify, vocabulaires
    metrics/           # score local identique à Zindi
    infer/             # inférence 1 thread → CSV de soumission
    frugality/         # wrapper autour de measure_frugality.py
  notebooks/           # notebooks Kaggle ou Colab (entraînement GPU)
  reports/
  experiments.csv      # une ligne par essai
```

- `src/text/normalize.py` : une seule fonction de normalisation (NFC ou NFD selon la phase 0, apostrophes, espaces), utilisée partout.
- `src/metrics/score.py` : réimplémente exactement le score Zindi (syllabify, WER par syllabe avec substitutions, suppressions et insertions, poids √n). Teste-le sur des cas simples : identique = 0, une syllabe fausse, un ton faux. Si un script officiel existe, vérifie que les deux donnent le même résultat.
- `experiments.csv` : colonnes `date, auteur, id_essai, piste, modele, unite_sortie, decodage, score_valid, taille_mo, rtf_1thread, ram_mo, score_public, notes`.

**Stop : attends ma validation.**

## Phase 2 — Jeu de validation et première soumission

1. Crée un jeu de validation d'environ 5 h, pris seulement dans les enregistrements validés, avec des locuteurs absents de l'entraînement si l'information existe (sinon, découpe par source ou par session). Graine fixée. Enregistre les listes dans `data/splits/`.
2. Fais une première soumission très simple, dont le seul but est de valider la chaîne de bout en bout : format du fichier, syllabification, mesure de frugalité. Par exemple, un petit modèle pré-entraîné ouvert en zero-shot, ou une sortie triviale. Le script `src/infer/predict.py` doit :
   - forcer 1 thread (`OMP_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, `torch.set_num_threads(1)`) ;
   - lire les audios de test et produire le CSV au format exact de Zindi, **syllabé** ;
   - afficher le temps total et le facteur temps réel.
3. Lance `measure_frugality.py` sur cette chaîne, puis ajoute la ligne dans `experiments.csv`.

**Stop : montre-moi le score local, le CSV et les mesures avant que je soumette.**

# Contraintes de travail

- Python 3.10+, PyTorch, aucun paquet maison dans le code de soumission.
- Code lisible et commenté en français, fonctions courtes, chemins configurables.
- Ne lance jamais un entraînement long en local sans me prévenir : les entraînements se font dans `notebooks/` sur Kaggle ou Colab.
