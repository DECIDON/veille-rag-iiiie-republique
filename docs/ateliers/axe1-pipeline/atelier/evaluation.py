"""Étape 6 — évaluation sur jeu de questions-réponses (leçon 0005, SYNTHÈSE §6.5).

Le seul juge fiable hors distribution est l'évaluation interne : ~200 Q&R
annotées à la main, dont la vérité terrain est l'intervention que la recherche
*doit* retrouver. Ce module évalue sur un échantillon (ici, les deux questions
de QUERIES.md, extraites des 28 Q&R annotées du corpus fourni) avec deux
métriques simples et suffisantes pour l'atelier :

- ``recall@k`` : sur 100 % des questions, au moins un attendu est-il dans les
  k premiers résultats ? (rappel, mesuré par question, moyenné)
- ``MRR`` : l'inverse du rang du premier attendu (1 si premier, 1/2 si second…)

Le format des questions est celui de ``data/questions/QUERIES.md`` (un bloc
Markdown par question) — c'est le fichier que le binôme complétera à la main.
Une ligne optionnelle ``question_oracle:`` autorise le bilan différentiel
(``evaluer_compare``) : question réelle d'un côté, requête oracle de l'autre.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

BLOC = re.compile(r"^##\s+", re.MULTILINE)


@dataclass
class Question:
    id: str
    texte: str
    attendus: list[str]
    filtres: dict = field(default_factory=dict)
    oracle: str = ""  # requête idéale (mots-clés de la réponse) : plafond, jamais question


def parser_queries(chemin: Path) -> list[Question]:
    """Parse le Markdown : un bloc par question, lignes ``- question:``, etc.

    Les lignes comprise entre deux barrières de code ``` sont ignorées : le
    gabarit documenté du fichier reste donc lisible sans polluer l'évaluation.
    """
    contenu = Path(chemin).read_text(encoding="utf-8")
    hors_barrieres, dans_barriere = [], False
    for ligne in contenu.splitlines():
        if ligne.lstrip().startswith("```"):
            dans_barriere = not dans_barriere
            continue
        if not dans_barriere:
            hors_barrieres.append(ligne)
    contenu = "\n".join(hors_barrieres)
    questions: list[Question] = []
    for bloc in BLOC.split(contenu)[1:]:
        lignes = bloc.splitlines()
        identifiant = lignes[0].split("—")[0].strip() if lignes else f"q{len(questions) + 1}"
        champs = {"question": "", "question_oracle": "", "attendus": "", "filtres": ""}
        for ligne in lignes:
            m = re.match(r"^\s*-\s*(question_oracle|question|attendus|filtres)\s*:\s*(.*)$", ligne)
            if m:
                champs[m.group(1)] = m.group(2).strip()
        if not champs["question"] or not champs["attendus"]:
            continue  # bloc commentaire ou exemple non validé
        attendus = [a.strip() for a in champs["attendus"].split(",") if a.strip()]
        filtres: dict = {}
        for paire in (f.strip() for f in champs["filtres"].split(";") if f.strip()):
            if "=" in paire:
                clef, valeur = paire.split("=", 1)
                filtres[clef.strip()] = valeur.strip()
        questions.append(Question(
            identifiant, champs["question"], attendus, filtres, champs["question_oracle"],
        ))
    return questions


def rappel_attendus(attendus: list[str], retours: list[str]) -> float:
    """1.0 si au moins un attendu figure dans les retours, sinon 0.0."""
    ensemble_attendus = set(attendus)
    return 1.0 if ensemble_attendus & set(retours) else 0.0


def premier_rang(attendus: list[str], retours: list[str]) -> float:
    """MRR : 1 / rang du premier attendu retrouvé, 0 si aucun."""
    ensemble = set(attendus)
    for rang, identifiant in enumerate(retours, start=1):
        if identifiant in ensemble:
            return 1.0 / rang
    return 0.0


def _executer(question: Question, recuperer, texte: str) -> dict:
    """Une passe : ``recuperer(question, texte) -> [chunk_id]``, métriques seules."""
    retours = recuperer(question, texte)
    return {
        "id": question.id,
        "texte": texte,
        "rappel": rappel_attendus(question.attendus, retours),
        "premier_rang": premier_rang(question.attendus, retours),
        "retours": retours,
    }


def _agreger(detail: list[dict]) -> dict:
    n = max(1, len(detail))
    return {
        "nb_questions": len(detail),
        "recall": sum(d["rappel"] for d in detail) / n,
        "mrr": sum(d["premier_rang"] for d in detail) / n,
    }


def evaluer(questions: list[Question], recuperer) -> dict:
    """Exécute les questions via la fonction ``recuperer(question, texte) -> [chunk_id]``.

    Retourne le détail par question plus les agrégats ``recall@k`` et ``MRR``.
    """
    detail = [_executer(q, recuperer, q.texte) for q in questions]
    return {"detail": detail, **_agreger(detail)}


def evaluer_compare(questions: list[Question], recuperer) -> dict:
    """Double passe : question réelle (``texte``) puis requête oracle (``oracle``).

    ``reel`` et ``oracle`` sont deux bilans ``{nb_questions, recall, mrr}`` ;
    ``ecart`` = oracle − réel, c'est-à-dire la part de la performance imputable
    aux mots de la réponse glissés dans la question. Le bilan oracle ne porte
    que sur les questions pourvues d'un oracle ; les autres n'y figurent pas.
    """
    detail = []
    for question in questions:
        ligne = {"id": question.id, "reel": _executer(question, recuperer, question.texte)}
        ligne["oracle"] = (
            _executer(question, recuperer, question.oracle) if question.oracle else None
        )
        detail.append(ligne)
    reel = _agreger([l["reel"] for l in detail])
    lignes_avec_oracle = [l for l in detail if l["oracle"]]
    oracle = _agreger([l["oracle"] for l in lignes_avec_oracle]) if lignes_avec_oracle else None
    ecart = (
        {"recall": oracle["recall"] - reel["recall"], "mrr": oracle["mrr"] - reel["mrr"]}
        if oracle else None
    )
    return {"detail": detail, "reel": reel, "oracle": oracle, "ecart": ecart}
