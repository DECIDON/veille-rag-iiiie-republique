# Veille technologique — Axe 1 : la « face données » d'un RAG sur les débats parlementaires de la IIIᵉ République

> Périmètre : pipeline de bout en bout depuis du **texte OCR déjà produit** (Journal officiel, dizaines de Go de texte brut) jusqu'à un corpus interrogeable (indexation + recherche + génération), en environnement **auto-hébergé et open source**, avec couvrant les deux scénarios **GPU** et **CPU seul**. L'OCR elle-même est hors périmètre ; le nettoyage post-OCR est dans le périmètre.
>
> Méthode : toutes les affirmations techniques (licences, tailles de modèles, fonctionnalités) ont été vérifiées fin 2026 sur les **sources primaires** (dépôts GitHub, cartes de modèles Hugging Face, documentations officielles, arXiv). Les URLs sont citées en ligne et reprises en fin de document.

---

## 1. Pré-traitement et structuration du texte post-OCR

### 1.1 Outils de structuration de documents

| Outil | Licence | Intérêt pour le projet | Limites |
|---|---|---|---|
| **Docling** (docling-project, projet hébergé à la LF AI & Data Foundation, initié par IBM Research Zurich) | **MIT** | Convertit une grande variété de formats (dont **texte brut `.txt`/`.text` et Markdown**) en une représentation unifiée `DoclingDocument` (JSON sans perte) avec titres, structure, provenance ; exports Markdown/HTML/JSON ; **chunkers natifs** (voir §2) qui portent les métadonnées (chemin de titres, numéros de page) ; export des *chunks* directement depuis le CLI et le serveur API (`docling-serve`) ; exécutable en air-gapped. ([repo](https://github.com/docling-project/docling), [rapport technique arXiv 2408.09869](https://arxiv.org/abs/2408.09869), [doc chunking](https://docling-project.github.io/docling/concepts/chunking/), [API server](https://docling-project.github.io/docling/usage/api_server/)) | L'extraction de métadonnées riches (titre, auteurs, langue) est annoncée « coming soon » ; pour du texte OCR brut, c'est surtout le **modèle de document + chunking + sérialisation** qui est utile, pas le parsing de mise en page. |
| **Apache Tika** | **Apache-2.0** | Moteur Java historique d'extraction de texte et de **métadonnées embarquées** sur des centaines de formats ; serveur Tika ; détection automatique de type. ([tika.apache.org](https://tika.apache.org/)) | Orienté « formats de fichiers », pas « structuration sémantique » ; moins adapté si tout est déjà en texte plat ; surcoût d'exploitation (JVM). |
| **Unstructured** (Unstructured-IO/unstructured) | **Apache-2.0** (LICENSE.md du dépôt) | Bibliothèque Python `partition()` qui transforme documents en éléments structurés (titres, narratif, tables…) avec des métadonnées, et module `chunking` ; extras d'installation par type de document. ([repo](https://github.com/Unstructured-IO/unstructured), [LICENSE.md](https://github.com/Unstructured-IO/unstructured/blob/main/LICENSE.md), [PyPI](https://pypi.org/project/unstructured/)) | Empilement de dépendances lourdes ; la partie « enrichissements » avancés est poussée vers leur plateforme payante ; pour du texte déjà plat, l'apport est faible par rapport à Docling. |
| **trafilatura** (adbar/trafilatura) | **Apache-2.0** | Extracteur de **contenu principal** type readability (familles readability/boilerpipe) : pertinent si vous re-téléchargez les pages HTML du JO pour constitution du corpus, pour éliminer navigation/boilerplate. ([repo](https://github.com/adbar/trafilatura)) | Inutile si le corpus OCR est déjà du texte pur. |

**Constat important (et honnête) :** pour des **transcriptions de débats en texte brut avec structure propre au JO** (analyse de la séance, noms des orateurs, interventions), il n'existe **pas d'outil open source dédié tout fait**. La pratique recommandée est un **étage de normalisation maison** (Python, regex + `str.normalize('NFKD')`, gestion des accents, unification des apostrophes typographiques, suppression des artefacts OCR) qui produit un **format JSON intermédiaire canonique** par intervention :

```json
{
  "id": "senat-1885-06-14-s001-i042",
  "date": "1885-06-14", "chambre": "senat", "session": "1885", "seance": "1", "ordre_du_jour": ["..."],
  "orateur": {"nom": "Victor Hugo", "role": null, "groupe": null},
  "titre_parent": "Suite de la discussion du budget…",
  "text_brut": "…", "text_normalise": "…",
  "page_jo": 612
}
```

- Les variantes orthographiques du XIXᵉ s., les noms d'orateurs (citoyens/ministres présidents…) se traitent par **règles + dictionnaires d'alias** (nom canonique ↔ graphies observées), stockés comme métadonnées filtrables — pas par un modèle.
- Le choix crucial : **ne jamais écraser le texte original** ; stocker `text_brut` (pour BM25 et l'authenticité des citations) + `text_normalise` (pour l'embedding), comme le permettent les colonnes multiples (PostgreSQL) ou les champs nommés multiples (Qdrant, OpenSearch).

### 1.2 Métadonnées et filtrage hybride

Toutes les bases du marché permettent de **filtrer avant/après similarité vectorielle** sur des métadonnées structurées — c'est LE moyen de restreindre une requête à « Chambre des députés, années 1880-1900, orateur X » :

- **Qdrant** : métadonnées = *payload* JSON indexé, filtrage avant/après ANN documenté ([concepts/payload](https://qdrant.tech/documentation/concepts/payload/)).
- **OpenSearch/Elastic** : filtres booléens Lucène natifs sur les champs (date, mot-clé).
- **PostgreSQL/pgvector** : n'importe quel filtre SQL, index B-tree/GIN combinés au scan vectoriel ; les *iterative index scans* du README pgvector ciblent précisément le problème « ANN + WHERE restrictif » ([README](https://github.com/pgvector/pgvector/blob/master/README.md)).
- **Weaviate** : filtres structurés par propriété, tokenisation configurable par propriété (dont gestion des stopwords/accents — utile pour le français) ([docs BM25](https://docs.weaviate.io/weaviate/search/bm25)).

---

## 2. Stratégies de découpage (chunking) pour textes de débats

Ce que les frameworks supportent **réellement** (vérifié dans leurs docs) :

### Docling — chunking structurel
`docling.chunking` fournit deux chunkeurs ([docs](https://docling-project.github.io/docling/concepts/chunking/)) :
- **HierarchicalChunker** : un chunk par élément du document (paragraphe, liste, table…), **en conservant le chemin de titres et les légendes** comme métadonnées.
- **HybridChunker** : part du résultat hiérarchique puis **ajuste à la taille de tokens d'un tokenizer HuggingFace donné** (découpe les chunks trop gros, fusionne les petits voisins partageant les mêmes titres `merge_peers=True`) ; tables sérialisées, en-têtes de tables répétés. La méthode `contextualize()` prépare la chaîne « titres + texte » à passer à l'embedding.
C'est la brique la plus alignée avec un corpus de séances structurées (une séance = document, rubriques = titres).

### LlamaIndex (MIT) — parsers de nœuds
Docs : [module guide node parsers](https://developers.llamaindex.ai/python/framework/module_guides/loading/node_parsers/modules), [API reference](https://developers.llamaindex.ai/python/framework-api-reference/node_parsers/).
- `SentenceSplitter`, `TokenTextSplitter`, `MarkdownNodeParser` (split par en-têtes markdown, **chemin de titres stocké par nœud**), `HTMLNodeParser`, `JSONNodeParser`.
- **`SentenceWindowNodeParser`** : chunk = phrase, avec une **fenêtre de phrases voisines** conservée en métadonnées (récupérées au moment de la génération) — équivalent propre de l'approche « small-to-big » sans base séparée.
- **`SemanticSplitterNodeParser`** : regroupe les phrases sémantiquement liées (adaptateur de la méthode LangChain).
- **`HierarchicalNodeParser` + `AutoMergingRetriever`** : hiérarchie de tailles de chunks avec liens parent/enfant ; au retrieval, remplace les enfants majoritairement récupérés par leur **parent** (contexte complet). C'est la récupération « parent-document » de LlamaIndex ([guide](https://developers.llamaindex.ai/python/framework/module_guides/loading/node_parsers/modules)).

### LangChain / LangGraph (MIT)
- Package `langchain-text-splitters` : `MarkdownHeaderTextSplitter` (split par titres MD, titres → métadonnées), `HTMLHeaderTextSplitter` / `HTMLSectionSplitter`, `RecursiveCharacterTextSplitter`, `TokenTextSplitter`… ([reference](https://reference.langchain.com/python/langchain_text_splitters)).
- **`SemanticChunker`** (package `langchain-experimental`) : découpage par similarité d'embeddings (points de rupture par percentile/écart-type) ([reference](https://reference.langchain.com/v0.3/python/experimental/text_splitter/langchain_experimental.text_splitter.SemanticChunker.html)).
- **`ParentDocumentRetriever`** : indexe de **petits chunks** (embeddings plus précis) et restitue au retrieval les **documents parents** stockés dans un docstore — pattern documentaire officiel LangChain ([reference](https://reference.langchain.com/python/langchain-classic/retrievers/parent_document_retriever/ParentDocumentRetriever), [source](https://github.com/langchain-ai/langchain/blob/master/libs/langchain/langchain_classic/retrievers/parent_document_retriever.py)).

### Chunking tardif (late chunking)
- Papier : **« Late Chunking: Contextual Chunk Embeddings Using Long-Context Embedding Models »**, Günther et al. (Jina AI), [arXiv 2409.04701](https://arxiv.org/abs/2409.04701). Principe : encoder le **document entier** avec un modèle longue fenêtre, puis regrouper les embeddings de *tokens* par fenêtre de chunk → chaque embedding de chunk porte le contexte global. Économie : une seule passe d'encodage pour tout le document plutôt qu'une par chunk.
- Implémentation officielle : dépôt [jina-ai/late-chunking](https://github.com/jina-ai/late-chunking) (notebooks + code).
- ⚠️ Pour du **français ancien**, il faut un embedding longue fenêtre multilingue (ex. Qwen3-Embedding, 32 k tokens — cf. §4) ; les modèles d'origine de Jina (jina-embeddings-v3) sont sous **CC-BY-NC-4.0** (non commercial !) ([carte](https://huggingface.co/jinaai/jina-embeddings-v3)) → écartés d'office.

### Recommandation pour les débats
Le JO a une grammaire naturelle : **séance → question/ordre du jour → intervention (orateur)**. Le découpage **par intervention** (borné, ~500–2 000 tokens, sinon découpage intra-intervention) est supérieur aux chunkings « sémantiques » automatiques ici, parce que les frontières sont *documentairement* vraies et que l'orateur est une métadonnée. Hiérarchie conseillée : `intervention` (enfant, indexé) → `séance` (parent, restitué) — soit via parent-document retrieval (LangChain/LlamaIndex), soit en stockant `parent_id` en payload + restitution applicative.

**RAPTOR** (arbre récursif de résumés — [arXiv 2401.18059](https://arxiv.org/abs/2401.18059), [implémentation officielle MIT](https://github.com/parthsarthi03/raptor)) : séduisant pour des questions « panoramiques » (position d'un parti sur un thème sur 10 ans), mais son indexation **fait résumer tout le corpus par un LLM** — coût énorme sur des dizaines de Go, et résumés non vérifiables en citation directe. À réserver à un sous-corpus (discours célèbres) ou à une variante « résumés par séance générés une seule fois ».

---

## 3. Modèles d'embedding open weights avec bon niveau en français

**Référentiels d'évaluation :** MTEB ([papier 2210.07316](https://arxiv.org/abs/2210.07316), [leaderboard](https://leaderboard.mteb.org/)) ; MMTEB multilingue ([arXiv 2502.13595](https://arxiv.org/abs/2502.13595)) ; **MTEB-French** 25 tâches natives français ([papier 2405.20468](https://arxiv.org/abs/2405.20468), benchmark *MTEB(fra, v1)* sur [leaderboard.mteb.org](https://leaderboard.mteb.org/benchmark/MTEB(fra,%20v1)). Le papier F-MTEB confirme que les meilleurs multilingues (E5, BGE, e5-mistral) dominent, que des modèles français autochtones s'en approchent (Solon-embeddings-large, sentence_croissant, sentence-camembert), et que **mistral-embed et les modèles Cohere/OpenAI y sont en licence fermée** (tableau des modèles, « Closed source »).

### Candidats open weights vérifiés (tailles, licences, contexte)

| Modèle | Licence | Taille | Dim. | Contexte | Atouts FR / CPU |
|---|---|---|---|---|---|
| **Qwen3-Embedding 0.6B / 4B / 8B** | **Apache-2.0** | 0,6–8 B | 32→4 096 (MRL, dimension tronquable) | **32 768** | N°1 du leaderboard MTEB multilingue au 05/06/2025 (score 70,58 pour le 8B, selon la [carte](https://huggingface.co/Qwen/Qwen3-Embedding-8B)) ; instruct-aware ; **0,6B = unique option vraiment CPU** |
| **bge-m3** (BAAI) | **MIT** | 568 M | 1 024 | **8 192** | Tri-fonction dense **+ sparse (pondérations de type BM25) + ColBERT dans un seul modèle** → hybride sans moteur séparé ([carte](https://huggingface.co/BAAI/bge-m3)) ; ~#51 MTEB(Multilingual, v2) ; dérivé FR : [manu/bge-m3-custom-fr](https://huggingface.co/manu/bge-m3-custom-fr) |
| **multilingual-e5 small / base / large** (Intfloat) | **MIT** | 118 M / 278 M / 560 M | 384/768/1 024 | 512 | Très fort en FR (l'e5-large-instruct ≈ #27 MTEB(Multilingual, v2) à 63,22 sur [leaderboard.mteb.org](https://leaderboard.mteb.org/benchmark/MTEB(Multilingual,%20v2))) ; contexte court (512) = contrainte pour de longues interventions |
| **gte-multilingual-base** (Alibaba) | **Apache-2.0** | ~305 Mo de poids | 768 | 512 | ~#52 MTEB multilingue v2 ([carte](https://huggingface.co/Alibaba-NLP/gte-multilingual-base)) ; reranker homologue Apache-2.0 |
| **snowflake-arctic-embed m / l (+ v2)** | **Apache-2.0** | ~0,1–0,5 B | 1 024 | 512+ | Spécialisés retrieval multilingue, très utilisés (l-v2.0 : ~2,2 M téléchargements) ([carte](https://huggingface.co/Snowflake/snowflake-arctic-embed-l)) |
| **nomic-embed-text-v1** | **Apache-2.0** | ~137 M | 768 | 8 192 | Léger et longue fenêtre, mais **orienté anglais** ([carte](https://huggingface.co/nomic-ai/nomic-embed-text-v1)) |
| **e5-mistral-7b-instruct** (Intfloat) | **MIT** | 7,1 B | 4 096 | **32 768** | Excellent (table F-MTEB), mais **GPU requis** (28 Go fp16, GGUF 4-bit existe : second-state/E5-Mistral-…-GGUF) ([carte](https://huggingface.co/intfloat/e5-mistral-7b-instruct)) |
| Français purs : **Solon-embeddings-large-0.1** (MIT, GGUF dispo), **sentence_croissant_alpha_v0.4** (MIT) | MIT | ~1,3 B (croissant) | — | 512–1 k | Alternatives FR natives citées en tête du papier F-MTEB ([cartes](https://huggingface.co/OrdalieTech/Solon-embeddings-large-0.1), [carte](https://huggingface.co/manu/sentence_croissant_alpha_v0.4)) |
| **splade-camembert-base-v2** | **Apache-2.0** | ~0,3 B | — | 512 | Apprentissage lexical sparse **en français** : alternative neuronale à BM25 pour l'hybride ([carte](https://huggingface.co/sparse-encoder/splade-camembert-base-v2)) |

### API propriétaires (à écarter en « open source strict », citées pour comparaison)
- **Mistral Embed** : **API uniquement, poids fermés** ([docs.mistral.ai](https://docs.mistral.ai/studio/knowledge-rag/embeddings) ; confirmé « Closed source » dans le tableau du [papier F-MTEB](https://arxiv.org/abs/2405.20468)).
- **Cohere Embed v3/v4** : API non ouverte ; aucun poids d'embedding v4 public sur le hub CohereLabs ([docs](https://docs.cohere.com/reference/embed)).
- **Jina embeddings v3/v4** : poids publics mais **CC-BY-NC-4.0 (non commercial)** ([carte](https://huggingface.co/jinaai/jina-embeddings-v3)) → incompatible avec une politique OSS stricte.

### Faisabilité CPU
Un encodeur de ~0,3–0,6 B (bge-m3, e5-large, gte) tient dans **~1–3 Go de RAM** et s'exécute sur CPU via **sentence-transformers** (Apache-2.0, [repo](https://github.com/huggingface/sentence-transformers)) ou **TEI** (Text Embeddings Inference, **Apache-2.0**, serveur optimisé **CPU via Candle** et GPU, embeddings + rerankers, [repo](https://github.com/huggingface/text-embeddings-inference)). Pour indexer l'équivalent de dizaines de Go de texte, comptez des jours de calcul sur CPU (à paralléliser par shards de corpus) — c'est du batch offline, donc acceptable ; c'est la génération (§5) qui est le vrai goulot d'étranglement sur CPU.

---

## 4. Bases vectorielles / moteurs de recherche (dizaines de Go ≈ plusieurs millions de chunks)

| Base | Licence (vérifiée) | Échelle / distribué | Filtres métadonnées | Hybride BM25/lexical + vector | Embeddings sur CPU |
|---|---|---|---|---|---|
| **Qdrant** | **Apache-2.0** ([repo](https://github.com/qdrant/qdrant)) | Mono-nœud → **cluster distribué** ; écrit en Rust ; vecteurs **sur disque** + **quantification** (scalair ×4, binaire ×32) ([doc](https://qdrant.tech/documentation/quantization/)) | Payload JSON indexé, filtrage natif ([doc](https://qdrant.tech/documentation/concepts/payload/)) | **Oui** : dense + sparse (SPLADE, **bge-m3**, etc.) + fusion (RRF, DBSF) ([doc](https://qdrant.tech/documentation/concepts/hybrid-search/)) | Oui (client Python ; la base elle-même est indépendante du GPU) |
| **Weaviate** | **BSD-3-Clause** ([LICENSE](https://github.com/weaviate/weaviate/blob/main/LICENSE)) | Mono-binaire avec sharding/réplication Raft intégrés | Filtres typés par collection | **Oui natif** : BM25F + vector fusionnés (`relativeScoreFusion`/`rankedFusion`, `alpha`) ([doc](https://docs.weaviate.io/weaviate/search/hybrid)) | Oui (vecteurs apportés par le client — *bring-your-own vectors*) |
| **Milvus** | **Apache-2.0** ([repo](https://github.com/milvus-io/milvus)) | Cloud-native, pensée pour le **très grand** (README : scalability) | Filtres booléens sur scalaires | **Oui** : multi-champs vectoriels + `hybrid search` (RRF/pondéré) ([README](https://github.com/milvus-io/milvus/blob/master/README.md)) | Oui (BYO vectors) ; exploitation lourde (composants distribués) |
| **PostgreSQL + pgvector** | **PostgreSQL License** (BSD-like) ([LICENSE](https://github.com/pgvector/pgvector/blob/master/LICENSE)) | Mono-instance robuste ; extensions tierces : **pgvectorscale** (Timescale, **PostgreSQL License**) pour le scale-out | **SQL complet** (le plus souple : dates, jointures, facets) | Non natif ; via `tsvector/tsquery` (BM25-ish) ou extension BM25 dédiée ; sinon fusion applicative avec Qdrant/OpenSearch | Oui |
| **OpenSearch** | **Apache-2.0** (fork Linux Foundation d'Elasticsearch) ([repo](https://github.com/opensearch-project/opensearch)) | Distribué (nœuds, répliques), agrégations analytiques | Filtres booléens | **Oui** : BM25 (Lucène) + plugin **neural-search** (Apache-2.0) pour kNN/sparse neuronal, recherche hybride via pipelines (normalisation + **RRF**) ([plugin](https://github.com/opensearch-project/neural-search), [doc hybride](https://docs.opensearch.org/latest/search-plugins/neural-search/hybrid-search/)) | Oui |
| Elasticsearch | **triple licence AGPL-3.0 / SSPL-1.0 / Elastic-2.0** — *source-available*, **pas open source OSI** ([LICENSE.txt](https://github.com/elastic/elasticsearch/blob/main/LICENSE.txt)) | — | — | — | ❌ écarté par la politique OSS (préférer OpenSearch) |
| **LanceDB** | **Apache-2.0** (format colonne **Lance** + base intégrée) ([repo](https://github.com/lancedb/lancedb), [lance](https://github.com/lancedb/lance)) | **Embarquée** (in-process, comme DuckDB) ; versionnement de données, multimodal | Filtrage SQL-like sur colonnes | Recherche vectorielle + filtres ; lexical au cas par cas | Oui (Python/Rust, parfait pour poste CPU) |
| **Chroma** | **Apache-2.0** ([repo](https://github.com/chroma-core/chroma)) | Embarquée + **mode serveur** ; pensée pour prototypes à production légère | Métadonnées filtrables | Vector + mots-clés basiques (`where_document`) | Oui |
| **Typesense** | **GPL-3.0** ([repo](https://github.com/typesense/typesense)) | Distribué léger, typo-tolérance | Filtres facettes | Recherche texte ++ + champs vectoriels | Oui |

### Dimensionnement (règle de pouce pour Qdrant, à recalibrer)
Soit ~30 Go de texte ⇒ ~15 M chunks de ~2 ko. Avec **bge-m3 (1 024 d, fp32)** : 15 M × 4,1 Ko ≈ **60 Go de vecteurs bruts** ; en **int8 (quantification ×4)** ≈ 15 Go ; en **binaire (×32)** ≈ 2 Go + rescoring exact (doc quantification Qdrant ci-dessus). Le texte source lui-même (60 Go avec les index texte) vit sur disque — les deux scénarios tiennent sur une machine unique (64 Go RAM) **à condition de quantifier**.

---

## 5. Génération et reranking (LLM open weights + piles de service)

### Piles de service vérifiées
| Pile | Licence | GPU | CPU |
|---|---|---|---|
| **vLLM** | **Apache-2.0** ([repo](https://github.com/vllm-project/vllm)) | ✅ (le standard) | Backend CPU **documenté mais lent/limité** ([doc CPU](https://docs.vllm.ai/en/latest/getting_started/installation/cpu.html)) ; quantizations AWQ/GPTQ/FP8 ([doc quantization](https://docs.vllm.ai/en/latest/features/quantization/)) |
| **Ollama** | **MIT** ([repo](https://github.com/ollama/ollama)) | ✅ auto | ✅ (moteur llama.cpp sous le capot, GGUF ; poste de travail) |
| **llama.cpp** | **MIT** ([repo](https://github.com/ggml-org/llama.cpp)) | ✅ | ✅ CPU-first, format **GGUF** et ses quants (Q4_K_M…) |
| **TEI** (HF Text Embeddings Inference) | **Apache-2.0** ([repo](https://github.com/huggingface/text-embeddings-inference)) | ✅ | ✅ CPU (Candle) — recommandé pour **embeddings + rerankers** en service Docker |
| **TGI** (Text Generation Inference) | Apache-2.0 ([repo](https://github.com/huggingface/text-generation-inference)) | ✅ | limité — sur GPU, alternative à vLLM |

(*Text-Router* (awslabs) est une librairie de routage d'embeddings, pas une pile de service — hors sujet.*)

### Modèles génératifs (open weights, candidats crédibles)
- **Qwen3** : **Apache-2.0**, gammes denses 0,6B/4B/8B ([Qwen3-8B](https://huggingface.co/Qwen/Qwen3-8B), [Qwen3-4B](https://huggingface.co/Qwen/Qwen3-4B)) et **MoE Qwen3-30B-A3B** (30 B de paramètres, ~3 B actifs par token — [carte](https://huggingface.co/Qwen/Qwen3-30B-A3B)) : c'est le meilleur compromis qualité/CPU (le MoE ne « coûte » que ses 3 B actifs par token).
- **Mistral Small 3.2 (24B) Instruct** : **Apache-2.0** ([carte](https://huggingface.co/mistralai/Mistral-Small-3.2-24B-Instruct-2506)) ; **Mistral Nemo 12B Instruct** : **Apache-2.0** ([carte](https://huggingface.co/mistralai/Mistral-Nemo-Instruct-2407)). En revanche **Mistral « Large » n'est pas open weights** (API uniquement, cf. docs.mistral.ai).
- **Llama-3.1-8B** : **licence Llama 3.1 (community)** — *non OSI*, clauses d'usage et restrictions de marque à vérifier juridiquement ([carte](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct)).
- **Gemma-3 4B/12B** : **« Gemma Terms of Use »** (Google) — poids ouverts, licence **non OSI** ([carte](https://huggingface.co/google/gemma-3-12b-it)).

### Rerankers (cross-encoders) — étape décisive pour la précision
| Reranker | Licence | Taille | CPU ? |
|---|---|---|---|
| **Qwen3-Reranker 0.6B / 4B / 8B** | **Apache-2.0** | 0,6–8 B ([carte](https://huggingface.co/Qwen/Qwen3-Reranker-4B)) | le 0,6B oui |
| **bge-reranker-v2-m3** (BAAI) | **Apache-2.0** | 568 M, multilingue ([carte](https://huggingface.co/BAAI/bge-reranker-v2-m3)) | ✅ |
| **gte-multilingual-reranker-base** | **Apache-2.0** | ~300 Mo ([carte](https://huggingface.co/Alibaba-NLP/gte-multilingual-reranker-base)) | ✅ |
| monoT5 (castorini/monot5-*msmarco) | licence non déclarée (recherche) ; anglais dominant ([carte](https://huggingface.co/castorini/monot5-base-msmarco)) | base→3B | ❌ FR + licence |
| Jina reranker v2 multilingue | **CC-BY-NC-4.0** (non commercial) ([carte](https://huggingface.co/jinaai/jina-reranker-v2-base-multilingual)) | 278 M | ❌ licence |
| Cohere Rerank (API) | fermé | — | ❌ |

### Réalité CPU-only
- Encodage/reranking : **OK** (modèles ≤ 0,6 B).
- Génération : seule la bande **≤ 8 B quantifiée GGUF** est praticable. Ordre de grandeur mémoire : fp16 ≈ 2 o/paramètre → GGUF Q4 ≈ 0,5–0,6 o/paramètre, soit **~5 Go pour un 8B Q4_K_M** (llama.cpp/Ollama). Pour une UX acceptable sur CPU, viser **Qwen3-4B** (ou Qwen3-30B-A3B Q4 si la RAM ≥ 24 Go), ou une **UX « retrieval only »** (moteur de recherche + surlignage, sans reformulation LLM) — c'est l'option que nous recommandons en variante CPU (§8).

---

## 6. Architectures RAG pertinentes pour un corpus de débats historiques

1. **RAG vectoriel naïf** (embeddings → top-k → prompt) : simple, mais fragile sur corpus dense, vocabulaire ancien, et questions comptables (« combien de fois… », « discours de X sur Y en 1893 »). À éviter seul.
2. **Hybride BM25 + vector + rerank** — *le socle recommandé* : l'orthographe OCR et les noms propres (députés, ministries, lois) exigent du lexical (BM25/sparse neuronal FR = splade-camembert) ; fusion (RRF) puis rerank (bge-reranker-v2-m3) gagne nettement la précision sur corpus bruité. Support natif : Weaviate, Qdrant (sparse+bge-m3), OpenSearch (pipeline hybride).
3. **Parent-document / auto-merging** : indexer des interventions, restituer séance ou partie de séance — LangChain `ParentDocumentRetriever`, LlamaIndex `HierarchicalNodeParser`+`AutoMergingRetriever`, Docling hierarchical chunking. Essentiel ici : une intervention isolée perd le contexte du « fait personnel », de la riposte.
4. **RAPTOR** : arborescence de résumés multi-échelles — utile pour les *questions panoramiques* (thématiques, longitudinales) mais coût d'indexation LLM sur tout le corpus ([papier](https://arxiv.org/abs/2401.18059), [code MIT](https://github.com/parthsarthi03/raptor)).
5. **GraphRAG** : Microsoft [GraphRAG](https://github.com/microsoft/graphrag) (**MIT**, [papier « From Local to Global » 2404.16130](https://arxiv.org/abs/2404.16130)) extrait entités/relations par LLM puis résume les communautés pour répondre aux *questions globales*. Corpus **très riche en entités** (députés, ministères, commissions, projets de loi) = cas d'école ; **mais** coût d'extraction LLM sur tout le corpus, et qualité dépendante de l'OCR. Alternative pragmatique : **graphe entretenu par les données du JO elles-mêmes** (orateurs, scrutins, ministères, suites de débats = arêtes fiables à 100 %, sans LLM) + Neo4j (**Community Edition GPL-3.0**, [repo](https://github.com/neo4j/neo4j)) en magasin.
6. **Agentic RAG** (LangGraph/LlamaIndex agents) : réécriture de requêtes archaïsmes → recherche multiple → vérification de citations → synthèse multi-sauts (« qui a répondu à Jaurès sur… »). Ajouté par-dessus le socle hybride ; la vérification de citation (source + page) est un argument clé pour un corpus historique.
7. **Late chunking** : séduisant avec Qwen3-Embedding-8B (32 k) en **GPU**, mais bénéfice difficile à prouver sur des interventions déjà autonomes ; ne le prévoir qu'en option A/B test.

**Synthèse propre au corpus historique :** privilégier tout ce qui **préserve citation et datation** (chunk → page JO → séance), la recherche **facetable temporelle**, et une évaluation en interne (un panel de Q&R « terrain » sur échantillon de séances) plutôt que les scores de leaderboard.

---

## 7. Orchestration : LlamaIndex vs LangChain/LangGraph vs Haystack vs R2R vs txtai

| Framework | Licence | Maturité / points forts pour **l'indexation hors-ligne à grande échelle** |
|---|---|---|
| **LlamaIndex** | **MIT** ([repo](https://github.com/run-llama/llama_index)) | Abstraction « ingestion pipeline » (readers → node parsers → embedders → vector store) très adaptée au batch ; large éventail de chunkers (cf. §2) ; intégrations Docling/Qdrant/OpenSearch. |
| **LangChain (+ LangGraph)** | **MIT** ([repo](https://github.com/langchain-ai/langchain), [LangGraph low-level/stateful, MIT](https://github.com/langchain-ai/langgraph)) | Splitters + `ParentDocumentRetriever` solides ; LangGraph pour la couche agent (états, boucles, checkpointing) ; attention : l'observabilité « sérieuse » (LangSmith) est un produit commercial optionnel. |
| **Haystack** (deepset) | **Apache-2.0** ([repo](https://github.com/deepset-ai/haystack)) | Pipelines explicites (converters/cleaners → preprocessors → retrievers → rankers → generators) sérialisables, pensée production ; converters propres = bon endroit pour nos UDF FR. |
| **R2R** (SciPhi) | **MIT** ([repo](https://github.com/SciPhi-AI/R2R)) | Système « production-ready » complet (agentic RAG, API REST) avec Postgres + graphe en interne ; opinionated : plus difficile à prendre par petits morceaux. |
| **txtai** (NeuML) | **Apache-2.0** ([repo](https://github.com/neuml/txtai)) | Tout-en-un (base d'embeddings, workflows, pipelines, agents) avec bindings multi-langages ; communauté plus petite. |

**Recommandation d'architecture :** pour **l'indexation de dizaines de Go**, la meilleure « abstraction » est un **script Python idempotent en shards** (Docling pour la forme, sentence-transformers/TEI pour l'encodage, client de la base pour l'ingest, JSON canonique en entrée) — les frameworks de RAG n'apportent rien au *batch* et ajoutent des dépendances. Les réserver à la **couche interrogation** : LlamaIndex *ou* Haystack pour le pipeline RAG, LangGraph si l'on veut de l'agentique piloté par états.

---

## 8. Pipeline de référence recommandé

### Communs aux deux scénarios
1. **Normalisation** (Python pur) : shards de `.txt` → JSON canonique par intervention (§1.1), alias d'orateurs, `chambre/date/session/page_jo`.
2. **Chunking** : intervention = unité (Docling HierarchicalChunker sur les séance-Markdown reconstituées, ou splitter maison sur marqueurs d'orateur) ; `parent_id` = séance.
3. **Indexation hybride** : vecteurs denses + sparse (bge-m3 en mode dense **et** sparse dans Qdrant, ou BM25 dans OpenSearch/Weaviate) + filtres payload ; quantification int8 + disque.
4. **Retrieval** : hybride (RRF/weighted) → **rerank bge-reranker-v2-m3** (ou Qwen3-Reranker-8B en GPU) → restitution du parent (séance) avec citation `page_jo`.
5. **Évaluation** : ~200 Q&R annotés en interne (métriques recall@k / nDCG), refaite à chaque changement d'embeddings — seul juge fiable pour un corpus hors distribution.

### Variante CPU seul
```
texte OCR → normalisation Python → [Docling JSON / chunking intervention]
   → embeddings bge-m3 (sentence-transformers ou TEI-CPU)  [MIT/Apache-2.0]
   → sparse bge-m3 (mêmes vecteurs, pas de moteur séparé)
   → Qdrant mono-nœud (Apache-2.0, HNSW quantifié int8, vecteurs sur disque)
   → rerank CPU : bge-reranker-v2-m3 (Apache-2.0)
   → UX : recherche + surlignage + filtres (date/orateur/chambre), RETOURS
     génération LLM optionnelle : Qwen3-4B GGUF Q4 via Ollama (MIT, CPU)
```
Coût RAM : index quantifié ~15–20 Go + modèle ~2 Go → machine 32–64 Go OK. **Défaut recommandé : UX retrieval-only** (le LLM CPU n'apporte que de la reformulation, au prix d'une latence de dizaines de secondes).

### Variante GPU
```
(gain 1) embeddings Qwen3-Embedding-8B (Apache-2.0, 32k ctx, MRL→1024d pour le stockage) via TEI/vLLM
   — ou 4B/0.6B selon budget ; instruct « français du XIXᵉ s., discours parlementaire » (les cartes recommandent des instructions dédiées, +1 à 5 %)
(gain 2) rerank Qwen3-Reranker-8B (Apache-2.0) en vLLM
(gain 3) générateur vLLM (Apache-2.0) : Qwen3-30B-A3B ou Mistral Small 3.2-24B (Apache-2.0)
(option) GraphRAG (MIT) sur un sous-corpus enrichi en entités, ou graphe « natif JO » + Neo4j (GPL-3.0) pour l'analyse des réseaux de parole
(option) RAPTOR (MIT) par séance/année pour les questions panoramiques
(gain 4) A/B du late chunking (arXiv 2409.04701) si les embeddings 32k sont retenus
```
Base vectorielle identique (Qdrant, ou OpenSearch si l'on veut aussi agrégations/analyses de facettes sur le corpus). **Licences finales du stack : 100 % MIT/Apache-2.0/BSD/PostgreSQL** — aucun verrou AGPL/SSPL/CC-BY-NC.

### Points de vigilance
- **bge-m3** : le mode sparse est intégré ; si vous préférez du lexical *vrai*, prenez OpenSearch (BM25 Lucène + lemmatisation FR) ou Weaviate (attention : ses stopwords par défaut sont anglais, configurer le français).
- Les licences « Gemma » et « Llama community » **ne sont pas des licences open source OSI** : si la politique projet est stricte, tenez-vous à Qwen3/Mistral (Apache-2.0).
- Cohere/Mistral Embed/Jina : non retenus (fermés ou non commerciaux), cités ici pour mémoire.
- Les volumes exacts (dizaines de Go ⇒ millions de chunks) doit être mesurée sur échantillon avant achat de la machine : les chiffres §4 sont des extrapolations linéaires.

---

## Références (URLs citées)

**Structuration**
- https://github.com/docling-project/docling (Docling, MIT, LF AI & Data) · https://docling-project.github.io/docling/concepts/chunking/ · https://docling-project.github.io/docling/usage/api_server/ · https://arxiv.org/abs/2408.09869 (rapport technique)
- https://tika.apache.org/ (Apache Tika, Apache-2.0)
- https://github.com/Unstructured-IO/unstructured + https://github.com/Unstructured-IO/unstructured/blob/main/LICENSE.md (Apache-2.0) · https://pypi.org/project/unstructured/
- https://github.com/adbar/trafilatura (Apache-2.0)
- https://qdrant.tech/documentation/concepts/payload/ · https://docs.weaviate.io/weaviate/search/bm25 · https://github.com/pgvector/pgvector/blob/master/README.md

**Chunking**
- https://developers.llamaindex.ai/python/framework/module_guides/loading/node_parsers/modules · https://developers.llamaindex.ai/python/framework-api-reference/node_parsers/
- https://reference.langchain.com/python/langchain_text_splitters · https://reference.langchain.com/v0.3/python/experimental/text_splitter/langchain_experimental.text_splitter.SemanticChunker.html · https://reference.langchain.com/python/langchain-classic/retrievers/parent_document_retriever/ParentDocumentRetriever · https://github.com/langchain-ai/langchain/blob/master/libs/langchain/langchain_classic/retrievers/parent_document_retriever.py
- https://arxiv.org/abs/2409.04701 (Late Chunking) · https://github.com/jina-ai/late-chunking
- https://arxiv.org/abs/2401.18059 (RAPTOR) · https://github.com/parthsarthi03/raptor (MIT)

**Embeddings / benchmark**
- https://arxiv.org/abs/2210.07316 (MTEB) · https://leaderboard.mteb.org/ + https://huggingface.co/spaces/mteb/leaderboard · https://arxiv.org/abs/2502.13595 (MMTEB) · https://arxiv.org/abs/2405.20468 (MTEB-French) · https://leaderboard.mteb.org/benchmark/MTEB(fra,%20v1) · https://github.com/embedded-benchmarks/mteb
- https://huggingface.co/Qwen/Qwen3-Embedding-8B · https://huggingface.co/BAAI/bge-m3 · https://huggingface.co/manu/bge-m3-custom-fr · https://huggingface.co/intfloat/multilingual-e5-large (+ -small/-base, -large-instruct) · https://huggingface.co/Alibaba-NLP/gte-multilingual-base · https://huggingface.co/Alibaba-NLP/gte-multilingual-reranker-base · https://huggingface.co/Snowflake/snowflake-arctic-embed-l · https://huggingface.co/nomic-ai/nomic-embed-text-v1 · https://huggingface.co/intfloat/e5-mistral-7b-instruct · https://huggingface.co/OrdalieTech/Solon-embeddings-large-0.1 · https://huggingface.co/manu/sentence_croissant_alpha_v0.4 · https://huggingface.co/sparse-encoder/splade-camembert-base-v2
- API fermées : https://docs.mistral.ai/studio/knowledge-rag/embeddings · https://docs.cohere.com/reference/embed · https://huggingface.co/jinaai/jina-embeddings-v3 (CC-BY-NC)

**Bases / moteurs**
- https://github.com/qdrant/qdrant · https://qdrant.tech/documentation/concepts/hybrid-search/ · https://qdrant.tech/documentation/quantization/
- https://github.com/weaviate/weaviate (+ LICENSE BSD-3) · https://docs.weaviate.io/weaviate/search/hybrid
- https://github.com/milvus-io/milvus · https://milvus.io/docs/hybrid-search
- https://github.com/pgvector/pgvector (PostgreSQL License) · https://github.com/timescale/pgvectorscale (PostgreSQL License)
- https://github.com/opensearch-project/opensearch (Apache-2.0) · https://github.com/opensearch-project/neural-search (Apache-2.0) · https://docs.opensearch.org/latest/search-plugins/neural-search/hybrid-search/
- https://github.com/elastic/elasticsearch/blob/main/LICENSE.txt (AGPL/SSPL/Elastic-2.0)
- https://github.com/lancedb/lancedb · https://github.com/lancedb/lance (Apache-2.0)
- https://github.com/chroma-core/chroma (Apache-2.0) · https://github.com/typesense/typesense (GPL-3.0)

**LLM / rerankers / serving**
- https://github.com/vllm-project/vllm · https://docs.vllm.ai/en/latest/getting_started/installation/cpu.html · https://docs.vllm.ai/en/latest/features/quantization/
- https://github.com/ollama/ollama (MIT) · https://github.com/ggml-org/llama.cpp (MIT)
- https://github.com/huggingface/text-embeddings-inference (Apache-2.0, CPU/Candle) · https://github.com/huggingface/sentence-transformers (Apache-2.0)
- https://github.com/huggingface/text-generation-inference (Apache-2.0)
- https://huggingface.co/Qwen/Qwen3-8B · https://huggingface.co/Qwen/Qwen3-4B · https://huggingface.co/Qwen/Qwen3-30B-A3B · https://huggingface.co/Qwen/Qwen3-Reranker-4B (+0.6B/8B) · https://huggingface.co/BAAI/bge-reranker-v2-m3 · https://huggingface.co/mistralai/Mistral-Small-3.2-24B-Instruct-2506 · https://huggingface.co/mistralai/Mistral-Nemo-Instruct-2407 · https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct (licence Llama 3.1) · https://huggingface.co/google/gemma-3-12b-it (Gemma Terms)

**Architectures & orchestration**
- https://github.com/microsoft/graphrag (MIT) · https://arxiv.org/abs/2404.16130 · https://github.com/neo4j/neo4j (GPL-3.0)
- https://github.com/run-llama/llama_index (MIT) · https://github.com/langchain-ai/langchain (MIT) · https://github.com/langchain-ai/langgraph (MIT) · https://github.com/deepset-ai/haystack (Apache-2.0) · https://github.com/SciPhi-AI/R2R (MIT) · https://github.com/neuml/txtai (Apache-2.0)
