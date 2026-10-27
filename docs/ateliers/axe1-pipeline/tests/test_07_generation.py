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
        "intervention_id": "senat-1922-11-28-s002-i140",
        "orateur": "Guy de Montjou", "chambre": "senat", "date": "1922-11-28",
        "page_jo": 11,
        "texte": "une des parties essentielles de l'organisation de notre aviation, c'est précisément l'infrastructure",
    }
    return {**base, **surcharge}


def test_prompt_impose_citations_et_refus():
    messages = construire_prompt("que dit Montjou de l'infrastructure aeronautique ?", [un_resultat()])
    systeme, utilisateur = messages[0]["content"], messages[1]["content"]
    assert "INSUFFISANT" in systeme
    assert "Journal officiel" in systeme
    assert "senat-1922-11-28-s002-i140" in utilisateur
    assert "page JO 11" in utilisateur
    assert messages[1]["role"] == "user"


@pytest.mark.reseau
def test_generation_reelle():
    config = Config()
    reponse = generer(
        "Que dit Montjou de l'infrastructure aéronautique à Laval ?",
        [un_resultat()], config, timeout=60,
    )
    assert isinstance(reponse, str) and reponse
