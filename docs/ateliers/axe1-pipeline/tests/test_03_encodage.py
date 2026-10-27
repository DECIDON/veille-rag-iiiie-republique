"""Tests de l'étape 3 — encodage et cache (leçon 0003).

Le encodeur de test est le `DummyEmbedder` (sac de mots déterministe) : ces
tests vérignent le *contrat* dense+sparse et l'idempotence du cache, pas la
qualité sémantique. Le test marqué ``modele`` valide le contrat sur les vrais
poids bge-m3 (téléchargement ~2 Go, à lancer une fois à la main).
"""
from __future__ import annotations

import json
import math

import pytest

from atelier import embedders
from atelier.chunking import etape2
from atelier.indexation import charger_cache, etape3_encoder
from atelier.normalisation import etape1


def test_dense_dimension_et_norme():
    encodeur = embedders.creer("dummy")
    vecteurs = encodeur.encode_dense(["le budget de l'aéronautique civile"])
    assert len(vecteurs[0]) == 1024
    assert abs(math.sqrt(sum(c * c for c in vecteurs[0])) - 1.0) < 1e-6


def test_dense_deterministe_et_distinct():
    encodeur = embedders.creer("dummy")
    a = encodeur.encode_dense(["le budget de l'aéronautique"])
    b = encodeur.encode_dense(["le budget de l'aéronautique"])
    c = encodeur.encode_dense(["les clauses aériennes du traité"])
    assert a == b
    assert a != c


def test_sparse_ids_positifs_et_poids_strictement_positifs():
    encodeur = embedders.creer("dummy")
    [sparse] = encodeur.encode_sparse(["subventions compagnies aeronef, credits"])
    assert sparse, "le sparse doit être non vide sur un texte non vide"
    assert all(isinstance(i, int) and i > 0 for i in sparse)
    assert all(w > 0 for w in sparse.values())


def test_cache_idempotent(config_test):
    """Encoder deux fois ne recalcule rien la seconde fois."""
    etape1(config_test)
    etape2(config_test)
    n_premier = etape3_encoder(config_test)
    assert n_premier == 165
    n_second = etape3_encoder(config_test)
    assert n_second == 0
    cache = charger_cache(config_test.cache_path)
    assert len(cache) == 165
    entree = next(iter(cache.values()))
    assert len(entree["dense"]) == 1024 and entree["sparse"]


@pytest.mark.modele
def test_contrat_bge_m3():
    """Véritables poids bge-m3 : dense 1 024 d, sparse non vide (marqueur « modele »)."""
    encodeur = embedders.creer("bge-m3")
    texte = "Le budget de l'aéronautique discuté au Sénat en 1922."
    dense = encodeur.encode_dense([texte])[0]
    sparse = encodeur.encode_sparse([texte])[0]
    assert len(dense) == 1024
    assert sparse and all(w > 0 for w in sparse.values())
