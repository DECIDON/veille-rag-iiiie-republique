# Atelier axe 1 — commandes usuelles. `make` sans argument affiche l'aide.
# Prérequis : uv (https://docs.astral.sh/uv/installation/) — il crée et gère .venv seul.
UV ?= uv

.PHONY: help setup up down test test-complet smoke pipeline eval demo clean

help:
	@echo "make setup          — créer .venv et installer les dépendances verrouillées (uv sync)"
	@echo "make up             — démarrer Qdrant (docker compose up -d)"
	@echo "make test           — tests unitaires (hors-ligne, aucun modèle)"
	@echo "make test-complet   — + tests d'intégration (Qdrant requis)"
	@echo "make smoke          — pipeline complet hors-ligne (encodeur dummy)"
	@echo "make pipeline       — pipeline réel bge-m3 (1re passe : ~2 Go de poids)"
	@echo "make eval           — recall@k et MRR sur data/questions/QUERIES.md"
	@echo "make down           — arrêter Qdrant"

setup:
	$(UV) sync

up:
	docker compose up -d

down:
	docker compose down -v

test:
	$(UV) run -m pytest

test-complet:
	$(UV) run -m pytest -m "not modele and not reseau"

smoke: up
	ATELIER_EMBEDDER=dummy $(UV) run python -m atelier normaliser
	ATELIER_EMBEDDER=dummy $(UV) run python -m atelier chunker
	ATELIER_EMBEDDER=dummy $(UV) run python -m atelier encoder
	ATELIER_EMBEDDER=dummy $(UV) run python -m atelier indexer
	ATELIER_EMBEDDER=dummy $(UV) run python -m atelier rechercher "budget ecole primaire" --no-rerank
	ATELIER_EMBEDDER=dummy $(UV) run python -m atelier evaluer --no-rerank

pipeline:
	$(UV) run python -m atelier normaliser
	$(UV) run python -m atelier chunker
	$(UV) run python -m atelier encoder
	$(UV) run python -m atelier indexer

eval:
	$(UV) run python -m atelier evaluer

clean:
	rm -rf data/normalise data/enfants data/parents data/vecteurs data/eval
