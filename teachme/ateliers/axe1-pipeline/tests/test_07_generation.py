"""Tests de l'étape 7 (bonus) — génération RAG via Ollama (leçon 0006).

Le test unitaire vérifie la construction du prompt (contraintes de citation).
Le test marqué ``reseau`` exige Ollama démarré et le modèle tiré : il est
sauté silencieusement sinon.
"""
from __future__ import annotations

import pytest

from atelier.generation import construire_prompt, generer
from atelier.config import Config


def un_resultat(**surcharge) -> dict:
    base = {
        "intervention_id": "chambre-1890-01-28-s001-i003",
        "orateur": "Jules Ferry", "chambre": "chambre", "date": "1890-01-28",
        "page_jo": 245, "texte": "l'ecole primaire est la vraie dette de l'Etat",
    }
    return {**base, **surcharge}


def test_prompt_impose_citations_et_refus():
    messages = construire_prompt("budget ecoles ?", [un_resultat()])
    systeme, utilisateur = messages[0]["content"], messages[1]["content"]
    assert "INSUFFISANT" in systeme
    assert "Journal officiel" in systeme
    assert "chambre-1890-01-28-s001-i003" in utilisateur
    assert "page JO 245" in utilisateur
    assert messages[1]["role"] == "user"


@pytest.mark.reseau
def test_generation_reelle():
    config = Config()
    reponse = generer(
        "Que dit le ministre sur l'école primaire ?",
        [un_resultat()], config, timeout=60,
    )
    assert isinstance(reponse, str) and reponse
