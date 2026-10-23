"""Tests de l'étape 6 — évaluation par questions-réponses (leçon 0005, §6.5).

Tout est testable hors-ligne : le parseur lit le format QUERIES.md, et les
métriques sont des fonctions pures que l'on joue sur des palmarès fictifs.
"""
from __future__ import annotations

from pathlib import Path

from atelier.evaluation import (
    Question,
    evaluer,
    parser_queries,
    premier_rang,
    rappel_attendus,
)

QUERIES_EXEMPLE = (Path(__file__).resolve().parent.parent
                   / "data" / "questions" / "QUERIES.md")


def test_parser_des_blocs():
    questions = parser_queries(QUERIES_EXEMPLE)
    assert len(questions) == 2                     # Q1 et Q2 du mini-corpus
    assert questions[0].id == "Q1"
    assert questions[0].attendus == ["chambre-1890-01-28-s001-i003"]
    assert questions[0].filtres["chambre"] == "chambre"
    assert questions[0].filtres["from"] == "1890-01-01"
    # Le gabarit final (attributs vides) ne doit pas compter comme question.
    assert all(q.texte for q in questions)


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

    def recuperer(question):
        return {"Q1": ["a", "x"], "Q2": ["y", "z"]}[question.id]

    bilan = evaluer(questions, recuperer)
    assert bilan["nb_questions"] == 2
    assert bilan["recall"] == 0.5      # Q1 retrouvée, Q2 perdue
    assert bilan["mrr"] == 0.5         # 1.0 pour Q1, 0 pour Q2
