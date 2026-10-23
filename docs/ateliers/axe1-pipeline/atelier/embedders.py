"""Étape 3 — encodage dense **et** sparse des granulats (leçon 0003).

Le modèle de référence est ``BAAI/bge-m3`` (MIT, 568 M) : il fournit d'une
part les vecteurs denses de 1 024 dimensions (sens, paraphrase), d'autre part
les vecteurs sparse appris (pondérations lexicales, façon BM25 appris) — la
veille retient précisément ce double usage, qui rend l'hybride possible sans
moteur lexical séparé, sur CPU, via ``sentence-transformers``.

Le second encodeur, ``DummyEmbedder``, n'a aucune valeur sémantique : sac de
mots déterministe (hash de tokens). Il sert uniquement à tester la plomberie
(cache, indexation, fusion) sans télécharger deux gigaoctets de poids, et aux
tests d'intégration. Ne jamais l'employer pour une mesure de qualité.
"""
from __future__ import annotations

import hashlib
import math
import re

_MOTS = re.compile(r"[0-9a-zà-ÿ]+")


class DummyEmbedder:
    """Emballeur lexical déterministe, hors-ligne, pour tests et smoke tests."""

    nom = "dummy"
    dim = 1024

    @staticmethod
    def _mots(texte: str) -> list[str]:
        return _MOTS.findall(texte.lower())

    @staticmethod
    def _hachage(mot: str) -> int:
        return int.from_bytes(
            hashlib.blake2b(mot.encode("utf-8"), digest_size=8).digest(), "big",
        )

    def encode_dense(self, textes: list[str]) -> list[list[float]]:
        vecteurs = []
        for texte in textes:
            v = [0.0] * self.dim
            for mot in self._mots(texte):
                h = self._hachage(mot)
                v[h % self.dim] += 1.0 if (h >> 63) else -1.0
            norme = math.sqrt(sum(c * c for c in v)) or 1.0
            vecteurs.append([c / norme for c in v])
        return vecteurs

    def encode_sparse(self, textes: list[str]) -> list[dict[int, float]]:
        vectors = []
        for texte in textes:
            v: dict[int, float] = {}
            for mot in self._mots(texte):
                indice = self._hachage(mot) % (2 ** 31)
                v[indice] = v.get(indice, 0.0) + 1.0
            vectors.append(v)
        return vectors


class BgeM3Embedder:
    """bge-m3 via sentence-transformers : dense (1 024 d) + sparse appris."""

    nom = "bge-m3"
    dim = 1024
    MODELE = "BAAI/bge-m3"

    def __init__(self, device: str | None = None) -> None:
        # Import différé : les tests unitaires n'ont ni torch ni la modèle.
        from sentence_transformers import SentenceTransformer, SparseTextEmbeddingModel

        self._dense = SentenceTransformer(self.MODELE, device=device)
        self._sparse = SparseTextEmbeddingModel(self.MODELE, device=device)

    def encode_dense(self, textes: list[str], batch_size: int = 16) -> list[list[float]]:
        vecteurs = self._dense.encode(
            list(textes), batch_size=batch_size, show_progress_bar=False,
        )
        return [[float(x) for x in v] for v in vecteurs]

    def encode_sparse(self, textes: list[str], batch_size: int = 16) -> list[dict[int, float]]:
        plonges = self._sparse.encode(
            list(textes), batch_size=batch_size, show_progress_bar=False,
        )
        return [
            {int(k): float(w) for k, w in plong.items() if w > 0.0}
            for plong in plonges
        ]


def creer(nom: str, device: str | None = None):
    """Fabrique l'encodeur demandé (``bge-m3`` ou ``dummy``)."""
    if nom == "dummy":
        return DummyEmbedder()
    if nom == "bge-m3":
        return BgeM3Embedder(device=device)
    raise ValueError(f"encodeur inconnu : {nom!r} (attendu « bge-m3 » ou « dummy »)")
