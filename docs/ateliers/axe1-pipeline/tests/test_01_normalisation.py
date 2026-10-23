"""Tests de l'étape 1 — normalisation (leçon 0001).

Ils se passent de tout service et de tout modèle : la normalisation est du
Python pur, et c'est voulu — c'est l'étage que l'on contrôle.
"""
from __future__ import annotations

import json

import pytest

from pathlib import Path

from atelier.normalisation import (
    charger_alias,
    charger_corpus,
    cle_alias,
    etape1,
    normaliser_enregistrement,
    normaliser_texte,
    valider,
)

ALIAS = Path(__file__).resolve().parent.parent / "data" / "corpus" / "alias_orateurs.json"


def test_apostrophes_unifiees_accentes_conservés():
    # Les apostrophes se unifient ; les accents restent (NFKD conserve les
    # diacritiques, la recomposition NFC les rend lisibles).
    sortie = normaliser_texte("l’École n’est pas l‘école")
    assert sortie == "l'École n'est pas l'école"


def test_apostrophe_aigu_devenue_ascii():
    sortie = normaliser_texte("d’accord")
    assert "'" in sortie and "\u2019" not in sortie


def test_tilde_et_espaces_insécables():
    sortie = normaliser_texte("livre\u00a0sur\u00a0les\u00a0écoles")
    assert "\u00a0" not in sortie and sortie.count(" ") == 3


def test_césure_rejointée_pas_les_vrais_tirets():
    joint = normaliser_texte("l'insti-\ntution")
    assert joint == "l'institution"
    conserve = normaliser_texte("le garde-\ndes-sceaux")
    # Règle assumée : tout trait d'union de fin de ligne est joint (césure OCR).
    assert "des" in conserve


def test_guillemets_unifies():
    assert normaliser_texte("« discours »") == '"discours"'


def test_texte_brut_jamais_écrasé():
    """normaliser_enregistrement ajoute text_normalise et garde text_brut intact."""
    enreg = {
        "id": "x", "date": "1890-01-28", "chambre": "chambre", "session": "1890",
        "seance": "1", "orateur": {"nom": "Personne"}, "page_jo": 1,
        "text_brut": "l’insti-\ntution",
    }
    enrichi = normaliser_enregistrement(enreg, {})
    assert enrichi["text_brut"] == enreg["text_brut"]
    assert enrichi["text_normalise"] == "l'institution"


def test_alias_orateurs():
    table = charger_alias(ALIAS)
    assert table[cle_alias("J. Ferry")] == "Jules Ferry"
    assert table[cle_alias("Citoyen Basly")] == "Albert Basly"


def test_nom_canonical_ajouté():
    table = charger_alias(ALIAS)
    enreg = {
        "id": "x", "date": "1890-01-28", "chambre": "chambre", "session": "1890",
        "seance": "1", "orateur": {"nom": "J. Ferry"}, "page_jo": 1, "text_brut": "a",
    }
    enrichi = normaliser_enregistrement(enreg, table)
    assert enrichi["orateur"]["nom_canonique"] == "Jules Ferry"


def test_validation_refuse_champs_manquants():
    with pytest.raises(ValueError) as erreur:
        valider({"id": "x", "date": "1890-01-28"})
    assert "orateur" in str(erreur.value) and "text_brut" in str(erreur.value)


def test_validation_refuse_date_non_iso():
    enreg = {
        "id": "x", "date": "28/01/1890", "chambre": "chambre", "session": "1890",
        "seance": "1", "orateur": {"nom": "a"}, "page_jo": 1, "text_brut": "a",
    }
    with pytest.raises(ValueError):
        valider(enreg)


def test_charger_corpus_refuse_doublons(tmp_path):
    enreg = {
        "id": "dup", "date": "1890-01-28", "chambre": "chambre", "session": "1890",
        "seance": "1", "orateur": {"nom": "a"}, "page_jo": 1, "text_brut": "a",
    }
    (tmp_path / "a.json").write_text(json.dumps([enreg, enreg]), encoding="utf-8")
    with pytest.raises(ValueError, match="dupliqué"):
        charger_corpus(tmp_path)


def test_etape1_complete_sur_exemple(config_test):
    n = etape1(config_test)
    assert n == 5
    lignes = (config_test.normalise_dir / "interventions.jsonl").read_text(
        encoding="utf-8").splitlines()
    assert len(lignes) == 5
    premier = json.loads(lignes[0])
    assert "text_normalise" in premier and premier["orateur"].get("nom_canonique")
