# Atelier axe 1 — le pipeline complet, du texte OCR à la recherche hybride

Kit d'exécution de la **leçon 0012** (`../../lessons/0012-atelier-pipeline-complet.html`).
Il implémente la variante CPU du pipeline de référence de la veille
(`../../axe1-donnees.md` §8), en Python, avec les briques retenues :

| Étape | Leçon | Brique retenue | Module |
|---|---|---|---|
| 1 Normaliser | [0001](../../lessons/0001-postocr-normalisation.html) | Python pur (NFKD, alias) | `atelier/normalisation.py` |
| 2 Découper | [0002](../../lessons/0002-chunking-parent-document.html) | par intervention + parent séance | `atelier/chunking.py` |
| 3 Encoder | [0003](../../lessons/0003-embeddings-dense-sparse.html) | **BAAI/bge-m3** (MIT), dense+sparse, CPU | `atelier/embedders.py` |
| 4 Indexer | [0004](../../lessons/0004-bases-vectorielles-quantification.html) | **Qdrant** (Apache-2.0), int8 + sparse | `atelier/indexation.py` |
| 5 Rechercher | [0005](../../lessons/0005-retrieval-hybride-rerank.html) | hybride RRF + **bge-reranker-v2-m3** | `atelier/recherche.py`, `atelier/fusion.py` |
| 6 Évaluer | [0005](../../lessons/0005-retrieval-hybride-rerank.html) | recall@k + MRR sur Q&R annotées | `atelier/evaluation.py` |
| 7 Générer (bonus) | [0006](../../lessons/0006-serving-llm-cpu.html) | **Ollama** (MIT) + Qwen3-4B, API OpenAI | `atelier/generation.py` |

## Démarrage rapide

Prérequis : [uv](https://docs.astral.sh/uv/installation/) (Python ≥ 3.10 est
installé et géré par uv au besoin) et Docker pour Qdrant.

```bash
cd docs/ateliers/axe1-pipeline
make setup         # uv sync : .venv + dépendances verrouillées (uv.lock)
make up            # Qdrant mono-nœud (docker)
make test          # tests unitaires — doivent passer sans Qdrant ni modèle
make smoke         # pipeline complet hors-ligne (encodeur dummy) sur exemple.json
make pipeline      # pipeline réel bge-m3 (télécharge ~2 Go de poids la 1re fois)
make eval          # recall@k / MRR sur data/questions/QUERIES.md
```

Toutes les commandes Python passent par `uv run` (ou `source .venv/bin/activate`) ;
les dépendances et leurs licences sont déclarées dans `pyproject.toml`, l'état
exact installé dans `uv.lock`.

## Étapes, commandes et vérification

Chaque étape a (1) une commande de mise en place, (2) un fichier de test
`pytest` dédié, (3) une vérification visuelle de votre côté. Le détail
pédagogique est dans la leçon 0012.

| Étape | Mise en place | Test | Vérification attendue |
|---|---|---|---|
| 1 | `uv run python -m atelier normaliser` | `uv run -m pytest tests/test_01_normalisation.py` | 5 lignes JSONL, `text_brut` intact + `text_normalise` |
| 2 | `uv run python -m atelier chunker` | `uv run -m pytest tests/test_02_chunking.py` | 5 enfants, 2 parents (séances) |
| 3 | `uv run python -m atelier encoder` | `uv run -m pytest tests/test_03_encodage.py` | cache `data/vecteurs/cache.jsonl`, relance ⇒ 0 recalcul |
| 4 | `uv run python -m atelier indexer` | `uv run -m pytest tests/test_04_indexation.py` (integration) | collection `jo_debats`, 5 points, dashboard Qdrant |
| 5 | `uv run python -m atelier rechercher "budget ecole primaire"` | `uv run -m pytest tests/test_05_recherche.py` | top-1 = l'intervention Ferry, parent cité |
| 6 | `uv run python -m atelier evaluer` | `uv run -m pytest tests/test_06_evaluation.py` | recall@5 et MRR affichés |
| 7 | `uv run python -m atelier generer "…"` (Ollama requis) | `uv run -m pytest tests/test_07_generation.py` | réponse citant les `page_jo` |

## Le corpus

Le contrat d'entrée (format JSON par intervention) est décrit dans
[`data/corpus/README.md`](data/corpus/README.md). Un mini-corpus de 5
interventions fictives (`data/corpus/exemple.json`) permet de tout tester avant
de déposer vos données réelles ; le jeu de questions d'évaluation se remplit
dans [`data/questions/QUERIES.md`](data/questions/QUERIES.md).

Vos exports bruts se déposent dans `data/corpus/brut/` et se convertissent avec
`uv run python outils/adaptateur_debats.py --chambre … --date …` — le détail du
mapping est dans [`data/corpus/README.md`](data/corpus/README.md), règle 5.

## Réglages (variables d'environnement)

| Variable | Défaut | Rôle |
|---|---|---|
| `ATELIER_QDRANT_URL` | `http://localhost:6333` | service Qdrant |
| `ATELIER_COLLECTION` | `jo_debats` | collection |
| `ATELIER_EMBEDDER` | `bge-m3` | `dummy` = plomberie hors-ligne (jamais pour mesurer) |
| `ATELIER_RERANKER` | `BAAI/bge-reranker-v2-m3` | cross-encoder d'étage final |
| `OLLAMA_URL` / `OLLAMA_MODEL` | `http://localhost:11434` / `qwen3:4b` | bonus 7 |

## Tests

```bash
make test           # unitaires : stdlib seule, aucun service requis
make test-complet   # + intégration : Qdrant démarré (docker compose up -d)
uv run -m pytest -m modele    # contrat des vrais poids bge-m3 (~2 Go)
uv run -m pytest -m reseau    # appel réel à Ollama (bonus 7)
```

## Passage GPU (quand vient le GPU)

Le pipeline change deux constantes et rien d'autre : encodeur
`Qwen/Qwen3-Embedding-8B` (servi par TEI ou vLLM, dimensions tronquées à 1 024
par MRL) et reranker `Qwen/Qwen3-Reranker-8B`. Voir leçon 0011 pour chiffrer
cet enrichissement avant de l'acheter.
