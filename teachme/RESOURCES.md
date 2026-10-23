# Ressources — RAG sur corpus parlementaire (IIIᵉ République)

Toujours privilégier ces sources primaires (la veille les a vérifiées le 21/10/2026). Les URLs proviennent des rapports de veille eux-mêmes.

## Connaissances (Knowledge)

### Point de départ
- [Veille interne : axe 1 — la face données](../axe1-donnees.md)
  Le pipeline complet, licences vérifiées. Use for : tout arbitrage d'indexation et de retrieval.
- [Veille interne : axe 2 — interface web](../axe2-interface-web.md)
  Plateformes, UI, serving, licences. Use for : choix du front et de la couche d'intégration.
- [Synthèse de veille](../README.md)
  Réponse courte + stack de référence + décisions recommandées. Use for : remettre une notion dans son contexte.

### Axe 1 — données
- [Docling — rapport technique (arXiv 2408.09869)](https://arxiv.org/abs/2408.09869) et [chunking](https://docling-project.github.io/docling/concepts/chunking/)
  Représentation JSON sans perte + chunkeurs hiérarchiques. Use for : structuration post-OCR, chunking structurel.
- [LangChain ParentDocumentRetriever (réf. officielle)](https://reference.langchain.com/python/langchain-classic/retrievers/parent_document_retriever/ParentDocumentRetriever) et [LlamaIndex node parsers](https://developers.llamaindex.ai/python/framework/module_guides/loading/node_parsers/modules)
  Use for : récupération parent-document (indexer fin, restituer large).
- [Late Chunking (arXiv 2409.04701)](https://arxiv.org/abs/2409.04701)
  Encoder le document entier puis découper les embeddings de tokens. Use for : option GPU, contexte global des chunks.
- [RAPTOR (arXiv 2401.18059)](https://arxiv.org/abs/2401.18059) et [GraphRAG (arXiv 2404.16130)](https://arxiv.org/abs/2404.16130)
  Use for : questions panoramiques/globales — et pour comprendre pourquoi la veille les réserve au GPU.
- [Carte bge-m3 (BAAI)](https://huggingface.co/BAAI/bge-m3)
  Dense + sparse + ColBERT dans un seul modèle MIT. Use for : compréhension hybride sans moteur séparé.
- [Carte Qwen3-Embedding-8B](https://huggingface.co/Qwen/Qwen3-Embedding-8B)
  32 k contexte, dimensions MRL tronquables, n°1 MTEB multilingue à sa sortie. Use for : variante GPU.
- [Leaderboard MTEB](https://leaderboard.mteb.org/) et [papier MTEB (2210.07316)](https://arxiv.org/abs/2210.07316), [MTEB-French (2405.20468)](https://arxiv.org/abs/2405.20468)
  Use for : choisir/justifier un modèle d'embedding francophone ; comprendre qu'un leaderboard ne juge pas un corpus hors distribution.
- [Qdrant — quantification](https://qdrant.tech/documentation/quantization/) et [payload/filtres](https://qdrant.tech/documentation/concepts/payload/)
  Use for : le calcul de dimensionnement ×4/×32 et le filtrage avant/après ANN.
- [OpenSearch neural-search (hybride + RRF)](https://docs.opensearch.org/latest/search-plugins/neural-search/hybrid-search/)
  Use for : comprendre BM25 + kNN fusionnés et les agrégations de facettes.
- [vLLM (dépôt)](https://github.com/vllm-project/vllm) et [Ollama (dépôt)](https://github.com/ollama/ollama)
  Use for : serving OpenAI-compatible ; API OpenAI-compatible d'Ollama ; backend CPU documenté mais lent de vLLM.

### Axe 2 — interface web
- [RAGFlow (dépôt, Apache-2.0, README_fr)](https://github.com/infiniflow/ragflow)
  Use for : archétype du turnkey « corpus documentaire » (DeepDoc CPU, citations traçables).
- [Kotaemon (dépôt)](https://github.com/Cinnamon/kotaemon)
  Use for : le pattern « citation → PDF surligné + score », référence UI chercheurs.
- [Chaîne d'API BnF : API Document](https://api.bnf.fr/fr/api-document-de-gallica) et [API IIIF](https://api.bnf.fr/fr/api-iiif-de-recuperation-des-images-de-gallica)
  Use for : provenance arK ↔ page OCR, liens profonds Gallica, visualisation IIIF.
- [Chainlit — éléments & OIDC](https://docs.chainlit.io/concepts/element)
  Use for : UI rapide avec affichage des sources RAG et authentification.
- [Open WebUI — LICENSE (clause de marque)](https://github.com/open-webui/open-webui/blob/main/LICENSE) et [Dify — LICENSE (conditions)](https://github.com/langgenius/dify/blob/main/LICENSE)
  Use for : comprendre les « Apache-2.0 à conditions » et la clause des 50 utilisateurs/30 j.
- [Elastic — « Elasticsearch is open source. Again! »](https://www.elastic.co/blog/elasticsearch-is-open-source-again) et [OpenSearch FAQ](https://opensearch.org/faq/)
  Use for : SSPL/Elastic-2.0 vs fork Apache-2.0 ; mécanique de l'AGPL en option.
- [Vanna (dépôt, MIT)](https://github.com/vanna-ai/vanna) et [WrenAI — LICENSE](https://github.com/Canner/WrenAI/blob/main/LICENSE)
  Use for : text-to-SQL en complément, affichage du SQL généré.
- [Papier fiabilité text-to-SQL (arXiv 2601.08778)](https://arxiv.org/abs/2601.08778)
  Use for : pourquoi les facettes doivent rester des agrégations déterministes (taux d'erreur annotateur jusqu'à 62,8 %).

## Sagesse (Communautés)
- [Forum Hugging Face](https://discuss.huggingface.co/)
  Use for : questions embeddings/TEI/sentence-transformers en pratique.
- [Slack/discussions Qdrant](https://qdrant.fr/)
  Use for : retours d'expérience quantification et filtrage à l'échelle.
- Note : préférence communautaire non encore exprimée par l'utilisateur — proposer légèrement, ne pas insister.

## Lacunes (Gaps)
- Aucun article de référence en français sur la post-correction OCR par LLM (la veille constate qu'aucun modèle public n'existe ; seul le mémoire Féral 2025 est documenté).
- Pas de benchmark public retrieval sur français XIXᵉ : l'évaluation interne (200 Q&R annotées) reste le seul juge — à traiter comme ressource à *créer*, pas à trouver.
