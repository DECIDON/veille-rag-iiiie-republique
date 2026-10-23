"""Étape 5 — recherche hybride, rerank et restitution du parent (leçons 0003-0005).

L'entonnoir suit la veille (§6.2 et §8) : deux bras prefetch (dense + sparse,
filtrés par payload), fusion RRF (native Qdrant côté serveur, ou locale via
``atelier.fusion``), rerank cross-encoder sur les seuls ~20 premiers candidats
(bge-reranker-v2-m3, Apache-2.0, CPU), puis restitution du parent séance (leçon
0002) pour que l'intervention citée ne soit pas isolée de son contexte.
"""
from __future__ import annotations

from pathlib import Path

from .fusion import rrf
from .normalisation import lire_jsonl


def construire_filtre(filtres: dict):
    """Dictionnaire simple → ``Filter`` Qdrant (pré-filtrage documentaire).

    Clés reconnues : ``chambre``, ``orateur``, ``from``/``to`` (dates incluses,
    ``YYYY-MM-DD``), ``session``.
    """
    from qdrant_client.models import (
        DatetimeRange,
        FieldCondition,
        Filter,
        MatchValue,
    )

    conditions = []
    if "chambre" in filtres:
        conditions.append(FieldCondition(key="chambre", match=MatchValue(value=filtres["chambre"])))
    if "orateur" in filtres:
        conditions.append(FieldCondition(key="orateur", match=MatchValue(value=filtres["orateur"])))
    if "session" in filtres:
        conditions.append(FieldCondition(key="session", match=MatchValue(value=str(filtres["session"]))))
    if "from" in filtres or "to" in filtres:
        conditions.append(FieldCondition(
            key="date",
            range=DatetimeRange(gte=filtres.get("from"), lte=filtres.get("to")),
        ))
    return Filter(must=conditions) if conditions else None


def _requete_bras(quest_id: str, question: str, embedder, config, filtre):
    """Construit un ``Prefetch`` (dense ou sparse) pour le bras ``quest_id``."""
    from qdrant_client.models import Prefetch

    if quest_id == "dense":
        vecteur = embedder.encode_dense([question])[0]
        return Prefetch(
            query=vecteur, using="dense", limit=config.top_prefetch, filter=filtre,
        )
    from qdrant_client.models import SparseVector

    plonges = embedder.encode_sparse([question])[0]
    return Prefetch(
        query=SparseVector(indices=list(map(int, plonges)), values=list(plonges.values())),
        using="sparse", limit=config.top_prefetch, filter=filtre,
    )


def recherche_hybride(question: str, embedder, config, client,
                      filtres: dict | None = None, fusion: str = "serveur"):
    """Retourne la liste ordonnée de payloads fusionnés (avant rerank)."""
    from qdrant_client.models import Fusion, FusionQuery

    filtre = construire_filtre(filtres or {})
    bras = [_requete_bras(n, question, embedder, config, filtre) for n in ("dense", "sparse")]

    if fusion == "serveur":
        reponse = client.query_points(
            collection_name=config.collection,
            prefetch=bras,
            query=FusionQuery(fusion=Fusion.RRF),
            limit=config.top_fusion,
            with_payload=True,
        )
        return [p.payload for p in reponse.points]

    # Fusion locale : deux ANN séparées puis RRF côté client (atelier.fusion).
    classements, payloads = [], {}
    for bras_q in bras:
        reponse = client.query_points(
            collection_name=config.collection,
            query=bras_q.query, using=bras_q.using,
            query_filter=filtre, limit=config.top_prefetch, with_payload=True,
        )
        classements.append([p.payload["chunk_id"] for p in reponse.points])
        for p in reponse.points:
            payloads[p.payload["chunk_id"]] = p.payload
    fusionnes = rrf(classements, k=config.rrf_k)
    return [payloads[d] for d, _ in fusionnes[:config.top_fusion]]


def reranker(question: str, candidats: list[dict], config, top_k: int | None = None,
             _modele=None) -> list[dict]:
    """Rerank cross-encoder sur les candidats fusionnés ; tri par score rerank."""
    from sentence_transformers import CrossEncoder

    modele = _modele or CrossEncoder(config.reranker, device="cpu")
    paires = [(question, c["texte"]) for c in candidats]
    scores = modele.predict(paires)
    classes = sorted(zip(candidats, scores), key=lambda cs: -cs[1])
    final = []
    for candidat, score in classes:
        copie = dict(candidat)
        copie["score_rerank"] = float(score)
        final.append(copie)
    return final[:top_k or config.top_rerank]


def charger_parents(chemin: Path) -> dict[str, dict]:
    if not Path(chemin).exists():
        return {}
    return {p["id"]: p for p in lire_jsonl(chemin)}


def restituer_parents(resultats: list[dict], parents: dict[str, dict]) -> list[dict]:
    """Attache le parent (séance reconstituée) à chaque résultat, sans le dupliquer."""
    for resultat in resultats:
        resultat["parent"] = parents.get(resultat.get("parent_id") or "")
    return resultats


def afficher(resultats: list[dict]) -> str:
    """Mise en forme texte d'une réponse « retrieval-first » (veille §8 CPU)."""
    lignes: list[str] = []
    for rang, r in enumerate(resultats, start=1):
        extrait = " ".join(r["texte"].split())
        if len(extrait) > 320:
            extrait = extrait[:320] + "…"
        lignes.append(
            f"{rang}. {r['orateur']} — {r['chambre']}, {r['date']}, "
            f"page JO {r['page_jo']} [{r['chunk_id']}]"
        )
        if r.get("titre_parent"):
            lignes.append(f"   sous « {r['titre_parent']} »")
        lignes.append(f"   « {extrait} »")
        score = r.get("score_rerank")
        lignes.append(f"   rerank : {score:+.3f}" if score is not None else "")
        parent = r.get("parent")
        if parent:
            lignes.append(
                f"   parent : {parent['id']} "
                f"({len(parent['interventions'])} interventions reconstituées)"
            )
    return "\n".join(l for l in lignes if l)
