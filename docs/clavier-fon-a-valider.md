# Clavier fon du jeu Xó : choix à valider

**Pour :** le linguiste référent du fon
**Statut :** à valider. Ces choix suivent l'alphabet des langues nationales du Bénin tel que l'équipe le comprend. Ils n'ont encore été vérifiés par aucun spécialiste.

Le jeu propose un clavier virtuel pour écrire le fon. Il remplace le clavier du téléphone dès qu'un champ attend du fon. Merci d'indiquer pour chaque point si le choix est juste, et sinon ce qu'il faut changer. Une colonne « Votre réponse » est prévue dans les tableaux.

## 1. Lettres du clavier

| Rangée | Lettres affichées | Votre réponse |
|---|---|---|
| Lettres propres au fon | ɖ ɛ ɔ ɣ (et Ɖ Ɛ Ɔ Ɣ en majuscules) | |
| Lettres latines | a b c d e f g h i j k l m n o p r s t u v w x y z | |
| Lettres exclues | q | |

Questions :

1. Le **ɣ** fait-il partie de l'orthographe officielle du fon, ou seulement d'autres langues gbe ?
2. Faut-il ajouter des touches pour les digrammes **gb**, **kp** et **ny**, ou les taper lettre par lettre suffit-il ?
3. Une lettre manque-t-elle, ou une lettre est-elle en trop ?

## 2. Tons

Les tons s'écrivent avec un signe au-dessus de la voyelle. On les obtient par un appui long sur une voyelle.

| Ton | Signe | Exemple sur a | Exemple sur ɛ | Votre réponse |
|---|---|---|---|---|
| Haut | accent aigu | á | ɛ́ | |
| Bas | accent grave | à | ɛ̀ | |
| Montant | caron | ǎ | ɛ̌ | |
| Descendant | accent circonflexe | â | ɛ̂ | |
| Moyen | aucun signe | a | ɛ | |

Voyelles qui portent un ton dans le clavier : **a e ɛ i o ɔ u**.

Questions :

4. Ces quatre signes et ce ton moyen sans signe sont-ils la bonne notation ?
5. Le ton moyen doit-il avoir un signe (par exemple un macron, ā) ?
6. Les consonnes nasales syllabiques (**m**, **n**) peuvent-elles porter un ton (par exemple ń, ǹ) ? Si oui, faut-il les ajouter à l'appui long ?
7. L'orthographe courante marque-t-elle tous les tons, ou seulement ceux qui distinguent deux mots ?

## 3. Voyelles nasales

Le clavier ne propose pas de touche spéciale pour les voyelles nasales. On les écrit aujourd'hui en ajoutant **n** après la voyelle (par exemple *ɛn*, *ɔn*).

8. Est-ce la bonne notation ? Faut-il plutôt un tilde (ɛ̃) ?
9. Comment noter le ton d'une voyelle nasale : sur la voyelle (*ɛ́n*) ?

## 4. Codage du texte

Chaque texte est enregistré sous une forme Unicode unique (NFC). Ainsi, un même mot est toujours codé de la même façon, quel que soit le clavier utilisé. Ce point est technique et ne demande pas de réponse, sauf si une lettre s'affiche mal dans le jeu.

## Après validation

Toutes les lettres et tous les tons sont définis dans un seul fichier du code, [tts_demo/frontend/src/fonInput.ts](../tts_demo/frontend/src/fonInput.ts). Les corrections du linguiste s'appliquent donc à un seul endroit.
