"""Étape 4 — indexation Qdrant (leçon 0004).

Un cache local (``data/vecteurs/cache.jsonl``) conserve les vecteurs déjà
calculés, clef par clef (empreinte encodeur+texte) : l'encodage est la partie
chère de la chaîne, et un batch d'indexation doit être idempotent et
repreneable (veille, §7 : « script Python idempotent en shards »).

Qdrant reçoit deux vecteurs nommés par point : ``dense`` (1 024 d, cosinus,
quantifiée int8 — la division par 4 de la mémoire, §4 de la veille) et
``sparse`` (les poids lexicaux de bge-m3). Les métadonnées de filtrage
(chambre, date, orateur, parent) portent un index de payload pour que le
pré-filtrage soit efficace.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from pathlib import Path

from .normalisation import lire_jsonl

NAMESPACE_POINT = uuid.uuid5(uuid.NAMESPACE_URL, "atelier-axe1-jo-debats")


def point_id(chunk_id: str) -> str:
    """Identifiant de point déterministe (UUID v5) → re-indexation idempotente."""
    return str(uuid.uuid5(NAMESPACE_POINT, chunk_id))


def _sparse_brut(plonges: dict[str, float]) -> dict:
    indices, valeurs = [], []
    for clef, poids in plonges.items():
        indices.append(int(clef))
        valeurs.append(float(poids))
    return {"indices": indices, "values": valeurs}


def _empreinte(texte: str, nom_encodeur: str) -> str:
    return hashlib.sha256(f"{nom_encodeur}\x00{texte}".encode("utf-8")).hexdigest()


def charger_cache(chemin: Path) -> dict[str, dict]:
    chemin = Path(chemin)
    if not chemin.exists():
        return {}
    cache = {}
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        if ligne.strip():
            entree = json.loads(ligne)
            cache[entree["id"]] = entree
    return cache


def etape3_encoder(config, embedder=None) -> int:
    """Étape 3 : calcule et met en cache les vecteurs manquants des enfants."""
    from . import embedders as _emb

    enfants = lire_jsonl(config.enfants_path)
    embedder = embedder or _emb.creer(config.embedder)
    cache = charger_cache(config.cache_path)

    a_encoder = [
        e for e in enfants
        if cache.get(e["id"], {}).get("empreinte")
        != _empreinte(e["texte"], embedder.nom)
    ]
    for debut in range(0, len(a_encoder), config.batch):
        morceau = a_encoder[debut:debut + config.batch]
        textes = [e["texte"] for e in morceau]
        denses = embedder.encode_dense(textes)
        sparse = embedder.encode_sparse(textes)
        for enfant, dense, plong in zip(morceau, denses, sparse):
            cache[enfant["id"]] = {
                "id": enfant["id"],
                "empreinte": _empreinte(enfant["texte"], embedder.nom),
                "dense": dense,
                "sparse": {str(k): float(v) for k, v in plong.items()},
            }
        print(f"encodé {min(debut + config.batch, len(a_encoder))}/{len(a_encoder)}")

    config.cache_path.parent.mkdir(parents=True, exist_ok=True)
    with config.cache_path.open("w", encoding="utf-8") as flux:
        for entree in cache.values():
            flux.write(json.dumps(entree, ensure_ascii=False) + "\n")
    return len(a_encoder)


def creer_collection(client, config, effacer: bool = False) -> None:
    """Crée (ou recrée) la collection : dense cosinus quantifié int8 + sparse."""
    from qdrant_client.models import (
        DatetimeIndexParams,
        DatetimeIndexType,
        Distance,
        KeywordIndexParams,
        KeywordIndexType,
        ScalarQuantization,
        ScalarQuantizationConfig,
        ScalarType,
        SparseVectorParams,
        VectorParams,
    )

    existantes = {c.name for c in client.get_collections().collections}
    if config.collection in existantes and effacer:
        client.delete_collection(collection_name=config.collection)
        existantes.discard(config.collection)
    if config.collection not in existantes:
        client.create_collection(
            collection_name=config.collection,
            vectors_config={
                # cosinus : les embeddings bge-m3 sont comparés en angle.
                "dense": VectorParams(size=config.dim, distance=Distance.COSINE),
            },
            sparse_vectors_config={"sparse": SparseVectorParams()},
            # leçon 0004 : la quantification scalaire int8 divise la mémoire par 4
            quantization_config=ScalarQuantization(
                scalar=ScalarQuantizationConfig(type=ScalarType.INT8),
            ),
        )
    for champ in ("chambre", "orateur", "parent_id", "session"):
        client.create_payload_index(
            collection_name=config.collection,
            field_name=champ,
            field_schema=KeywordIndexParams(type=KeywordIndexType.KEYWORD),
        )
    client.create_payload_index(
        collection_name=config.collection,
        field_name="date",
        field_schema=DatetimeIndexParams(type=DatetimeIndexType.DATETIME),
    )


def _payload(enfant: dict) -> dict:
    return {
        "chunk_id": enfant["id"],
        "intervention_id": enfant["intervention_id"],
        "parent_id": enfant["parent_id"],
        "date": enfant["date"],
        "chambre": enfant["chambre"],
        "session": enfant["session"],
        "seance": enfant["seance"],
        "orateur": enfant["orateur"],
        "orateur_brut": enfant["orateur_brut"],
        "role": enfant.get("role"),
        "groupe": enfant.get("groupe"),
        "résumé": enfant.get("résumé"),
        "page_jo": enfant["page_jo"],
        "chunk_index": enfant["chunk_index"],
        "chunk_total": enfant["chunk_total"],
        "texte": enfant["texte"],
    }


def etape4_indexer(config, client=None) -> int:
    """Étape 4 : envoie les points (cache de vecteurs + payload) vers Qdrant."""
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, SparseVector

    client = client or QdrantClient(url=config.qdrant_url)
    creer_collection(client, config)

    enfants = lire_jsonl(config.enfants_path)
    cache = charger_cache(config.cache_path)
    manquants = [e["id"] for e in enfants if e["id"] not in cache]
    if manquants:
        raise RuntimeError(
            f"{len(manquants)} granulats sans vecteurs en cache — lancer d'abord « encoder »"
        )

    points = [
        PointStruct(
            id=point_id(enfant["id"]),
            vector={
                "dense": cache[enfant["id"]]["dense"],
                "sparse": SparseVector(**_sparse_brut(cache[enfant["id"]]["sparse"])),
            },
            payload=_payload(enfant),
        )
        for enfant in enfants
    ]
    taille_lot = 128
    for debut in range(0, len(points), taille_lot):
        client.upsert(
            collection_name=config.collection,
            points=points[debut:debut + taille_lot],
            wait=True,
        )
        print(f"indexé {min(debut + taille_lot, len(points))}/{len(points)}")
    return len(points)
