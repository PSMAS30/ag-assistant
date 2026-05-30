"""
demo_data.py — AG fictive pré-chargée pour le mode démo (sans audio, sans clé API)
Simule 3 types d'AG : copropriété, association, PME
"""

DEMOS = {
    "copropriete": {
        "label": "🏢 Copropriété Les Acacias — AG annuelle 2024",
        "metadata": {
            "type": "copropriete",
            "nom": "Copropriété Les Acacias",
            "date": "2024-06-15",
            "lieu": "Salle communale, 12 rue des Lilas, 75012 Paris",
            "syndic": "Cabinet Durand & Associés",
            "nb_lots": 24,
            "nb_presents": 14,
            "nb_representes": 4,
            "nb_absents": 6,
            "tantiemes_presents": 612,
            "tantiemes_total": 1000,
        },
        "transcription": """
Bonjour à toutes et à tous. Il est dix-huit heures trente, je déclare ouverte l'assemblée générale
annuelle de la copropriété Les Acacias pour l'exercice 2024.

Je suis Maître Lefebvre, représentant du Cabinet Durand et Associés, syndic de la copropriété.

Nous avons 14 copropriétaires présents et 4 représentés par procuration, soit 18 copropriétaires
sur 24, représentant 612 millièmes sur 1000. Le quorum est atteint, nous pouvons débuter.

Ordre du jour :
Point 1 : Approbation des comptes de l'exercice 2023
Point 2 : Vote du budget prévisionnel 2024-2025
Point 3 : Travaux de ravalement de façade
Point 4 : Remplacement de la chaudière collective
Point 5 : Questions diverses

--- Point 1 : Approbation des comptes 2023 ---

Je vous présente les comptes de l'exercice 2023. Les charges totales s'élèvent à 48 320 euros,
conformes au budget voté l'année dernière. Le solde créditeur est de 2 150 euros.

Vote : Qui approuve les comptes de l'exercice 2023 ?
Pour : 16 voix. Contre : 1 voix. Abstention : 1 voix.
Les comptes sont approuvés.

--- Point 2 : Budget prévisionnel 2024-2025 ---

Le budget prévisionnel proposé pour 2024-2025 est de 51 000 euros, soit une augmentation de 5,5%
liée à la hausse des coûts énergétiques.

Vote : Qui approuve le budget prévisionnel 2024-2025 à 51 000 euros ?
Pour : 15 voix. Contre : 2 voix. Abstention : 1 voix.
Le budget est approuvé.

--- Point 3 : Travaux de ravalement de façade ---

Trois devis ont été soumis. Le devis retenu par le conseil syndical est celui de l'entreprise
Façades Pro pour un montant de 87 000 euros TTC, travaux à réaliser au printemps 2025.
Un appel de fonds exceptionnel de 3 625 euros par lot sera voté.

Vote : Qui approuve les travaux de ravalement avec l'entreprise Façades Pro pour 87 000 euros ?
Pour : 13 voix. Contre : 4 voix. Abstention : 1 voix.
Les travaux sont approuvés. Majorité article 25 atteinte.

--- Point 4 : Remplacement de la chaudière collective ---

La chaudière date de 1998 et présente des signes de vieillissement. Le devis pour une chaudière
à condensation nouvelle génération s'élève à 22 500 euros. Ce remplacement permettrait une
économie estimée à 18% sur les charges de chauffage.

Vote : Qui approuve le remplacement de la chaudière pour 22 500 euros ?
Pour : 9 voix. Contre : 7 voix. Abstention : 2 voix.
La résolution est rejetée. La majorité de l'article 25 n'est pas atteinte.

--- Point 5 : Questions diverses ---

Madame Petit signale un problème d'humidité dans les parties communes du sous-sol. Le syndic
prend note et fera intervenir un diagnostiqueur dans les 30 jours.

Monsieur Bernard demande si le digicode de la porte principale peut être changé. Accord général,
le syndic s'en charge dans les 15 jours.

Il est vingt heures dix, la séance est levée.
""",
    },

    "association": {
        "label": "🤝 Association Sportive Élan Vitry — AG extraordinaire",
        "metadata": {
            "type": "association",
            "nom": "Association Sportive Élan Vitry",
            "date": "2024-09-28",
            "lieu": "Gymnase municipal de Vitry-sur-Seine",
            "president": "Sophie Marchand",
            "nb_membres": 87,
            "nb_presents": 43,
            "nb_representes": 8,
            "quorum_requis": "50% + 1",
        },
        "transcription": """
Bonsoir à tous. Il est dix-neuf heures, j'ouvre cette assemblée générale extraordinaire de
l'Association Sportive Élan Vitry. Je suis Sophie Marchand, présidente de l'association.

Nous comptons 43 membres présents et 8 procurations, soit 51 membres sur 87 inscrits.
Le quorum requis est de 50% des membres plus un, soit 44 voix. Nous atteignons ce quorum.

Cette AGE a été convoquée pour deux points urgents.

--- Point 1 : Modification des statuts — cotisation annuelle ---

Suite à la hausse des coûts de location du gymnase, le bureau propose de porter la cotisation
annuelle de 80 euros à 110 euros pour les adultes, et de 50 euros à 65 euros pour les moins
de 18 ans. Cette mesure prendrait effet au 1er janvier 2025.

Débat : Monsieur Karim Diallo s'interroge sur la possibilité d'un tarif solidaire. La présidente
précise qu'un tarif réduit à 80 euros existera sur demande auprès du trésorier.

Vote : Qui approuve la modification de l'article 12 des statuts relatif aux cotisations ?
Pour : 44 voix. Contre : 5 voix. Abstention : 2 voix.
La modification des statuts est adoptée à la majorité des deux tiers.

--- Point 2 : Acquisition d'équipements sportifs ---

Le bureau souhaite acheter 2 buts de football homologués et renouveler les dossards.
Budget total estimé : 3 200 euros, financé à 50% par une subvention municipale déjà obtenue.
La part restante de 1 600 euros sera prélevée sur les réserves de l'association.

Vote : Qui approuve l'acquisition des équipements pour 3 200 euros ?
Pour : 49 voix. Contre : 0 voix. Abstention : 2 voix.
La résolution est adoptée à l'unanimité.

Prochaine AG ordinaire : mars 2025. La séance est levée à vingt heures vingt-cinq.
""",
    },

    "pme": {
        "label": "🏭 SAS Innov'Tech — AG ordinaire annuelle",
        "metadata": {
            "type": "pme",
            "nom": "SAS Innov'Tech",
            "date": "2024-04-30",
            "lieu": "Siège social — 45 avenue de la République, 69003 Lyon",
            "president": "Alexandre Fontaine",
            "capital_social": "150 000 €",
            "nb_associes": 5,
            "nb_presents": 5,
            "parts_totales": 1500,
        },
        "transcription": """
Il est quatorze heures. Alexandre Fontaine, président de la SAS Innov'Tech, ouvre l'assemblée
générale ordinaire annuelle des associés. Tous les associés sont présents, représentant la
totalité des 1 500 parts sociales. Le quorum est atteint.

Présents : Alexandre Fontaine (600 parts), Nadia Benchikh (300 parts), Thomas Roux (250 parts),
Claire Vidal (200 parts), Marc Lejeune (150 parts).

--- Point 1 : Approbation des comptes annuels 2023 ---

Le directeur financier Thomas Roux présente les comptes. Le chiffre d'affaires 2023 s'établit
à 2,3 millions d'euros, en progression de 18% par rapport à 2022. Le résultat net est de
142 000 euros. Les capitaux propres s'élèvent à 380 000 euros.

Vote : Approbation des comptes annuels de l'exercice 2023.
Pour : 1 500 parts (unanimité). Contre : 0. Abstention : 0.
Résolution adoptée à l'unanimité.

--- Point 2 : Affectation du résultat ---

Le président propose d'affecter le résultat comme suit : 14 200 euros en réserve légale,
50 000 euros en réserves facultatives, et 77 800 euros distribués en dividendes aux associés
au prorata de leurs parts.

Vote : Approbation de l'affectation du résultat.
Pour : 1 500 parts (unanimité). Contre : 0. Abstention : 0.
Résolution adoptée à l'unanimité.

--- Point 3 : Renouvellement du mandat du commissaire aux comptes ---

Le mandat du cabinet Ernst & Martin arrive à échéance. Le président propose son renouvellement
pour une durée de 6 exercices.

Vote : Renouvellement du mandat du commissaire aux comptes.
Pour : 1 350 parts. Contre : 150 parts (Marc Lejeune). Abstention : 0.
Résolution adoptée.

--- Point 4 : Autorisation d'emprunt bancaire ---

Pour financer l'acquisition de nouveaux équipements de production, la direction sollicite
une autorisation d'emprunt auprès du Crédit Industriel de Lyon, d'un montant maximum de
200 000 euros sur 5 ans.

Vote : Autorisation d'emprunt jusqu'à 200 000 euros.
Pour : 1 500 parts (unanimité). Contre : 0. Abstention : 0.
Résolution adoptée à l'unanimité.

La séance est levée à seize heures quinze.
""",
    },
}


def get_demo(key: str) -> dict:
    """Retourne les données d'une démo par clé."""
    if key not in DEMOS:
        raise ValueError(f"Démo inconnue : {key}. Valeurs possibles : {list(DEMOS.keys())}")
    return DEMOS[key]


def list_demos() -> list[dict]:
    """Retourne la liste des démos disponibles pour l'interface."""
    return [{"key": k, "label": v["label"]} for k, v in DEMOS.items()]
