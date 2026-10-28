"""Configuration centrale de l'atelier — tous les chemins et tous les réglages.

Les variables d'environnement ``ATELIER_*`` et ``OLLAMA_*`` ont priorité sur les
valeurs par défaut ; elles ne sont lues qu'à un seul endroit, dans ``charger()``,
pour que le reste du code ne dépende que d'un objet ``Config`` immutable.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field, replace
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
DATA = RACINE / "data"


@dataclass(frozen=True)
class Config:
    # --- services externes -------------------------------------------------
    qdrant_url: str = "http://localhost:6333"
    collection: str = "jo_debats"
    embedder: str = "bge-m3"  # "bge-m3" (référence) ou "dummy" (plomberie, hors-ligne)
    reranker: str = "BAAI/bge-reranker-v2-m3"
    ollama_url: str = "http://localhost:11434"
    # qwen3:4b-instruct (hybride, raisonnement désactivable) et non qwen3:4b :
    # ce dernier tag sert aujourd'hui la variante « Thinking 2507 » dont le
    # raisonnement est inarrêtable → minutes de latence invisible sur CPU.
    ollama_model: str = "qwen3:4b-instruct"
    ollama_max_tokens: int = 500     # borne la réponse (et le raisonnement)
    ollama_num_ctx: int = 8192       # 3 enfants de ~1 200 tokens + marge

    # --- dimensions du pipeline -------------------------------------------
    dim: int = 1024               # dimension des vecteurs denses de bge-m3
    max_tokens_chunk: int = 1200  # étape 2 : taille maximale d'un granulat
    top_prefetch: int = 50        # étape 5 : candidats par bras avant fusion
    top_fusion: int = 20          # étape 5 : candidats retenus après fusion RRF
    top_rerank: int = 5           # étapes 5-6 : nombre de résultats finaux
    rrf_k: int = 60               # constante k de la fusion RRF (leçon 0005)
    batch: int = 16               # étape 3 : textes par passe d'encodage

    # --- chemins ------------------------------------------------------------
    corpus_dir: Path = field(default_factory=lambda: DATA / "corpus")
    normalise_dir: Path = field(default_factory=lambda: DATA / "normalise")
    enfants_path: Path = field(default_factory=lambda: DATA / "enfants" / "enfants.jsonl")
    parents_path: Path = field(default_factory=lambda: DATA / "parents" / "seances.jsonl")
    cache_path: Path = field(default_factory=lambda: DATA / "vecteurs" / "cache.jsonl")
    questions_path: Path = field(default_factory=lambda: DATA / "questions" / "QUERIES.md")
    eval_dir: Path = field(default_factory=lambda: DATA / "eval")


def charger() -> Config:
    """Construit la configuration en appliquant les variables d'environnement."""
    def _chemin(var: str, defaut: Path) -> Path:
        valeur = os.environ.get(var)
        return Path(valeur) if valeur else defaut

    defauts = Config()
    return replace(
        defauts,
        qdrant_url=os.environ.get("ATELIER_QDRANT_URL", defauts.qdrant_url),
        collection=os.environ.get("ATELIER_COLLECTION", defauts.collection),
        embedder=os.environ.get("ATELIER_EMBEDDER", defauts.embedder),
        reranker=os.environ.get("ATELIER_RERANKER", defauts.reranker),
        ollama_url=os.environ.get("OLLAMA_URL", defauts.ollama_url),
        ollama_model=os.environ.get("OLLAMA_MODEL", defauts.ollama_model),
        corpus_dir=_chemin("ATELIER_CORPUS", defauts.corpus_dir),
        normalise_dir=_chemin("ATELIER_NORMALISE", defauts.normalise_dir),
        questions_path=_chemin("ATELIER_QUESTIONS", defauts.questions_path),
    )
