# Atelier axe 1 — commandes usuelles. `make` sans argument affiche l'aide.
PY ?= .venv/bin/python

.PHONY: help venv up down test test-complet smoke pipeline eval demo clean

help:
	@echo "make venv           — créer .venv et installer requirements.txt"
	@echo "make up             — démarrer Qdrant (docker compose up -d)"
	@echo "make test           — tests unitaires (hors-ligne, aucun modèle)"
	@echo "make test-complet   — + tests d'intégration (Qdrant requis)"
	@echo "make smoke          — pipeline complet hors-ligne (encodeur dummy)"
	@echo "make pipeline       — pipeline réel bge-m3 (1re passe : ~2 Go de poids)"
	@echo "make eval           — recall@k et MRR sur data/questions/QUERIES.md"
	@echo "make down           — arrêter Qdrant"

venv:
	python3 -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

up:
	docker compose up -d

down:
	docker compose down -v

test:
	$(PY) -m pytest

test-complet:
	$(PY) -m pytest -m "not modele and not reseau"

smoke: up
	ATELIER_EMBEDDER=dummy $(PY) -m atelier normaliser
	ATELIER_EMBEDDER=dummy $(PY) -m atelier chunker
	ATELIER_EMBEDDER=dummy $(PY) -m atelier encoder
	ATELIER_EMBEDDER=dummy $(PY) -m atelier indexer
	ATELIER_EMBEDDER=dummy $(PY) -m atelier rechercher "budget ecole primaire" --no-rerank
	ATELIER_EMBEDDER=dummy $(PY) -m atelier evaluer --no-rerank

pipeline:
	$(PY) -m atelier normaliser
	$(PY) -m atelier chunker
	$(PY) -m atelier encoder
	$(PY) -m atelier indexer

eval:
	$(PY) -m atelier evaluer

clean:
	rm -rf data/normalise data/enfants data/parents data/vecteurs data/eval
