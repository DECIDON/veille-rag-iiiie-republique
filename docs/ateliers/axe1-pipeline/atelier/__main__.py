"""Interface en ligne de commande de l'atelier (leçon 0012).

Usage : ``python -m atelier <commande>`` depuis le répertoire de l'atelier.
Commandes : normaliser, chunker, encoder, indexer, rechercher, evaluer, generer.
"""
from __future__ import annotations

import argparse
import sys

from . import config as _config


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m atelier", description=__doc__)
    sous = parser.add_subparsers(dest="commande")

    sous.add_parser("normaliser", help="étape 1 — corpus JSON → interventions normalisées")
    sous.add_parser("chunker", help="étape 2 — interventions → enfants + parents")
    sous.add_parser("encoder", help="étape 3 — enfants → vecteurs dense+sparse (cache)")
    sous.add_parser("indexer", help="étape 4 — cache → Qdrant (création + upsert)")

    p_rech = sous.add_parser("rechercher", help="étape 5 — recherche hybride + rerank")
    p_rech.add_argument("question")
    p_rech.add_argument("--chambre")
    p_rech.add_argument("--orateur")
    p_rech.add_argument("--from", dest="from_", help="date minimale YYYY-MM-DD")
    p_rech.add_argument("--to", help="date maximale YYYY-MM-DD")
    p_rech.add_argument("--session")
    p_rech.add_argument("--fusion", choices=("serveur", "locale"), default="serveur")
    p_rech.add_argument("--no-rerank", action="store_true")

    p_eval = sous.add_parser("evaluer", help="étape 6 — recall@k et MRR sur QUERIES.md")
    p_eval.add_argument("--k", type=int, default=5)
    p_eval.add_argument("--no-rerank", action="store_true")

    p_gen = sous.add_parser("generer", help="étape 7 (bonus) — synthèse LLM citée")
    p_gen.add_argument("question")
    p_gen.add_argument("--k", type=int, default=3)

    args = parser.parse_args(argv)
    if not args.commande:
        parser.print_help()
        return 1

    config = _config.charger()

    if args.commande == "normaliser":
        from . import normalisation
        n = normalisation.etape1(config)
        print(f"{n} interventions normalisées → {config.normalise_dir}/interventions.jsonl")
        return 0

    if args.commande == "chunker":
        from . import chunking
        n_e, n_p = chunking.etape2(config)
        print(f"{n_e} enfants → {config.enfants_path}")
        print(f"{n_p} parents (séances) → {config.parents_path}")
        return 0

    if args.commande == "encoder":
        from . import indexation
        n = indexation.etape3_encoder(config)
        print(f"{n} vecteurs calculés, cache → {config.cache_path}")
        return 0

    if args.commande == "indexer":
        from . import indexation
        n = indexation.etape4_indexer(config)
        print(f"{n} points upsertés dans la collection « {config.collection} »")
        return 0

    if args.commande == "rechercher":
        from . import recherche
        return _rechercher(config, args, recherche)

    if args.commande == "evaluer":
        from . import evaluation
        return _evaluer(config, args, evaluation)

    if args.commande == "generer":
        from . import recherche
        return _generer(config, args, recherche)

    return 1


def _filtres(args) -> dict:
    filtres = {}
    if getattr(args, "chambre", None):
        filtres["chambre"] = args.chambre
    if getattr(args, "orateur", None):
        filtres["orateur"] = args.orateur
    if getattr(args, "from_", None):
        filtres["from"] = args.from_
    if getattr(args, "to", None):
        filtres["to"] = args.to
    if getattr(args, "session", None):
        filtres["session"] = args.session
    return filtres


def _rechercher(config, args, recherche) -> int:
    from qdrant_client import QdrantClient
    from . import embedders

    encodeur = embedders.creer(config.embedder)
    client = QdrantClient(url=config.qdrant_url)
    candidats = recherche.recherche_hybride(
        args.question, encodeur, config, client, filtres=_filtres(args),
        fusion=args.fusion,
    )
    if not candidats:
        print("aucun candidat — collection vide ? lancer « encoder » puis « indexer ».")
        return 1
    if args.no_rerank:
        resultats = candidats[:config.top_rerank]
    else:
        resultats = recherche.reranker(args.question, candidats, config)
    resultats = recherche.restituer_parents(
        resultats, recherche.charger_parents(config.parents_path),
    )
    print(recherche.afficher(resultats))
    return 0


def _evaluer(config, args, evaluation) -> int:
    questions = evaluation.parser_queries(config.questions_path)
    if not questions:
        print(f"aucune question exploitable dans {config.questions_path}")
        return 1

    from . import embedders, recherche
    from qdrant_client import QdrantClient

    encodeur = embedders.creer(config.embedder)
    client = QdrantClient(url=config.qdrant_url)
    modele_rerank = None  # un seul chargement du cross-encoder pour toute la session

    def recuperer(q, texte: str) -> list[str]:
        nonlocal modele_rerank
        candidats = recherche.recherche_hybride(
            texte, encodeur, config, client, filtres=q.filtres,
        )
        if args.no_rerank:
            final = candidats[:args.k]
        else:
            if modele_rerank is None:
                from sentence_transformers import CrossEncoder
                modele_rerank = CrossEncoder(config.reranker, device="cpu")
            final = recherche.reranker(
                texte, candidats, config, top_k=args.k, _modele=modele_rerank,
            )
        return [r["intervention_id"] for r in final]

    bilan = evaluation.evaluer_compare(questions, recuperer)
    for ligne in bilan["detail"]:
        reel = f"rappel={ligne['reel']['rappel']:.0f} rang={ligne['reel']['premier_rang']:.2f}"
        if ligne["oracle"]:
            suite = (f" | oracle : rappel={ligne['oracle']['rappel']:.0f} "
                     f"rang={ligne['oracle']['premier_rang']:.2f}")
        else:
            suite = " | oracle : —"
        print(f"  {ligne['id']:<6} réel : {reel}{suite}")
    reel, oracle = bilan["reel"], bilan["oracle"]
    print(f"questions : {reel['nb_questions']} — "
          f"réel : recall@{args.k} {reel['recall']:.2f}, MRR {reel['mrr']:.2f}", end="")
    if oracle:
        print(f" — oracle ({oracle['nb_questions']} q.) : "
              f"recall@{args.k} {oracle['recall']:.2f}, MRR {oracle['mrr']:.2f} — "
              f"écart : {bilan['ecart']['recall']:+.2f} / {bilan['ecart']['mrr']:+.2f}")
    else:
        print()
    return 0


def _generer(config, args, recherche) -> int:
    from . import embedders, generation
    from qdrant_client import QdrantClient

    encodeur = embedders.creer(config.embedder)
    client = QdrantClient(url=config.qdrant_url)
    candidats = recherche.recherche_hybride(args.question, encodeur, config, client)
    resultats = recherche.reranker(args.question, candidats, config, top_k=args.k)
    reponse = generation.generer(args.question, resultats, config)
    print(reponse)
    print("\n— sources —")
    for r in resultats:
        print(f"  [{r['intervention_id']}] {r['orateur']}, page JO {r['page_jo']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
