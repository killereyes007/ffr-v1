"""Contenu du jeu : textes FRANÇAIS à traduire / dire en fon, par domaine.

Aucune traduction fon n'est fournie ici : le fon vient des contributeurs, puis
des experts. Chaque ligne est un élément ; le niveau découle du type :
  mot -> facile, phrase -> moyen, paragraphe -> difficile.
Les listes sont écrites une ligne par élément (lignes vides ignorées).
"""

DOMAINS = [
    {"id": "sante", "label": "Santé", "mode": "histoire", "position": 1,
     "story_kicker": "Un centre de santé de quartier",
     "story_title": "Au centre de santé du quartier",
     "story_body": "L'agent de santé reçoit les habitants du quartier dès le matin. Aujourd'hui, une mère est venue avec son enfant qui tousse depuis plusieurs jours."},
    {"id": "education", "label": "Éducation", "mode": "histoire", "position": 2,
     "story_kicker": "Une salle de classe de village",
     "story_title": "La rentrée à l'école du village",
     "story_body": "C'est le premier jour de classe après les vacances. L'instituteur accueille les élèves devant l'école, certains reviennent de loin pour cette rentrée."},
    {"id": "religion_traditions", "label": "Religion & traditions", "mode": "histoire", "position": 3,
     "story_kicker": "Une cérémonie saisonnière",
     "story_title": "La cérémonie du village",
     "story_body": "Une fois par saison, les familles du village se réunissent autour des anciens pour une cérémonie transmise depuis des générations."},
    {"id": "agriculture", "label": "Agriculture", "mode": "phrases", "position": 4},
    {"id": "commerce_marche", "label": "Commerce & marché", "mode": "phrases", "position": 5},
    {"id": "administration", "label": "Administration & vie quotidienne", "mode": "phrases", "position": 6},
    {"id": "metiers_travail", "label": "Métiers & travail", "mode": "phrases", "position": 7},
]

CONTENT = {
    "sante": {
        "mot": """
la fièvre
le médicament
la tête
le ventre
la toux
la douleur
le médecin
l'infirmière
l'hôpital
le centre de santé
la pharmacie
le paludisme
le moustique
la moustiquaire
le vaccin
la piqûre
l'enfant
le bébé
la femme enceinte
le sang
le cœur
la main
le pied
l'œil
la dent
le dos
l'eau propre
le savon
la maladie
la guérison
le repos
le rendez-vous
l'ordonnance
le comprimé
la blessure
le pansement
la diarrhée
la vaccination
la température
la santé
""",
        "phrase": """
Bonjour, qu'est-ce qui vous amène aujourd'hui ?
Avez-vous de la fièvre depuis combien de jours ?
Buvez beaucoup d'eau et reposez-vous.
N'oubliez pas de revenir si ça ne va pas mieux.
Où as-tu mal ?
J'ai mal à la tête depuis hier.
Mon enfant ne mange plus depuis ce matin.
Prends ce comprimé deux fois par jour.
Dors sous la moustiquaire chaque nuit.
Lave-toi les mains avec du savon avant de manger.
Le médecin va vous recevoir dans un instant.
Je voudrais prendre un rendez-vous pour demain.
Il faut emmener le malade à l'hôpital.
Est-ce que la douleur est forte ?
Respire doucement, tout va bien se passer.
Ne bois pas l'eau du marigot, elle n'est pas propre.
Le vaccin protège les enfants contre les maladies.
Elle attend un bébé pour le mois prochain.
Montre-moi où tu t'es blessé.
La pharmacie ferme à huit heures du soir.
""",
        "paragraphe": """
L'agent de santé explique calmement que la fièvre peut avoir plusieurs causes, qu'il faut surveiller la température chaque soir et revenir si elle ne baisse pas après trois jours de repos.
Pendant la saison des pluies, les moustiques sont nombreux. Chaque famille doit dormir sous une moustiquaire, vider les eaux stagnantes autour de la maison et consulter dès les premiers signes de fièvre.
Avant de préparer le repas, il faut se laver les mains avec du savon, utiliser de l'eau propre et couvrir les aliments. Ces gestes simples protègent toute la famille contre la diarrhée.
""",
    },
    "education": {
        "mot": """
le cahier
la leçon
le livre
le stylo
le crayon
la craie
le tableau
l'école
la classe
l'instituteur
la maîtresse
l'élève
le directeur
la cour de récréation
le banc
le cartable
la règle
la gomme
l'examen
la note
le devoir
la lecture
l'écriture
le calcul
la dictée
la rentrée
les vacances
la récréation
la question
la réponse
l'alphabet
la lettre
le nombre
le dessin
la chanson
le jeu
l'uniforme
la bibliothèque
le certificat
l'apprentissage
""",
        "phrase": """
Ouvrez vos cahiers à la page dix.
Qui peut me dire la capitale du Bénin ?
Le travail que tu as fait est très bien.
N'oublie pas d'apporter ton livre demain.
Levez la main avant de parler.
Écoutez bien, je répète une seule fois.
Copie ce texte dans ton cahier.
Combien font deux plus trois ?
La récréation commence dans cinq minutes.
Range tes affaires dans ton cartable.
Tu as bien lu, continue comme ça.
Demain, nous avons un examen de calcul.
Qui n'a pas fini son devoir ?
Viens au tableau écrire ton nom.
L'école est ouverte du lundi au vendredi.
Les élèves chantent avant de commencer la classe.
Je ne comprends pas la question.
Peux-tu répéter, s'il te plaît ?
Il faut apprendre sa leçon chaque soir.
Bravo, tu as la meilleure note de la classe !
""",
        "paragraphe": """
L'instituteur rappelle que chaque élève doit relire sa leçon le soir, et que ceux qui ont des difficultés peuvent rester après la classe pour qu'on reprenne ensemble les parties mal comprises.
Chaque matin, les enfants marchent plusieurs kilomètres pour arriver à l'école. Ils se saluent dans la cour, rangent leurs cartables et s'assoient en silence quand la maîtresse entre dans la classe.
À la fin de l'année, le directeur réunit les parents pour donner les résultats. Les élèves qui ont bien travaillé reçoivent un certificat et toute l'école applaudit.
""",
    },
    "religion_traditions": {
        "mot": """
la cérémonie
les anciens
l'ancêtre
la tradition
le chant
le tambour
la danse
le village
la famille
le chef
le roi
le masque
la fête
la prière
l'offrande
le marché sacré
le proverbe
le conte
le griot
la coutume
la naissance
le mariage
le deuil
le baptême
le temple
l'église
la mosquée
le couvent
le vodoun
la bénédiction
la libation
l'esprit
la mémoire
l'histoire
la récolte
la saison
la terre
la rivière
l'arbre sacré
le respect
""",
        "phrase": """
Les anciens nous ont transmis cette histoire.
Chaque saison, le village se réunit ici.
Respecte la terre de tes ancêtres.
Cette fête rassemble toute la famille.
Les tambours résonnent dans tout le village.
Écoute le conte que raconte grand-père.
Il faut saluer les anciens avec respect.
Les enfants dansent autour du feu.
Nous remercions nos ancêtres pour cette récolte.
Le chef du village prend la parole.
Chaque famille apporte son offrande.
Le mariage aura lieu à la saison sèche.
Ne parle pas fort pendant la prière.
Cette coutume est très ancienne.
Le proverbe dit que la patience est une richesse.
Nous portons des habits blancs pour la cérémonie.
La mémoire des anciens est notre bibliothèque.
Le bébé recevra son nom dans une semaine.
Ils chantent ensemble jusqu'au lever du soleil.
Transmettons nos traditions à nos enfants.
""",
        "paragraphe": """
Chaque saison, les familles se rassemblent autour des anciens pour écouter les récits transmis de génération en génération, et personne ne quitte la cérémonie avant que le dernier chant ne soit terminé.
Quand un bébé naît, la famille se réunit pour lui donner son nom. Les anciens bénissent l'enfant, les tambours résonnent et chacun apporte un petit cadeau pour lui souhaiter une longue vie.
Le soir, autour du feu, le conteur commence une histoire. Les enfants écoutent en silence, car chaque conte garde un conseil précieux que les anciens veulent transmettre.
""",
    },
    "agriculture": {
        "mot": """
la récolte
le champ
la semence
le maïs
le manioc
l'igname
le haricot
l'arachide
le palmier
le cocotier
la houe
la machette
la charrue
le tracteur
la pluie
la saison sèche
la saison des pluies
la terre
le sol
l'engrais
l'eau
le puits
le jardin
le légume
la tomate
le piment
l'oignon
la banane
l'ananas
la mangue
le coton
le poulet
la chèvre
le mouton
le bœuf
le poisson
l'étang
le grenier
le paysan
le troupeau
""",
        "phrase": """
Il va pleuvoir, il faut rentrer les régimes de maïs.
Le champ de mon père est derrière la rivière.
Nous semons le maïs au début de la saison des pluies.
Prends la houe et viens m'aider au champ.
La récolte de manioc sera bonne cette année.
Il faut arroser les tomates le soir.
Les chèvres mangent l'herbe près du chemin.
La terre est trop sèche, nous attendons la pluie.
Mets les haricots au soleil pour les sécher.
Le grenier est plein de maïs.
Mon frère garde le troupeau toute la journée.
Il faut enlever les mauvaises herbes.
L'igname se plante en début d'année.
Nous vendons nos légumes au marché.
Le puits est profond, fais attention.
Les oiseaux mangent les graines dans le champ.
Cette année, la récolte d'ananas est abondante.
Ma mère prépare la terre avant de semer.
Il faut protéger les jeunes plants du vent.
Nous partageons la récolte entre les familles.
""",
        "paragraphe": """
Chaque matin, je vais au champ avant qu'il fasse trop chaud. Je m'occupe des plants et j'arrose quand la terre est sèche.
Au début de la saison des pluies, les paysans préparent la terre, plantent le maïs et le manioc, puis surveillent les champs chaque semaine pour enlever les mauvaises herbes.
Après la récolte, la famille fait sécher le maïs au soleil, le range dans le grenier et vend le reste au marché pour acheter de quoi nourrir les enfants et payer l'école.
""",
    },
    "commerce_marche": {
        "mot": """
le prix
le marché
la vendeuse
l'acheteur
l'argent
la monnaie
le franc
le tissu
le pagne
la balance
le sac
le panier
la boutique
la marchandise
le poisson fumé
la viande
le riz
l'huile
le sel
le sucre
la farine
le savon
la tomate
la pomme de terre
le crédit
la dette
la réduction
le client
le commerçant
le transport
la moto
le colis
la commande
le bénéfice
la perte
l'étal
la quantité
le kilo
le tas
le paiement
""",
        "phrase": """
Combien coûte ce tissu ?
C'est trop cher, peux-tu baisser un peu ?
Je reviendrai demain acheter plus.
Donne-moi un kilo de riz, s'il te plaît.
Voici ta monnaie, merci beaucoup.
Quel est le prix de ce panier ?
Ces tomates sont fraîches, goûte-les.
Je n'ai pas assez d'argent aujourd'hui.
Peux-tu me faire un meilleur prix ?
Le marché est ouvert tous les cinq jours.
Elle vend du poisson fumé au bord de la route.
J'achète trois tas de piment.
Mets tout dans le sac, merci.
Tu peux payer demain, je te fais confiance.
Cette marchandise vient du Nigeria.
Le client a toujours raison.
Combien de pagnes veux-tu ?
La vendeuse pèse le riz sur la balance.
Les affaires sont calmes aujourd'hui.
Nous ouvrons la boutique à sept heures.
""",
        "paragraphe": """
Chaque matin, la vendeuse installe son étal au marché. Elle range les tomates, les piments et les oignons, puis salue les clients et discute du prix avec chacun d'eux.
Pour acheter du tissu, il faut comparer les prix de plusieurs boutiques, toucher la qualité et discuter calmement. Un bon commerçant sait faire un meilleur prix à ceux qui reviennent souvent.
À la fin de la journée, le commerçant compte l'argent, note ce qu'il a vendu et prépare la commande du lendemain pour ne jamais manquer de marchandise.
""",
    },
    "administration": {
        "mot": """
la carte d'identité
le passeport
le certificat de naissance
l'acte de mariage
le formulaire
la signature
le tampon
le bureau
la mairie
le maire
le quartier
l'arrondissement
la police
le commissariat
le tribunal
le juge
la banque
le compte
le téléphone
le numéro
l'adresse
la rue
la maison
le loyer
l'électricité
la facture
le courrier
la poste
le bus
le taxi
la route
l'impôt
le vote
l'électeur
le passage piéton
la file d'attente
le guichet
le document
la photo
la nationalité
""",
        "phrase": """
Où se trouve le bureau du quartier ?
J'ai besoin d'un certificat de naissance.
Le marché ferme à quelle heure aujourd'hui ?
Remplissez ce formulaire et signez en bas.
Quel est votre nom et votre adresse ?
Il faut apporter deux photos d'identité.
Le guichet ouvre à huit heures.
Je voudrais ouvrir un compte à la banque.
Combien coûte le transport jusqu'à la ville ?
Prenez la deuxième rue à gauche.
Mon numéro de téléphone est écrit ici.
Avez-vous votre carte d'identité ?
Il faut payer la facture d'électricité avant la fin du mois.
Le maire reçoit les habitants le mardi.
Revenez demain avec tous vos documents.
Je cherche la poste du quartier.
Le taxi me dépose devant la mairie.
Faites la queue, s'il vous plaît.
Où est-ce que je peux voter ?
Le loyer se paie au début du mois.
""",
        "paragraphe": """
Pour obtenir un certificat de naissance, il faut se rendre à la mairie avec une pièce d'identité et deux photos. L'agent remplit le formulaire, appose le tampon et remet le document en quelques jours.
Chaque mois, la famille paie la facture d'électricité et le loyer. Mon père garde tous les papiers dans une pochette pour les retrouver facilement quand l'administration les demande.
Le jour des élections, les habitants du quartier font la queue devant le bureau de vote. Chacun présente sa carte, signe la liste et dépose son bulletin dans l'urne.
""",
    },
    "metiers_travail": {
        "mot": """
le mécanicien
le menuisier
le maçon
le forgeron
le tailleur
la couturière
le coiffeur
le cuisinier
le boulanger
le pêcheur
le chauffeur
le conducteur de moto
le commerçant
le médecin
l'infirmier
le professeur
l'électricien
le plombier
le peintre
le tisserand
le potier
le boucher
le gardien
le patron
l'ouvrier
l'apprenti
le salaire
le chantier
l'atelier
l'outil
le marteau
la scie
la machine
la clé
le travail
le métier
l'entreprise
la fatigue
le contrat
l'expérience
""",
        "phrase": """
Je cherche du travail pour la saison sèche.
Mon oncle est menuisier depuis vingt ans.
Le mécanicien répare ma moto.
Le maçon construit la maison de mon voisin.
Ma sœur est couturière au marché.
Passe-moi le marteau, s'il te plaît.
L'apprenti observe son maître avec attention.
Le patron paie les ouvriers à la fin du mois.
Il travaille du matin jusqu'au soir.
Le pêcheur part avant le lever du soleil.
Le chauffeur conduit le car jusqu'à la ville.
Je voudrais apprendre le métier de forgeron.
Le chantier commence lundi prochain.
La boulangère fait du pain chaque nuit.
Un bon ouvrier respecte toujours ses outils.
Le tailleur prend les mesures du client.
Mon père répare les chaussures depuis trente ans.
Le travail bien fait rend fier.
Il faut de la patience pour apprendre un métier.
Le coiffeur ouvre son salon à huit heures.
""",
        "paragraphe": """
Mon frère répare les motos au bord de la route. Beaucoup de gens viennent le voir quand leur moto tombe en panne.
Le menuisier choisit le bois, le mesure avec soin, puis le coupe à la scie. Il assemble les planches pour fabriquer une table solide que sa famille et ses clients utiliseront pendant des années.
Dans l'atelier de couture, l'apprentie observe sa maîtresse. Elle apprend à prendre les mesures, à couper le tissu et à coudre chaque vêtement avec patience avant de recevoir ses premiers clients.
""",
    },
}


def iter_items():
    """Produit (domain_id, kind, texte, position) pour tout le contenu."""
    for domain_id, kinds in CONTENT.items():
        for kind, block in kinds.items():
            position = 0
            for line in block.splitlines():
                text = line.strip()
                if not text:
                    continue
                position += 1
                yield domain_id, kind, text, position
