"""Atelier pratique — axe 1 de la veille RAG « débats de la IIIᵉ République ».

Le paquet implémente le pipeline de référence de la variante CPU de la veille
(axe1-donnees.md §8) : normalisation → découpage par intervention → encodage
bge-m3 (dense + sparse) → indexation Qdrant quantifiée → recherche hybride
fusionnée RRF → rerank → (bonus) génération via Ollama.

Chaque module correspond à une étape de l'atelier (leçon 0012) et possède son
fichier de test dans ``tests/``.
"""

__version__ = "0.1"
