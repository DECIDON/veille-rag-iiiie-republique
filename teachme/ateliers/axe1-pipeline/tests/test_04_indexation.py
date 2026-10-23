"""Tests de l'étape 4 — indexation Qdrant (leçon 0004).

Marqués ``integration`` : ils exigent ``docker compose up -d`` et le paquet
``qdrant-client``. Ils utilisent l'encodeur ``dummy``, donc tournent hors-ligne
une fois le conteneur démarré. La collection de test est dédiée et nettoyée.
"""
from __future__ import annotations

import pytest

from atelier.chunking import etape2
from atelier.indexation import etape3_encoder, etape4_indexer, point_id
from atelier.normalisation import etape1

pytestmark = pytest.mark.integration


def test_collection_creee_avec_quantification_et_sparse(client_qdrant, config_test):
    etape1(config_test)
    etape2(config_test)
    etape3_encoder(config_test)
    n = etape4_indexer(config_test, client=client_qdrant)
    assert n == 5

    info = client_qdrant.get_collection(config_test.collection)
    assert info.config.params.sparse_vectors and "sparse" in info.config.params.sparse_vectors
    assert info.config.quantization_config.scalar.type == "int8"
    assert info.points_count == 5


def test_payload_et_indices_de_filtre(client_qdrant, config_test):
    from qdrant_client.models import FieldCondition, Filter, MatchValue

    etape1(config_test)
    etape2(config_test)
    etape3_encoder(config_test)
    etape4_indexer(config_test, client=client_qdrant)

    info = client_qdrant.get_collection(config_test.collection)
    champs_indexes = set(info.payload_schema)
    assert {"chambre", "orateur", "date", "parent_id", "session"} <= champs_indexes

    assert client_qdrant.count(
        collection_name=config_test.collection, exact=True,
    ).count == 5
    assert client_qdrant.count(
        collection_name=config_test.collection, exact=True,
        count_filter=Filter(must=[
            FieldCondition(key="chambre", match=MatchValue(value="senat")),
        ]),
    ).count == 2



def test_upsert_idempotent(client_qdrant, config_test):
    etape1(config_test)
    etape2(config_test)
    etape3_encoder(config_test)
    etape4_indexer(config_test, client=client_qdrant)
    etape4_indexer(config_test, client=client_qdrant)  # seconde passe
    assert client_qdrant.count(collection_name=config_test.collection, exact=True).count == 5


def test_point_id_deterministe():
    assert point_id("chambre-1890-01-28-s001-i003-c01") == point_id(
        "chambre-1890-01-28-s001-i003-c01")
