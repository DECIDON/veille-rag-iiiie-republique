# Synthèse — Veille technologique : interroger un grand corpus texte (RAG)

**Projet** : interface de consultation web auto-hébergée pour interroger en langage naturel les transcriptions OCR des débats parlementaires de la IIIᵉ République (dizaines de Go), public mixte (chercheurs + grand public), primat à l'open source, scénarios GPU et CPU-only.

**Date de la veille : 21 octobre 2026.** Méthode : sources primaires exclusivement (dépôts Git + fichiers LICENSE bruts, documentations officielles, cartes de modèles, arXiv, API Gallica/BnF, journaux officiels des données). Deux rapports détaillés complètent cette synthèse :

- [axe1-donnees.md](axe1-donnees.md) — pipeline de bout en bout : post-OCR → chunking → embeddings → base vectorielle → rerank → génération.
- [axe2-interface-web.md](axe2-interface-web.md) — plateformes RAG prêtes à l'emploi, interfaces sur mesure, serving, licences.
- Matériaux annexes (session parallèle, non reproduits ici) : deep-dive Sampo-UI / EclaiRAGe / précédents parlementaires / fiabilité text-to-SQL **et** sources du corpus (Gallica, IIIF, volumétrie) — conclusions reprises §5, identifiées comme telles.

---

## 1. Réponse courte

**Il n'existe aucune solution open source « tout-en-un » qui réunisse** : index externe en lecture seule + facettes déterministes (date, chambre, orateur) + citations avec lien vers la page source + LLM 100 % local. Les plateformes clés en main obligent à recopier le corpus dans leur propre index ; les moteurs de recherche facetée n'ont pas de RAG. Le projet passe donc par un **assemblage de briques permissives** (MIT/Apache-2.0/BSD), toutes vérifiées.

## 2. Stack de référence (100 % open source, licences permissives)

| Fonction | Composant retenu | Licence | Alternative |
|---|---|---|---|
| Structuration post-OCR | Normalisation Python maison → JSON canonique par intervention (métadonnées date/chambre/orateur/page JO) | — | Docling (chunking structurel) |
| Chunking | **Par intervention**, récupération parent-séance (LlamaIndex `AutoMergingRetriever` / LangChain `ParentDocumentRetriever`) | MIT | Docling `HierarchicalChunker` |
| Embeddings FR | CPU : **bge-m3** (dense+sparse+colbert intégrés, 568 M) ; GPU : **Qwen3-Embedding** (0,6→8 B, n°1 MTEB multilingue) | MIT / Apache-2.0 | multilingual-e5, gte, arctic-embed |
| Base de recherche | **Qdrant** (hybride dense+sparse, filtres payload, quantification ×4/×32) ou **PostgreSQL+pgvector** (facettes SQL, jointures) | Apache-2.0 / PostgreSQL | **OpenSearch** (Apache-2.0) si facettes analytiques lourdes |
| Rerank | **bge-reranker-v2-m3** (CPU) / **Qwen3-Reranker** (GPU) | Apache-2.0 | gte-reranker |
| Serving LLM | **Ollama** (dév/CPU) → **vLLM** (prod, API OpenAI-compatible) | MIT / Apache-2.0 | llama.cpp, TEI (Apache-2.0) |
| Génération | **Qwen3** (0,6–8 B denses ; MoE 30B-A3B = meilleur compromis CPU ; Apache-2.0) | Apache-2.0 | Mistral Small 3.2 / Nemo (Apache-2.0) |
| Interface | **Chainlit** (française, Apache-2.0, OIDC, affichage des sources) ou front **Next.js** ; POC rapide : **RAGFlow** (Apache-2.0) | Apache-2.0 | Kotaemon (citations chercheurs), Onyx CE (MIT) |
| Provenance | **arK Gallica + API IIIF BnF** (deep links page source), schémas de métadonnées AN/Sénat | — | visualiseur Mirador/Universal Viewer |

**Écartés pour licence** (politique OSS stricte) : Elasticsearch (SSPL/Elastic-2.0, AGPL en option seulement), Llama/Gemma (licences non-OSI), Jina embeddings/rerankers (CC-BY-NC), Mistral Embed & Cohere (API fermées), Morphik (BSL), Dify/FastGPT/LobeChat (Apache-2.0 *avec conditions* multi-tenant/logo), Open WebUI (clause de marque non OSI déclenchée dès 50 utilisateurs/30 j — quasi sûr pour un service public).

## 3. Axe 1 — Mise en place des données (résumé)

- **Pas d'outil dédié aux débats du XIXᵉ** : normalisation Python (accents, apostrophes, artefacts OCR) + format JSON canonique *par intervention*, avec `text_brut` (pour BM25 et l'authenticité des citations) **et** `text_normalise` (pour l'embedding), orateurs unifiés par dictionnaires d'alias.
- **Chunking par intervention** supérieur aux chunkings « sémantiques » : frontières documentairement vraies, orateur = métadonnée. Restitution de la séance entière au moment de la réponse (parent-document).
- **Embeddings** : seuls des poids ouverts permissifs et forts en français (MTEB/MMTEB/MTEB-French) ; bge-m3 fournit dense **et** sparse dans un seul modèle MIT → hybride sans moteur séparé, faisable CPU (~1–3 Go RAM).
- **Bases** : ~30 Go de texte ≈ ~15 M chunks ≈ ~60 Go de vecteurs bruts → **quantifiés** (int8 ×4) ≈ 15 Go : une machine 64 Go suffit. Qdrant, pgvector ou OpenSearch selon le besoin de facettes.
- **Architecture** : socle **hybride BM25/sparse + vector + rerank** (indispensable sur OCR bruité et noms propres) ; parent-document ; GraphRAG et RAPTOR en options GPU seulement (coût LLM sur tout le corpus) ; évaluation interne sur ~200 Q&R annotées, seul juge fiable hors distribution.
- **Batch d'indexation** : script Python idempotent shardé (les frameworks RAG n'apportent rien au batch) ; plusieurs jours de calcul CPU, acceptable (offline).

## 4. Axe 2 — Interface de consultation (résumé)

- **Clés en main, shortlist** : RAGFlow (Apache-2.0, pur, citations traçables, OCR/layout sur CPU, README en français, 16 Go RAM mini) ; Kotaemon (Apache-2.0, citations avec PDF surligné — idéal chercheurs, maintenance en ralentissement) ; Onyx CE (MIT mais SSO/RBAC en version payante ; ré-indexe tout chez lui) ; AnythingLLM (MIT, simple, pauvre en citations) ; Open WebUI (excellent chat + branchement sur index vectoriel externe Qdrant/Milvus/pgvector, **mais clause de marque non OSI** >50 utilisateurs → test uniquement). Morts ou détournés : Verba (archivé), Quivr (pivot hors-RAG), R2R (**dernier commit 07/11/2025, vérifié**), Morphik (BSL).
- **Gap confirmé** : aucune plateforme ne prend un **index externe en lecture seule** avec facettes. Moteur de facettes = agrégations **déterministes** de l'index (OpenSearch `aggs` ou SQL), jamais text-to-SQL ni LLM (taux d'erreur annotateur jusqu'à 62,8 % sur les benchmarks officiels, arXiv 2601.08778).
- **UI retenue** : Chainlit pour livrer vite (auth OIDC, éléments « sources », traduction FR) ; bascule Next.js quand l'UX facettée devient critique ; UI facettée sur base **Searchkit** (Apache-2.0) si piste OpenSearch.
- **Provenance, motif central** : chaque chunk porte cote + tome + page + **arK Gallica** ; chaque réponse cite verbatim avec lien profond `gallica.bnf.fr/ark:/…` et vue IIIF. C'est ce qui distingue un outil scientifique d'un jouet de démo.
- **Text-to-SQL** en complément seulement (comptages « combien de discours de Jaurès en 1904 ? ») : Vanna (MIT) ou WrenAI (Apache-2.0) sur les tables Postgres, avec affichage du SQL généré.
- **AGPL** : juridiquement compatible d'un service public (Khoj, Neo4j CE, option AGPL d'Elastic) mais impose de garder toute modification publiquement redistribuable → préférer le permissif sur le chemin critique.

## 5. Matériau annexe (session parallèle — conclusions à recouper au prochain sprint)

Reçu en cours de veille d'un autre agent de recherche (rapport `/tmp/opencode/veille/axe-B-interfaces.md`, sources primaires datées du 21/10/2026) :

- **Sampo-UI** (Aalto, MIT) : portail sémantique facetté sur endpoint SPARQL — **pas un RAG, aucun LLM** ; le papier « Sampo multi-field hybrid RAG » cité par ailleurs **n'existe pas** (vérifications arXiv/OpenAlex/GitHub négatives). Mais **ParliamentSampo** (débats finlandais → Parla-CLARIN → RDF → portail MIT) est le **précédent direct** de notre sujet ; excellent réservoir de patterns (facettes déclaratives, perspectives multiples, lecture seule par construction).
- **EclaiRAGe** (Huma-Num, MIT, Streamlit+Chroma+Ollama, Zenodo+HAL+*Humanités numériques* 2025) : gabarit éditorial français à répliquer (publication + code + hébergement souverain), pas une fondation (upload uniquement, zéro facette).
- **Précédents parlementaires** : *NosDéputés* (AGPL, patterns deep links), *EU Parliament Monitor* (Apache-2.0 + **serveur MCP read-only** — motif transposable : exposer l'index au LLM en lecture seule), *SansadSearch* (Inde, 2026 : facettes orateur/date/session + retour source — le plus proche du cahier des charges UI).
- **Recommandation convergeante** : facettes/comptages déterministes sur index unique (OpenSearch), UI facettée maison (Searchkit), chat branché sur les permalinks — ce que la synthèse indépendante ci-dessus retient aussi.

### Sources du corpus (même session, rapport `/tmp/opencode/veille/axe-A-sources.md`, 21–22/10/2026)

Même si l'OCR est acquis, ce rapport fiabilise la couche provenance et le dimensionnement :

- **Séries Gallica confirmées** (SPARQL `data.bnf.fr`) : JO Débats **Chambre 1881–1940** (ARK cb328020951) et **Sénat 1880–1940** (ARK cb34363182v) — **domaine public**, réutilisation libre hors usage contractuel, mention « source : BnF ». Lacune 1870–1880 (début des séries). Aucun dump massif de la JO distribué par la BnF.
- **Chaîne d'ingestion de référence** : Puren et al. 2025 (*Digital Scholarship & Humanities*) — 10 418 pages Chambre 1889–1893 téléchargées via l'**API IIIF `api.bnf.fr`**, pipeline layout → Tesseract → déshyphen → TEI, deep links par page (`…/ark:/12148/bpt6k…/f569.item`) : modèle direct pour notre maillage arK ↔ page OCR.
- **Volumétrie** : 14 législatures, ~10–12 k pages/législature ⇒ Chambre + Sénat ≈ **250–350 k pages** (extrapolation) ; **MVP recommandé : 1 législature** (1889–1893, terrain d'évaluation déjà publié).
- **Post-OCR** : aucun modèle public de post-correction OCR français n'existe — stratégie validée : index tolérant au bruit + **correction LLM ciblée sur les pages chaudes**, seule exception documentée : mémoire Féral 2025 (LLM sur les Tables des noms du Sénat IIIe).
- **Précédents réutilisables** : `common-pile/uk_hansard` (débats UK 1803–1944, même époque, licence permissive — corpus de test transverse) ; AGRorIdA (topic modeling JO). 10 hypothèses [H] restent à retester hors réseau filtré (PONTEX, RetroNews, périmètre IIIe de data.senat.fr/AN, People's Assembly, PARLLEARN, etc.).

## 6. Décisions recommandées

1. **Phase 0 (quelques jours)** : échantillon d'**une législature (1889–1893 recommandé**, précédent Puren = terrain d'évaluation direct, ~10 k pages) → pipeline complet variante CPU (bge-m3 + Qdrant quantifié + rerank + Chainlit + Ollama Qwen3-4B) ; mesurer latence, qualité de retrieval, dimensionnement réel.
2. **Phase 1** : service de provenance (arK Gallica ↔ pages OCR) et modèle de données JSON canonique avant toute indexation à pleine échelle — c'est le actif non regenerable.
3. **Phase 2** : arbitrage rendu public — (a) tour de chauffe RAGFlow/Chainlit vs (b) service stable Next.js/OpenSearch ; garde-fou licence : rien de non-permissif sur le chemin critique.
4. **Avec GPU** : Qwen3-Embedding-8B + Qwen3-Reranker-8B + vLLM (Qwen3-30B-A3B) ; options RAPTOR/GraphRAG sur sous-corpus ; sinon **UX retrieval-first** (extraits surlignés, mode « sans LLM »).
5. **Évaluation** : 200 Q&R annotées en interne (recall@k, nDCG) + audit OCR-orthographe → refonte d'alias si besoin, avant tout benchmark interne.

## 7. Vigilances

- Licences à surveiller dans le temps : Onyx (`ee/`), LiteLLM (`enterprise/`), WrenAI (modules AGPL annoncés), Open WebUI (clause de marque), Dify/FastGPT (multi-tenant).
- Les volumétries (§3, axe1 §4) sont des extrapolations linéaires à recalibrer sur échantillon.
- Points non tranchés (annexe) : People's Assembly/TheyWorkForMe injoignables le 21/10 ; statut exact d'archivage de Verba et react-search-ui (API GitHub limitée ce jour) ; validité du balisage Parla-CLARIN pour un JO français XIXᵉ vs TEI ; **10 hypothèses [H] du rapport sources à retester sur réseau non filtré** (PONTEX, RetroNews, périmètre IIIe des open data AN/Sénat, lacune 1870–1880, People's Assembly/PARLLEARN, UniOCR/Kraken).
