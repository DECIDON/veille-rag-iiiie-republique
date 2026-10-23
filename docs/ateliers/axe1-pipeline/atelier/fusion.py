"""Fusion RRF (Reciprocal Rank Fusion) implémentée côté client (leçon 0005).

Qdrant sait fusionner lui-même les bras de recherche prefetch (paramètre
``fusion`` de l'API query). Cette implémentation Python sert de *seam* : elle
rend le mécanisme testable unitairement, documente la formule (la veille §6.2 :
« leurs scores étant incomparables, la fusion RRF les combine par le rang »),
et permet de fusionner un troisième bras (par exemple un BM25 Lucène
d'OpenSearch) plus tard, sans toucher au moteur.

    score(doc) = Σ  1 / (k + rang(source, doc))      k = 60 par convention
"""
from __future__ import annotations


def rrf(classements: list[list[str]], k: int = 60) -> list[tuple[str, float]]:
    """Fusionne des classements (listes d'identifiants, du mieux noté au moins
    bien noté) et retourne ``[(id, score_rrf), …]`` trié par score décroissant."""
    scores: dict[str, float] = {}
    for classement in classements:
        for rang, doc_id in enumerate(classement, start=1):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rang)
    return sorted(scores.items(), key=lambda kv: (-kv[1], kv[0]))
