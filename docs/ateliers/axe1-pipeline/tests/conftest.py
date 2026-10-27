"""Fixtures communes des tests de l'atelier.

Convention : les tests unitaires (étiquette par défaut) tournent sans aucune
dépendance tierce installée et sans service ; les tests marqués
``integration`` exigent Qdrant (``docker compose up -d``) et sont sautés s'il
est injoignable ; ceux marqués ``modele`` téléchargent les vrais poids.
"""
from __future__ import annotations

import os
import shutil
import socket
from dataclasses import replace
from pathlib import Path
from urllib.parse import urlparse

import pytest

from atelier.config import RACINE, Config

CORPUS_EXEMPLE = RACINE / "data" / "corpus"


def config_sandbox(tmp_path, **surcharge) -> Config:
    """Une configuration qui écrit tout dans le répertoire temporaire pytest.

    Le corpus sous test est une copie du corpus fourni (``debats.converti.json``,
    Sénat, 28 novembre 1922) seule, isolée du vrai dossier ``data/corpus/`` :
    les tests « sur corpus fourni » restent vrais quand vos données réelles y
    sont déposées à côté.
    """
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    for fichier in ("debats.converti.json", "alias_orateurs.json"):
        source = CORPUS_EXEMPLE / fichier
        if source.exists():
            shutil.copy(source, corpus / fichier)
    return replace(
        Config(),
        embedder="dummy",
        corpus_dir=corpus,
        normalise_dir=tmp_path / "normalise",
        enfants_path=tmp_path / "enfants.jsonl",
        parents_path=tmp_path / "seances.jsonl",
        cache_path=tmp_path / "cache.jsonl",
        eval_dir=tmp_path / "eval",
        **surcharge,
    )


def qdrant_injoignable() -> bool:
    url = urlparse(os.environ.get("ATELIER_QDRANT_URL", "http://localhost:6333"))
    try:
        with socket.create_connection((url.hostname, url.port or 6333), timeout=0.5):
            return False
    except OSError:
        return True


@pytest.fixture()
def client_qdrant():
    """Client Qdrant, ou test sauté si le service ou le client manquent."""
    pytest.importorskip("qdrant_client")
    if qdrant_injoignable():
        pytest.skip("Qdrant injoignable — lancer « docker compose up -d »")
    from qdrant_client import QdrantClient

    url = os.environ.get("ATELIER_QDRANT_URL", "http://localhost:6333")
    client = QdrantClient(url=url)
    yield client
    try:
        client.delete_collection(collection_name="atelier_test")
    except Exception:
        pass


@pytest.fixture()
def config_test(tmp_path):
    return replace(config_sandbox(tmp_path), collection="atelier_test")
