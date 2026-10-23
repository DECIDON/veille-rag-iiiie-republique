"""Tests de l'étape 5 — recherche hybride, fusion et rerank (leçon 0005).

Les tests ``unit`` valident la formule RRF et la construction du filtre sans
aucun service. Les tests ``integration`` exercent l'entonnoir complet (préfetche
dense+sparse, fusion, filtre de payload) sur l'encodeur ``dummy`` — à but de
plomberie : le dummy étant lexical, un nom propre commun doit suffire à faire
remonter le bon document.
"""
from __future__ import annotations

import pytest

from atelier.chunking import etape2
from atelier.embedders import creer as creer_dummy
from atelier.fusion import rrf
from atelier.indexation import etape3_encoder, etape4_indexer
from atelier.normalisation import etape1
from atelier.recherche import construire_filtre, recherche_hybride


def test_rrf_le_document_present_dans_les_deux_bras_gagne():
    fusion = rrf([["a", "b"], ["b", "c"]])
    classement = [doc for doc, _ in fusion]
    assert classement == ["b", "a", "c"]  # b cumulatif, a un seul rang, c queue de bras
    assert len(fusion) == 3              # tout le monde est conservé


def test_rrf_score_exact():
    [(premier, score)] = rrf([["a"], ["a"]])
    assert premier == "a"
    assert abs(score - (1 / 61 + 1 / 61)) < 1e-9


def test_rrf_sans_classement_supplementaire_sur_egalite():
    fusion = rrf([["a", "b"], ["b", "a"]])
    assert [d for d, _ in fusion][0] == "a"  # égalité de score → ordre stable (premier vu)


def test_construire_filtre_chambre_et_date():
    pytest.importorskip("qdrant_client")
    filtre = construire_filtre({"chambre": "senat", "from": "1891-01-01", "to": "1891-12-31"})
    assert filtre is not None
    assert len(filtre.must) == 2


def test_construire_filtre_vide_retourne_none():
    pytest.importorskip("qdrant_client")
    assert construire_filtre({}) is None


@pytest.mark.integration
def test_recherche_hybride_retient_le_bon_document(client_qdrant, config_test):
    etape1(config_test)
    etape2(config_test)
    etape3_encoder(config_test)
    etape4_indexer(config_test, client=client_qdrant)

    candidats = recherche_hybride(
        "Decazeville mineurs gendarmes arbitres",
        creer_dummy("dummy"), config_test, client_qdrant,
    )
    ids_attendus = [c["intervention_id"] for c in candidats]
    assert "chambre-1890-01-28-s001-i009" in ids_attendus[:3]


@pytest.mark.integration
def test_filtre_de_recherche_exclut_l_autre_chambre(client_qdrant, config_test):
    etape1(config_test)
    etape2(config_test)
    etape3_encoder(config_test)
    etape4_indexer(config_test, client=client_qdrant)


    candidats = recherche_hybride(
        "budget", creer_dummy("dummy"), config_test, client_qdrant,
        filtres={"chambre": "senat"},
    )
    assert candidats, "le bras dense+sparse doit retourner quelque chose"
    assert all(c["chambre"] == "senat" for c in candidats), \
        "le pré-filtrage de payload doit s'appliquer aux deux bras"
