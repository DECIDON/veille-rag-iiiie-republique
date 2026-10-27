"""Exporte les 28 Q&R de queries.json au format QUERIES.md, double passe incluse.

Usage :  uv run python outils/exporte_querries_md.py
Sortie : data/questions/QUERIES.complet.md — fichier généré, à ne pas éditer à
la main (régénérer depuis queries.json). Pour l'évaluer à l'étape 6 :

    ATELIER_QUESTIONS=data/questions/QUERIES.complet.md uv run python -m atelier evaluer

Chaque bloc porte `question:` (la requête réaliste, dérivée de l'intitulé seul)
et `question_oracle:` (les mots-clés de la réponse) : le bilan affiche les deux
passes et leur écart.
"""

import json
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
QUERIES = RACINE / "data/questions/queries.json"
SORTIE = RACINE / "data/questions/QUERIES.complet.md"

doc = json.loads(QUERIES.read_text(encoding="utf-8"))

lignes = [
    "# Jeu de questions complet (28) — généré depuis queries.json",
    "",
    "> Ne pas éditer ici : les vérités terrain vivent dans",
    "> [`queries.json`](queries.json) (`outils/genere_queries.py`).",
    "> Évaluer avec :",
    ">",
    ">     ATELIER_QUESTIONS=data/questions/QUERIES.complet.md uv run python -m atelier evaluer",
    "",
]

for q in doc["questions"]:
    premier = q["generation"]["interventions"][0]["id"]
    # senat-1922-11-28-s002-i007 → chambre=senat ; from=to=2022-11-28
    morceaux = premier.split("-")
    chambre, date = morceaux[0], "-".join(morceaux[1:4])
    attendus = ", ".join(i["id"] for i in q["generation"]["interventions"])
    lignes += [
        f"## {q['id']} — {q['intitule']}",
        f"- question: {q['requete']}",
        f"- question_oracle: {q['requete_oracle']}",
        f"- attendus: {attendus}",
        f"- filtres: chambre={chambre}; from={date}; to={date}",
        "",
    ]

SORTIE.write_text("\n".join(lignes), encoding="utf-8")
print(f"{len(doc['questions'])} blocs → {SORTIE}")
