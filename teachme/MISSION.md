# Mission : comprendre les notions techniques derrière la veille RAG « débats de la IIIᵉ République »

## Why
Le projet doit arbitrer une stack RAG open source (axe 1 : données, axe 2 : interface web) devant des pairs — chercheurs et service public. Pour défendre ces choix en réunion de sprint et détecter les mauvaises surprises, il faut maîtriser les notions sous-jacentes, pas seulement lire la synthèse.

## Success looks like
- Savoir expliquer de bout en bout le pipeline de l'axe 1 : post-OCR → chunking → embeddings → base vectorielle → hybridation → rerank → génération, et justiquer chaque brique retenue/écartée.
- Savoir expliquer les notions de l'axe 2 : plateformes turnkey vs stack composée, provenance (arK/IIIF), facettes déterministes vs text-to-SQL, pièges de licences.
- Être capable de critiquer une dimension (les ~15 M chunks / ~60 Go de vecteurs) et de recalculer le chiffre sur un échantillon.
- Recommander l'arbitrage GPU vs CPU-only en connaissance de cause (latence, quantification, MoE).

## Constraints
- Deux axes imposés comme hiérarchie du cours : Axe 1 — données ; Axe 2 — interface web.
- Tout est ancré sur la veille existante (`../axe1-donnees.md`, `../axe2-interface-web.md`, `../SYNTHESE.md`) et ses sources primaires ; langue d'apprentissage : français.
- Leçons courtes (≤ 15 min chacune), une notion = une leçon.

## Out of scope
- L'OCR elle-même (hors périmètre de la veille).
- L'entraînement ou le fine-tuning de modèles de poids.
- Les hypothèses [H] de l'annexe « sources » encore à retester (PONTEX, périmètre IIIᵉ des open data, etc.).
