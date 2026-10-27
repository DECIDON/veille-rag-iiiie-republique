"""Tests de l'étape 2 — découpage par intervention et hiérarchie parent/enfant
(leçon 0002)."""
from __future__ import annotations

import json

from atelier.chunking import (
    decouper_texte,
    enficher,
    estimer_tokens,
    etape2,
    identifiant_seance,
    seance_parent,
)
from atelier.normalisation import etape1


def une_intervention(**surcharge) -> dict:
    base = {
        "id": "senat-1922-11-28-s002-i001",
        "date": "1922-11-28", "chambre": "senat", "session": "1922", "seance": "2",
        "orateur": {"nom": "X", "nom_canonique": "X"}, "page_jo": 1,
        "text_normalise": "Une intervention brève, documentaire fermée.",
        "text_brut": "Une intervention brève, documentaire fermée.",
    }
    return {**base, **surcharge}


def test_intervention_courte_un_seul_enfant():
    enfants = enficher(une_intervention(), max_tokens=1200)
    assert len(enfants) == 1
    enfant = enfants[0]
    assert enfant["chunk_total"] == 1
    assert enfant["parent_id"] == "senat-1922-11-28-s002"
    assert enfant["intervention_id"] == "senat-1922-11-28-s002-i001"
    assert enfant["texte"] == une_intervention()["text_normalise"]


def test_intervention_longe_plusieurs_enfants_numerotes():
    texte = "\n\n".join(
        f"Paragraphe {i}. " + "mot " * 300 for i in range(8)
    )
    enfants = enficher(une_intervention(text_normalise=texte), max_tokens=200)
    assert len(enfants) > 1
    assert [e["chunk_index"] for e in enfants] == list(range(1, len(enfants) + 1))
    assert all(e["chunk_total"] == len(enfants) for e in enfants)
    assert all(enfant["parent_id"] == enfants[0]["parent_id"] for enfant in enfants)


def test_decoupe_ne_perd_aucun_mot():
    texte = "\n\n".join(f"Phrase {i} mot-{i}." for i in range(50))
    fragments = decouper_texte(texte, max_tokens=60)
    mots_origine = sorted(texte.replace("\n", " ").split())
    mots_fragments = sorted(" ".join(fragments).split())
    assert mots_fragments == mots_origine


def test_chaque_fragment_respecte_la_taille_maximale():
    texte = "\n\n".join(" ".join(f"mot{i}" for i in range(400)) for _ in range(5))
    for fragment in decouper_texte(texte, max_tokens=150):
        assert estimer_tokens(fragment) <= 150 * 1.35  # marge d'arrondi ×1,3


def test_parent_reconstitue_la_seance():
    groupe = [
        une_intervention(),
        une_intervention(id="senat-1922-11-28-s002-i002", page_jo=2,
                         orateur={"nom": "Y", "nom_canonique": "Y"}),
    ]
    parent = seance_parent(groupe)
    assert parent["id"] == "senat-1922-11-28-s002"
    assert parent["interventions"] == [g["id"] for g in groupe]
    assert parent["intervenants"] == ["X", "Y"]
    assert "page 1" in parent["texte_reconstitue"]
    assert parent["texte_reconstitue"].count("#") >= 2  # le texte est verbatim, pas résumé


def test_identifiant_seance_complete_le_zero():
    assert identifiant_seance({"chambre": "senat", "date": "1922-11-28", "seance": 2}) \
        == "senat-1922-11-28-s002"


def test_etape2_complete_sur_corpus_fourni(config_test):
    etape1(config_test)
    n_enfants, n_parents = etape2(config_test)
    assert n_enfants == 165      # aucune intervention ne dépasse le plafond de 1 200 tokens
    assert n_parents == 1        # l'export ne couvre qu'une séance
    enfants = [json.loads(l) for l in
               config_test.enfants_path.read_text(encoding="utf-8").splitlines()]
    assert {e["parent_id"] for e in enfants} == {"senat-1922-11-28-s002"}
