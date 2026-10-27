"""Tests de l'étape 6 — évaluation par questions-réponses (leçon 0005, §6.5).

Tout est testable hors-ligne : le parseur lit le format QUERIES.md, et les
métriques sont des fonctions pures que l'on joue sur des palmarès fictifs.
"""
from __future__ import annotations

from pathlib import Path

from atelier.evaluation import (
    Question,
    evaluer,
    evaluer_compare,
    parser_queries,
    premier_rang,
    rappel_attendus,
)

QUERIES_EXEMPLE = (Path(__file__).resolve().parent.parent
                   / "data" / "questions" / "QUERIES.md")


def test_parser_des_blocs():
    questions = parser_queries(QUERIES_EXEMPLE)
    assert len(questions) == 2                     # Q1 et Q2 du corpus fourni
    assert questions[0].id == "Q1"
    assert questions[0].attendus == ["senat-1922-11-28-s002-i007"]
    assert questions[0].filtres["chambre"] == "senat"
    assert questions[0].filtres["from"] == "1922-11-01"
    assert "budget general" in questions[0].oracle  # question_oracle lu à part
    # Q2 attend une séquence : plusieurs identifiants valides, séparés par virgule
    assert len(questions[1].attendus) == 4
    # Le gabarit final (attributs vides) ne doit pas compter comme question.
    assert all(q.texte for q in questions)


def test_question_realiste_sans_fuite():
    """La question réelle ne doit pas porter les mots qui constituent la réponse."""
    questions = parser_queries(QUERIES_EXEMPLE)
    for q in questions:
        mots_question = set(q.texte.lower().replace("'", " ").split())
        mots_oracle = set(q.oracle.lower().replace("'", " ").split())
        # les hapax de l'oracle (hors frame budgétaire) n'ont rien à faire dans la question
        assert not {"abracadabrante", "moffett", "san", "stefano"} & mots_question


def test_rappel_binaire():
    assert rappel_attendus(["a", "b"], ["z", "a", "y"]) == 1.0
    assert rappel_attendus(["a"], ["z", "y"]) == 0.0


def test_premier_rang():
    assert premier_rang(["a"], ["x", "a", "y"]) == 0.5   # rang 2
    assert premier_rang(["a"], []) == 0.0
    assert premier_rang(["a"], ["a"]) == 1.0


def test_bilan_aggegre_les_questions():
    questions = [
        Question("Q1", "q1", ["a"]),
        Question("Q2", "q2", ["b"]),
    ]

    def recuperer(question, texte):
        return {"Q1": ["a", "x"], "Q2": ["y", "z"]}[question.id]

    bilan = evaluer(questions, recuperer)
    assert bilan["nb_questions"] == 2
    assert bilan["recall"] == 0.5      # Q1 retrouvée, Q2 perdue
    assert bilan["mrr"] == 0.5         # 1.0 pour Q1, 0 pour Q2


def test_compare_double_passe_et_ecart():
    """Avec l'oracle on retrouve, avec la question réelle on se perd : l'écart
    mesuré est exactement celui que l'on veut exhiber à l'étape 6."""
    questions = [
        Question("Q1", "thème vague", ["a"], oracle="mot exact de la réponse"),
        Question("Q2", "autre thème", ["b"]),                      # sans oracle
    ]

    def recuperer(question, texte):
        return ["a" if "exact" in texte else "z"]

    bilan = evaluer_compare(questions, recuperer)
    assert bilan["reel"]["recall"] == 0.0
    assert bilan["oracle"]["recall"] == 1.0          # seulement sur la q. à oracle
    assert bilan["oracle"]["nb_questions"] == 1
    assert bilan["ecart"]["recall"] == 1.0
    assert bilan["detail"][1]["oracle"] is None      # Q2 sans oracle : passe unique
