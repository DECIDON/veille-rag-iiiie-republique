# Axe 2 — Le côté usage : interface web de consultation, plateformes « turnkey » et stacks composées

> Veille technologique réalisée le **21 octobre 2026**, exclusivement sur **sources primaires** (dépôts Git, fichiers LICENSE, documentations officielles). Les étoiles GitHub et dates de dernier commit sont des instantanés relevés ce jour via les pages de dépôt GitHub et l'API GitHub.
>
> Contexte du projet : service web auto-hébergé de questionnement (RAG) d'un corpus de **dizaines de Go de transcriptions OCR des débats parlementaires de la IIIᵉ République**, avec deux publics (chercheurs exigeant citations précises, facettes, exports ; grand public en Q&A en langage naturel). Scénarios GPU et CPU-only.

Sommaire :
- [1. Plateformes « turnkey » auto-hébergées](#1-plateformes-turnkey-auto-hébergées)
- [2. Angle « corpus parlementaires / historiques »](#2-angle--corpus-parlementaires--historiques-)
- [3. Interfaces construites (« self-built UI »)](#3-interfaces-construites--self-built-ui-)
- [4. Couche de serving et d'intégration](#4-couche-de-serving-et-dintégration)
- [5. Text-to-SQL sur les métadonnées](#5-text-to-sql-sur-les-métadonnées)
- [6. Licences et pièges d'hébergement](#6-licences-et-pièges-dhébergement)
- [7. Recommandations](#7-recommandations)
- [Références](#références)

---

## 1. Plateformes turnkey auto-hébergées

### Tableau comparatif (relevé du 21/10/2026)

| Projet | Licence | Complétude OSS | LLM locaux (Ollama/vLLM/OpenAI-compat.) | Vector DB / moteur | Recherche hybride | Citations | Multi-utilisateurs / auth | GPU/CPU | Activité (étoiles, dernier push) | API |
|---|---|---|---|---|---|---|---|---|---|---|
| **RAGFlow** | Apache-2.0 | 100 % OSS (cloud payant en option) | Oui : Ollama, vLLM, fournisseurs majeurs | Elasticsearch (défaut) ou Infinity | Oui (« multi-recall + rerank fusionné ») | Oui, traçables, visualisation des chunks | Oui (teams, console admin) | **CPU** pour l'OCR/layout DeepDoc en v1.0 ; mini 4 vCPU/16 Go/50 Go | ≈92,6k★, actif (commit du jour) | HTTP API + SDK Python |
| **Dify** | Apache-2.0 **modifié** : multi-tenant interdit sans licence commerciale, logo/© non modifiables | OSS complet, mais conditions ci-contre | Oui : plugins marketplace Ollama, vLLM, OpenAI-API-compatible, Xinference | Vector DB multiples (Weaviate, Qdrant, Milvus, pgvector…) + full-text | Oui : vector / full-text / **hybride** + rerank | Oui (attributions/citations dans les apps) | Oui (workspaces, RBAC) ; multi-tenant = payant/licence | Compatible CPU ; dépend des modèles | ≈159k★, très actif | API REST complète |
| **AnythingLLM** | MIT | Oui (desktop + serveur Docker identiques) | Oui : Ollama, LM Studio, LocalAI, OpenAI-compat. | LanceDB (défaut), Chroma, Milvus, Qdrant, Weaviate, Astra, Pinecone… | Non documentée (retrieval vectoriel ; pas de page hybride/BM25 dans la doc) | Affichage des sources dans les threads (léger) | Oui, mode multi-utilisateur (Docker uniquement), rôles Admin/Manager/Default | Léger, **CPU-only jouable** (Petit LLM via Ollama) | ≈67k★, très actif | API serveur + widget d'intégration + extension navigateur |
| **Open WebUI** | Licence « Open WebUI » (type BSD-3) **+ clause de marque** (interdit de retirer le branding >50 utilisateurs/30 j, sauf permission/enterprise) | Noyau OSS complet ; quelques fonctionnalités « Enterprise » (branding etc.) | Oui : Ollama natif, tout endpoint OpenAI-compatible (donc vLLM, LiteLLM) | Intégré (pgvector optionnel, chemin par défaut SQLite/FAISS-like) | Partielle (engine TF-IDF + vector ; HyDE, rerank) | Oui, citations cliquables dans les réponses | Oui : RBAC, groupes, OIDC/SSO, LDAP, MFA, SCIM, clés API | CPU OK avec petits modèles ; scale « jusqu'à des milliers de sièges » | ≈156k★, très actif | API OpenAI-compatible exposée |
| **Onyx** (ex-Danswer) | **MIT** hors répertoires `ee/` (Onyx Enterprise License) — open-core assumé | CE = RAG/chat/agents complets ; SSO SAML/OIDC, RBAC, analytics, whitelabel **réservés à l'EE** | Oui : Ollama, LiteLLM, vLLM, plus tous fournisseurs propriétaires | Index vector + mot-clé interne (OpenSearch dans le stack standard) | Oui (« hybrid index » revendiqué) | Oui, références/sources | Oui ; **SSO/RBAC = Enterprise** | Mode Standard (index complet, lourd) ou **Lite <1 Go** (chat sans indexation) | ≈32,7k★, très actif | REST + bots Slack/Discord + MCP + widget |
| **Khoj** | **AGPL-3.0** | Oui, auto-hébergé complet ; version « Teams/Enterprise » commerciale | Oui : tous LLM locaux ou distants | PostgreSQL **pgvector** (image `pgvector/pgvector:pg15` du compose) + SearXNG | Sémantique avancée (hybride non mis en avant) | Oui (sources affichées) | Oui (comptes multiples) | Doc : mini 8 Go RAM, GPU conseillé pour les modèles locaux | ≈38k★, maintenu (dernier commit août selon badge) | Non priorisé |
| **Kotaemon** | Apache-2.0 | Oui (Gradio) | Oui : APIs + locaux via Ollama / llama-cpp | Par défaut LanceDB/Chroma via pipeline interne (orienté PDF) | **Oui** : retriever full-text + vector + rerank | **Excellentes** : citations avec score, aperçu PDF surligné dans le navigateur, alerte faible pertinence | Oui : login multi-utilisateur, collections privées/publiques, partage | CPU possible (petits modèles) | ≈26k★, **rythme ralenti (dernier push juil. 2026)** | Non (UI/pipeline Python) |
| **R2R** (SciPhi) | MIT | Oui (REST + dashboard) | Oui (OpenAI-compat. via LiteLLM) | PostgreSQL/pgvector + Neo4j optionnel | Oui (hybride + rerank configurables) | Oui (chunk-level citations) | Oui (users, collections, access control) | CPU possible | ≈8k★, maintenu | REST-first |
| **Quivr** | MIT — ⚠️ **pivot produit** : « Quivr V2 » n'est plus un chat-RAG mais un moteur d'ingestion/monitoring de flux (`v0`, « ne pas utiliser en production ») ; le chat-RAG historique n'est plus la vocation | — | via plugins | PostgreSQL + index de recherche reconstruisable | « Hybrid search » revendiqué (lexical conservé pendant la reconstruction des vecteurs) | n/a | n/a | n/a | ≈39,6k★, actif mais **hors sujet RAG documentaire** | API `v0` |
| **Verba** | BSD-3 | ⚠️ **Projet discontinué, dépôt archivé** (Weaviate) : plus de correctifs ni de patchs de sécurité | Ollama/HF à l'époque | Weaviate uniquement | Non | Sources affichées (simple) | Non | n/a | ≈7,7k★, **archivé** (dernier push juin 2026) | — |
| **Morphik** | ⚠️ **BSL 1.1 : non open source** (usage production limité à <2 000 $/mois de revenus ; conversion Apache-2.0 prévue le 18/06/2029) | Non (open-core + BSL) | Oui (OpenAI-compat.) | pgvector | Oui (semantic + keyword) | Oui | Partiel | GPU conseillé | ≈3,7k★, actif | REST |
| **DeepChat** (ex-Ilumino-Codes, désormais org **ThinkInAIXYZ**) | Apache-2.0 | Oui | Oui | — | n/a | n/a | Desktop **local-first**, pas un service web multi-utilisateurs | Bureau local | ≈6,4k★, très actif | — |
| **MaxKB** (1Panel/fit2cloud) | **GPL-3.0** (attention : pas AGPL, mais copyleft fort à la redistribution) | Oui ; docs surtout en **chinois** | Oui (fournisseurs + OpenAI-compat.) | Weaviate/pgvector selon config | Mode « mixed » + rerank revendiqués dans la doc | Oui | Oui | CPU OK | ≈23k★, très actif (push du jour) | API + widget |
| **FastGPT** (labring) | Apache-2.0 **modifié** (multi-tenant SaaS interdit sans licence, logo non retirable) — mêmes conditions que Dify | Oui ; écosystème orienté chinois | Oui (OpenAI-compat., Ollama via plugins) | pgvector / milvus… | Oui (vector + full-text) | Oui | Oui | CPU OK | ≈30k★, très actif | API |
| **LobeChat / LobeHub** | « **LobeHub Community License** » (Apache-2.0 + conditions, restrictions commerciales) | Oui mais licence dérivée non OSI | Oui (tous fournisseurs) | Vector interne / pgvector | Non mis en avant | Oui | Oui | CPU OK | ≈83k★, très actif | API |

### Notes par plateforme

**RAGFlow** — Le plus « orienté corpus documentaire » des turnkey : extraction basée sur la compréhension de document (DeepDoc : layout, OCR, tableaux, en **inférence CPU** dans la v1.0 open source), templates de chunking explicites, mots-clés ajoutables aux chunks pour booster le ranking lexical, **citations traçables** et test de récupération intégré, agentique RAG multi-étapes. Supporte Ollama et vLLM pour les modèles. Déploiement Docker (Elasticsearch par défaut ou Infinity), config minimale conseillée 4 vCPU/16 Go/50 Go. README officiel **en français** (README_fr.md). Apache-2.0 pur, sans open-core côté serveur (le cloud est un service distinct). (<https://github.com/infiniflow/ragflow>, <https://ragflow.io/docs/>)

**Dify** — Plateforme « LLMOps » très complète (apps, workflows, knowledge pipelines). Recherche en base de connaissances : indexation vectorielle ou **hybride (vector + full-text)**, rerank en option, métadonnées de documents, bases de connaissances externes via API. Fournisseurs de modèles via plugins marketplace (Ollama, vLLM, Xinference, OpenAI-API-compatible vérifiés sur le marketplace). ⚠️ Licence Apache 2.0 **avec conditions supplémentaires** : interdiction d'opérer un environnement multi-tenant sans licence commerciale et obligation de conserver logo/© dans la console. Pour un service public mono-tenant avec branding conservé, l'usage est conforme. (<https://github.com/langgenius/dify/blob/main/LICENSE>, <https://docs.dify.ai/>, <https://marketplace.dify.ai/plugin/ollama>)

**AnythingLLM** — Le plus simple à auto-héberger (Docker ou bureau), MIT, nombreux vector DB embarqués, nombreux LLM locaux (Ollama, LM Studio, LocalAI). Mode multi-utilisateur (rôles Admin/Manager/Default) disponible dans la version Docker ; widget d'intégration web et extension navigateur. En revanche : **pas de recherche hybride documentée**, citations modestes — grand public OK, chercheurs moins bien servis. (<https://github.com/Mintplex-Labs/anything-llm>, <https://docs.anythingllm.com/>, <https://docs.useanything.com/features/security-and-access>)

**Open WebUI** — Interface chat multi-utilisateurs la plus répandue ; conversation avec n'importe quel backend OpenAI-compatible (donc Ollama/vLLM/LiteLLM), **RAG sur fichiers téléversés et « Knowledge »** avec citations cliquables, extraction documentaire branchable (Docling, Mistral OCR, Apache Tika, extracteur externe), moteur de recherche web (SearXNG, etc.), chunkage configurable, **SSO/OIDC, LDAP, MFA, SCIM, RBAC et clés API dans le noyau** (contrairement à Onyx). ⚠️ Licence spécifique : clause interdisant de retirer/remplacer le branding « Open WebUI » au-delà de 50 utilisateurs distincts sur 30 jours glissants, sauf accord écrit ou licence enterprise — point critique pour un service public personnalisé. (<https://github.com/open-webui/open-webui/blob/main/LICENSE>, <https://docs.openwebui.com/features/chat-conversations/rag/>, <https://docs.openwebui.com/features/authentication-access/auth/sso/>)

**Onyx** — « Couche de contexte » d'entreprise : connecteurs (50+ apps), index **hybride vector+mot-clé**, agents, deep research, web search, widget embarquable, air-gappable, Ollama/LiteLLM/vLLM supportés. CE sous **MIT**, mais SSO (OIDC/SAML), synchronisation de groupes SCIM, RBAC fin, analytics et whitelabel sont dans l'édition **Enterprise** (`ee/`). Deux modes : Standard (index complet) ou **Lite** (<1 Go, sans indexation). Bon candidat si l'on n'a pas besoin du SSO en version gratuite. (<https://github.com/onyx-dot-app/onyx/blob/main/LICENSE>, <https://github.com/onyx-dot-app/onyx/blob/main/README.md>)

**Khoj** — AGPL-3.0 ; auto-hébergement complet (PostgreSQL **pgvector** imposé, SearXNG pour le web), LLM locaux ou distants, recherche sémantique sur vos documents, clients web/embarqués (Obsidian, Emacs, mobile). La version « Teams/Enterprise » (on-prem/hybride) est commerciale. L'AGPL est compatible d'un service public (le code doit rester ouvert à l'usage réseau), mais c'est un choix à assumer juridiquement si vous fork. (<https://github.com/khoj-ai/khoj> AGPL via GitHub, <https://docs.khoj.dev>, docker-compose du dépôt : `pgvector/pgvector:pg15`)

**Kotaemon** (par Cinnamon, ex-Cohere) — Interface RAG « pourchercheurs » : pipeline **hybride full-text+vector avec rerank**, **citations avancées avec aperçu PDF surligné dans le navigateur et score de pertinence**, avertissement quand la retrieval est faible, multi-login et collections privé/public, LLM via API ou locaux (Ollama, llama-cpp-python). Construit sur Gradio ; dépendances Python ; dernier push juillet 2026 (rythme en ralentissement). Très proche du besoin « chercheurs ». (<https://github.com/Cinnamon/kotaemon>, <https://cinnamon.github.io/kotaemon/>)

**R2R** — Backend RAG « production-grade » MIT, orienté API REST (users, collections, graphs, hybrid+rerank, citations chunk-level), avec app web de démo ; pertinent comme brique de stack composée plutôt que comme front final. (<https://github.com/SciPhi-AI/r2r>)

**Sortis du périmètre** (vérifié sur les dépôts) : **Verba** archivé/discontinu ; **Quivr** devenu un moteur de flux (V2 `v0`, plus une app de chat-RAG) ; **Morphik** sous BSL non-OSS avec plafond de revenus ; **DeepChat** devenu un client desktop local-first (non adapté à un service web public) ; **Vellum** exclu (SaaS). **MaxKB / FastGPT / LobeChat** : actifs et crédibles techniquement, mais licences à conditions (GPL-3.0, Apache+conditions, licence communautaire) et documentation prioritairement en chinois — à considérer si l'écosystème anglophone devient insuffisant.

---

## 2. Angle « corpus parlementaires / historiques »

État de l'art OSS constaté (GitHub, data.gouv, éditeurs de données) :

- **Données ouvertes officielles** (utile pour facettes date/orateur/chambre et pour l'enrichissement de nos métadonnées) :
  - **data.assemblee-nationale.fr** : API et exports JSON sous **Licence ouverte** — députés, organes, **débats de séance publique, amendements, votes, questions** ; structure XML/JSON documentée (« Schémas »). (<https://data.assemblee-nationale.fr/>)
  - **data.senat.fr** : travaux législatifs, amendements, **comptes rendus des débats**, questions, sous licence ouverte ; point d'entrée et FAQ. (<https://data.senat.fr/>)
  - Consolidation amont : jeu de données « Parlementaires français » par **DataParl** sur data.gouv.fr (normalisation AN/Sénat/PE). (<https://www.data.gouv.fr/datasets/parlementaires-francais-assemblee-nationale-senat-parlement-europeen>)
  - **ParlAPI** (Regards Citoyens) : API « propre » sur l'open data parlementaire, projet historique réhébergé hors GitHub (le dépôt GitHub renvoie vers le nouveau forgeron). Bon précédent d'exposition d'API sur ces données. (<https://github.com/regardscitoyens/parlapi>)
- **Gallica / BnF (provenance et deep links)** : la BnF expose des **API officielles** — recherche (GLW), **API Document** (métadonnées + `OAIRecord`, arK) et **API IIIF** (images et manifests des documents numérisés). C'est la base du pattern « citation → page source » : stocker l'**arK** de chaque page citée et générer des liens profonds `https://gallica.bnf.fr/ark:/61565/…` + manifests IIIF pour un visualiseur de page (Mirador/Universal Viewer). (<https://api.bnf.fr/fr/api-document-de-gallica>, <https://api.bnf.fr/fr/api-iiif-de-recuperation-des-images-de-gallica>, <https://www.data.gouv.fr/dataservices/api-gallica-iiif>)
- **CLASIT** (plateforme d'outils d'analyse de corpus pour les SHS, portée par la TGIR Huma-Num) : référence méthodologique pour l'analyse de corpus de textes par les historiens ; le site `clasit.cnrs.fr` était **injoignable** lors de la veille (21/10/2026) — à recontrôler ; l'outil lui-même n'est pas un frontend web public. (<https://clasit.cnrs.fr/>)
- Nous n'avons **pas trouvé de clone OSS « chat avec les débats »** mature et maintenu sur données françaises (recherches GitHub « parli* », « assemblee », « scrapers parlement » : uniquement scrapers datés type OpnTec/parliament-scraper, ou outils de suivi type ParlAPI). Les UI de référence restent les moteurs de recherche officiels AN/Sénat (recherche par chambre, date, type de texte, orateur) et les projets de monitoring type **TheyWorkForYou/parlparse** côté UK. (<https://github.com/mysociety/parlparse>, <https://github.com/OpnTec/parliament-scraper>)

**Patterns UX à retenir pour notre interface** (issus des outils consultés ci-dessus et des UI « chat-with-citations » §1) :

1. **Citation → source** : chaque chunk cite (a) la référence interne (cote, tome, page), (b) un lien profond Gallica/`ark:` quand le document est numérisé, (c) l'extrait exact entourant le passage (contexte ± phrase). Kotaemon (surlignage PDF) et RAGFlow (visualisation des chunks) montrent comment le faire côté UI.
2. **Facettes systématiques** : date, chambre, orateur, groupe/qualification, type d'intervention, session — c'est ce que font AN/Sénat ; le RAG pur sans facettes est insuffisant pour les historiens.
3. **Recherche hybride en premier** (exact/phrase + sémantique), la génération n'étant qu'un habillage : corpus OCR = beaucoup de bruit lexical, le BM25/lexical reste décisif.
4. **Provenance affichée** : afficher le modèle + version d'index + score de retrieval à côté de la réponse (Onyx/RAGFlow/Kotaemon le font), et exporter la réponse avec ses sources (CSV/JSON/BibTeX) pour le public chercheur.
5. **Comptes rendus ≠ verbatim** : prévoir l'affichage de la structure hiérarchique (séance → ordre du jour → intervention) plutôt que des chunks plats — RAGFlow (templates par format) et Kotaemon (chunking par section PDF) aident, sinon c'est à vous de le porter dans le modèle de données.

---

## 3. Interfaces construites (« self-built UI »)

| Framework | Licence | Apports RAG/multi-utilisateurs | Limites |
|---|---|---|---|
| **Chainlit** (entreprise française) | Apache-2.0 | Chat complet + affichage d'**éléments** (PDF viewer « ideal to display RAG sources », texte, dataframe), steps de raisonnement, **auth OIDC/OAuth**, data layer (persistance threads/étapes/feedbacks), traductions UI par fichier JSON (`fr` personnalisable, langue suivie par navigateur), intégrations LangChain/LlamaIndex | Pas de facettes/recherche clés en main : tout est dans votre code Python | 
| **Gradio** | Apache-2.0 | Rapide à prototyper, files d'attente, thèmes (thème Kotaemon dispo) ; multi-user limité (auth de base) | Peu adapté à une UI riche facettes en production |
| **Streamlit** | Apache-2.0 | Simple, widgets riches ; la doc montre un **flux de login OIDC manuel**, mais pas de gestion d'utilisateurs intégrée | Multi-utilisateurs/SSO = à bricoler ou passer par Streamlit Cloud |
| **Next.js + AI SDK / LangChain / LlamaIndex** (ex. **Vercel ai-chatbot**, Apache-2.0) | Apache-2.0 | Contrôle total UI (facettes, facettes persistées, URLs propres, exports), SSR/SEO, composants chat + citations libres | Tout à construire ; maintenance front continue |
| **OpenSearch Dashboards** | Apache-2.0 | Si la retrieval vit dans OpenSearch : exploration/facettes/visualisations gratuites, plugins neural/hybrid et agents RAG (ML Commons) | UX « dashboards », pas un chat citoyen grand public |
| **Vespa** | Apache-2.0 | Moteur hybride bm25+vectoriel+rank-profile à l'échelle, API de recherche, pas de front « chat » livré | Courbe d'apprentissage forte ; sur-dimensionné <10 M docs |

Réf : <https://github.com/Chainlit/chainlit> · <https://docs.chainlit.io/authentication/overview> · <https://docs.chainlit.io/authentication/oauth> · <https://docs.chainlit.io/concepts/element> · <https://docs.chainlit.io/customisation/translation> · <https://github.com/gradio-app/gradio> · <https://github.com/streamlit/streamlit> · <https://discuss.streamlit.io/t/how-to-visualize-sources-in-streamlit-chat-app/87209> · <https://github.com/vercel/ai-chatbot> · <https://opensearch.org/faq/> · <https://docs.opensearch.org/latest/query-dsl/compound/hybrid/> · <https://docs.opensearch.org/latest/ml-commons-plugin/agents-tools/tools/rag-tool/> · <https://github.com/vespa-engine/vespa>

**Pattern « chat-with-citations » constaté partout** : (1) la réponse est rendue avec des marqueurs `[^n]` cliquables ; (2) un panneau latéral affiche les chunks sources avec score + bouton « ouvrir la source » ; (3) le lien source pointe vers une **vue stable du document** (aperçu PDF surligné — Kotaemon — ou page IIIF/deep link — Gallica). C'est exactement ce qu'il faut pouvoir faire avec l'ark Gallica.

---

## 4. Couche de serving et d'intégration

- **Ollama** (MIT) : sert les modèles locaux et expose nativement l'**API OpenAI-compatible `/v1`** (« Call cloud models with Ollama, OpenAI, or Anthropic APIs »). C'est l'interface minimale de branchement de tous les outils ci-dessus. (<https://github.com/ollama/ollama> · <https://ollama.com/docs>)
- **vLLM** (Apache-2.0) : serveur **OpenAI-compatible** de production (continous batching, quantizations). Les plateformes qui parlent « OpenAI-compatible » acceptent vLLM tel quel : vérifié pour Dify (plugin `vllm`), RAGFlow (doc « Deploy local models » Ollama/vLLM), Onyx (README), Open WebUI (connection any OpenAI-compatible). (<https://github.com/vllm-project/vllm> · <https://docs.vllm.ai/en/latest/serving/openai_compatible_server/> · <https://ragflow.io/docs/deploy_local_llm>)
- **LiteLLM** (MIT, avec répertoire `enterprise/` sous licence commerciale — open core) : proxy/gateway unifiant 100+ fournisseurs derrière un endpoint OpenAI, avec virtual keys et budgets — utile pour exposer une seule porte aux outils et compter par usage. (<https://github.com/BerriAI/litellm> · <https://docs.litellm.ai/>)
- **Conséquences CPU-only** : le choix de l'UI ne change rien au goulot LLM, mais l'architecture doit être **retrieval-first** : (1) indexer en amont les embeddings par batch (offline), (2) exposer d'abord une recherche hybride + facettes (CPU OK : OpenSearch/ES/Postgres+pgvector), (3) limiter la génération à de petits modèles (3–8B quantifiés via Ollama/llama.cpp) et afficher systématiquement les chunks récupérés — les patterns « Open WebUI/Chainlit + petits modèles + gros retrieval » restent utilisables sans GPU ; (4) prévoir un mode « sans LLM » (extraits purs) pour l'auditeur qui veut du déterministe. Noter que RAGFlow fait tourner son OCR/layout **sur CPU** en v1 open source et qu'Onyx Lite tourne avec <1 Go.

---

## 5. Text-to-SQL sur les métadonnées

Complément naturel du RAG pour « combien de discours de Jaurès en 1904 ? », « textes déposés par la chambre des députés entre 1876 et 1885 » :

- **Vanna** (MIT) — bibliothèque Python NL→SQL « RAG for SQL » (entraînée sur DDL/docs/exemples SQL). V2 ajoute un **web component** de chat (tableaux, graphs Plotly, résumé en langage naturel, streaming SSE), intégration FastAPI et filtrage par permission utilisateur. Licence MIT au 21/10/2026, dernier push février 2026 (rythme moindre). (<https://github.com/vanna-ai/vanna> · <https://vanna.ai/docs/quick-start>)
- **WrenAI** (Canner) — « GenBI » open source reposant sur une **couche sémantique versionnée** (MDL : définitions de métriques, enums, jointures approuvées, exemples) ; le dépôt est **multi-licences** : `core/`, `sdk/`, `skills/`, `examples/` et racine en **Apache-2.0**, docs en CC-BY-4.0, des modules AGPL-3.0 *pourraient* apparaître (table de correspondance dans le LICENSE). Pilote par agents (MCP, CLI) plutôt que par une UI chat dédiée. (<https://github.com/Canner/WrenAI/blob/main/LICENSE> · <https://docs.getwren.ai>)
- **Recommandation pratique** : stocker corpus **et** métadonnées en **PostgreSQL (+ pgvector)** donne d'un côté la recherche vectorielle, de l'autre un entrepôt interrogeable en SQL ; Vanna (MIT) ou Wren (Apache-2.0) peuvent traduire les questions en SQL sur ces tables, et l'UI peut afficher le SQL généré (bon pour la confiance des chercheurs, pratique visible chez Vanna/Wren).

---

## 6. Licences et pièges d'hébergement

- **AGPL et service public auto-hébergé** : l'AGPLv3 ajoute l'obligation (section 13) d'offrir le **source de la version modifiée à tout utilisateur qui « interagit à distance »** avec le logiciel. Pour un service public ouvert à tous, cela signifie que toute personnalisation de Khoj (AGPL) doit rester publiquement redistribuable en source — généralement acceptable pour un projet public, mais qui « verrouille » toute stratégie de ré-licence. Pour les composants du chemin critique (interface exposée au public), préférer des licences permissives (Apache/MIT/BSD) pour garder la liberté de personnaliser sans obligation de publication. Réf : texte AGPL et analyses : <https://www.elastic.co/blog/elasticsearch-is-open-source-again> (mécanisme décrit), <https://www.elastic.co/pricing/faq/licensing>.
- **Elasticsearch vs OpenSearch** : Elasticsearch/Kibana sont triple-licence **SSPL / Elastic License 2.0 / AGPLv3** depuis sept. 2024 (ni SSPL ni Elastic License ne sont des licences open source OSI ; l'option AGPL rend le code « open source » mais avec copyleft réseau). **OpenSearch** (fork de la v7.10) et OpenSearch Dashboards sont **Apache-2.0** pur. Pour un service auto-hébergé sans redistribution, les deux sont légalement utilisables ; OpenSearch garde l'avantage d'une licence pérenne et de plugins ML/hybride inclus. (<https://www.elastic.co/blog/elasticsearch-is-open-source-again> · <https://www.elastic.co/pricing/faq/licensing> · <https://opensearch.org/faq/>)
- **Turnkey à conditions façon Dify** : le « Apache-2.0 modifié » de **Dify** (multi-tenant interdit sans contrat, logo/© conservés) et celui de **FastGPT** (SaaS multi-tenant, logo) doivent être lus avant de mutualiser une instance pour plusieurs institutions — un portail mono-institution avec marque conservée reste dans les clous. **LobeChat** applique une « Community License » dérivée d'Apache avec conditions commerciales. (<https://github.com/langgenius/dify/blob/main/LICENSE> · <https://raw.githubusercontent.com/labring/FastGPT/main/LICENSE> · <https://raw.githubusercontent.com/lobehub/lobe-chat/main/LICENSE>)
- **Clause de branding d'Open WebUI** : la licence interdit de retirer/masquer/remplacer le branding « Open WebUI » **dès 50 utilisateurs distincts par fenêtre glissante de 30 jours**, sauf accord écrit ou licence enterprise — quasi certain pour un service public ; à intégrer dans la décision dès le premier jour. (<https://github.com/open-webui/open-webui/blob/main/LICENSE>)
- **Open-core à surveiller** : **Onyx** (SSO/RBAC/whitelabel = `ee/`), **LiteLLM** (`enterprise/`), **Morphik** (BSL + plafond de revenus), MaxKB/FastGPT (fonctionnalités « pro » et écosystème commercial chinois). Toujours vérifier le fichier LICENSE et les répertoires `ee/`/`enterprise/` avant de bâtir dessus.
- **Copyleft fort non-AGPL** : **MaxKB** est GPL-3.0 : un service auto-hébergé n'oblige pas à publier le source (pas de clause réseau), mais toute distribution d'une version modifiée l'oblige. Khoj (AGPL) est plus strict. D'un point de vue « service public numérique », les deux sont compatibles ; l'open-core l'est beaucoup moins.

---

## 7. Recommandations

### Plateformes turnkey — shortlist

1. **RAGFlow** (Apache-2.0) — meilleur alignement « corpus documentaire exigeant » : chunking par templates, mots-clés par chunk, citations traçables, hybride + rerank, OCR CPU, actifs et doc en français. Retenir : Elasticsearch/Infinity + 16 Go de RAM mini.
2. **Open WebUI** (licence BSD-3 + clause branding) — pour le volet **grand public** (chat + knowledge + citations) branché sur Ollama/vLLM via OpenAI-compat., SSO/RBAC natifs. Accepter la clause de marque ou payer l'enterprise ; sinon l'utiliser en phase de test uniquement.
3. **Onyx Community Edition** (MIT) — alternative si l'on veut des connecteurs multiples et une vraie recherche hybride, en acceptant que SSO/RBAC soient hors CE (ou en les déléguant au reverse-proxy/IdP devant l'app).
4. **AnythingLLM** (MIT) — option minimale 100 % permissive pour un POC léger ; trop pauvre côté citations/facettes pour les chercheurs.
5. **Kotaemon** (Apache-2.0) — à garder comme **référence UI « citations + facettes de score »** pour les chercheurs, voire comme petite UI de service, en surveillant le ralentissement de maintenance.
6. **Dify** — si le besoin de workflows/agentique dépasse le RAG pur ; vérifier la conformité mono-tenant/logo avant usage institutionnel.
   Exclus : Verba (archivé), Quivr (pivot non-RAG), Morphik (BSL non-OSS), DeepChat (desktop), LobeChat/MaxKB/FastGPT (licences à conditions + doc/écosystème chinois) — gardés en veille.

### Stack composée — shortlist (recommandée pour le service cible)

- **Index/retrieval** : PostgreSQL **pgvector** (corpus < quelques dizaines de Go : un seul composant, jointures avec les métadonnées, backups triviaux) ; sinon **OpenSearch** Apache-2.0 (hybride bm25+kNN, agrégations pour facettes, OpenSearch Dashboards gratuits) ; **Vespa** seulement si l'échelle l'exige.
- **Serving** : **Ollama** (développement, CPU) puis **vLLM** (OpenAI-compatible, multi-utilisateurs) ; **LiteLLM** en gateway si plusieurs modèles/fournisseurs cohabitent.
- **Front** : **Chainlit** (français, Apache-2.0, OIDC, data layer, éléments PDF/sources) pour livrer vite une UI correcte multi-utilisateurs ; basculement Next.js (base **vercel/ai-chatbot** Apache-2.0) quand l'UX facettes devient critique.
- **Complément** : **Vanna** (MIT) ou **WrenAI** (Apache-2.0) pour la NL→SQL sur les tables de métadonnées AN/Sénat + arK Gallica, avec affichage du SQL généré.
- **Provenance** : schéma de métadonnées aligné sur les schémas AN/Sénat (data.assemblee-nationale.fr, data.senat.fr) + arK Gallica pour deep links et IIIF ; chaque réponse affiche chunk + cote + page + lien profond.

### Scénarios GPU vs CPU

- **GPU dispo** : vLLM (modèle 7–14B quantisé) + RAGFlow (ingestion) ou stack composée ; génération pour tous.
- **CPU only** : retrieval-first — recherche hybride + facettes en interface principale, petits modèles (3–8B) via Ollama pour la synthèse, mode « extraits purs » sans LLM, embeddings calculés en offline. RAGFlow (DeepDoc CPU) et Open WebUI restent utilisables ; Onyx Lite pour une UI à <1 Go.

---

## Références

Plateformes turnkey :

1. RAGFlow — dépôt (licence Apache-2.0, README_fr) : <https://github.com/infiniflow/ragflow>
2. RAGFlow — docs (quickstart, citations, modèles locaux Ollama/vLLM, prérequis 4 vCPU/16 Go/50 Go, DeepDoc CPU) : <https://ragflow.io/docs/>
3. Dify — LICENSE (Apache-2.0 + conditions multi-tenant/logo) : <https://github.com/langgenius/dify/blob/main/LICENSE>
4. Dify — docs (méthodes d'indexation vector/hybride, métadonnées, bases externes) : <https://docs.dify.ai/> et <https://docs.dify.ai/en/self-host/use-dify/knowledge/create-knowledge/setting-indexing-methods.md>
5. Dify — plugins marketplace (ollama, vllm, openai_api_compatible, xinference) : <https://marketplace.dify.ai/plugin/ollama> · <https://marketplace.dify.ai/plugin/vllm> · <https://marketplace.dify.ai/plugin/openai_api_compatible>
6. AnythingLLM — dépôt (MIT) : <https://github.com/Mintplex-Labs/anything-llm>
7. AnythingLLM — docs (vector DB, LLM locaux Ollama/LM Studio/LocalAI) : <https://docs.anythingllm.com/> · <https://docs.anythingllm.com/features/vector-databases>
8. AnythingLLM — multi-user mode : <https://docs.useanything.com/features/security-and-access>
9. Open WebUI — LICENSE (clause branding) : <https://github.com/open-webui/open-webui/blob/main/LICENSE>
10. Open WebUI — docs RAG/citations : <https://docs.openwebui.com/features/chat-conversations/rag/> ; knowledge : <https://docs.openwebui.com/features/workspace/knowledge>
11. Open WebUI — auth SSO/OIDC, RBAC, SCIM, MFA : <https://docs.openwebui.com/features/authentication-access/> · <https://docs.openwebui.com/features/authentication-access/auth/sso/>
12. Onyx — LICENSE (MIT hors `ee/`) : <https://github.com/onyx-dot-app/onyx/blob/main/LICENSE>
13. Onyx — README (hybrid index, Ollama/LiteLLM/vLLM, Lite <1 Go, EE=SSO/RBAC/whitelabel) : <https://github.com/onyx-dot-app/onyx>
14. Khoj — dépôt (AGPL-3.0, docs « open-source, self-hostable. Always. », offre Enterprise) : <https://github.com/khoj-ai/khoj> · <https://docs.khoj.dev> · compose pgvector : <https://github.com/khoj-ai/khoj/blob/main/docker-compose.yml>
15. Kotaemon — dépôt (Apache-2.0, hybride, citations PDF surlignées, multi-login) : <https://github.com/Cinnamon/kotaemon> · user guide : <https://cinnamon.github.io/kotaemon/>
16. R2R — dépôt (MIT, API-first) : <https://github.com/SciPhi-AI/r2r>
17. Quivr — dépôt (pivot « Quivr V2 », statut `v0`) : <https://github.com/The-Vibe-Company/quivr>
18. Verba — dépôt archivé (BSD-3, discontinué) : <https://github.com/weaviate/Verba>
19. Morphik — LICENSE BSL 1.1 : <https://raw.githubusercontent.com/morphik-org/morphik-core/main/LICENSE> · dépôt : <https://github.com/morphik-org/morphik-core>
20. DeepChat — dépôt (ThinkInAIXYZ, Apache-2.0, desktop local-first) : <https://github.com/ThinkInAIXYZ/deepchat>
21. MaxKB — dépôt (GPL-3.0) : <https://github.com/1Panel-dev/MaxKB> · docs (zh) : <https://docs.fit2cloud.com/maxkb/>
22. FastGPT — LICENSE (Apache-2.0 + conditions) : <https://raw.githubusercontent.com/labring/FastGPT/main/LICENSE> · dépôt : <https://github.com/labring/FastGPT>
23. LobeChat — licence communautaire : <https://raw.githubusercontent.com/lobehub/lobe-chat/main/LICENSE> · dépôt : <https://github.com/lobehub/lobe-chat>

Corpus parlementaires / historiques :

24. Open data Assemblée nationale (licence ouverte, débats/amendements/votes, schémas) : <https://data.assemblee-nationale.fr/>
25. Open data Sénat (comptes rendus, textes, questions) : <https://data.senat.fr/>
26. DataParl / data.gouv.fr « Parlementaires français » : <https://www.data.gouv.fr/datasets/parlementaires-francais-assemblee-nationale-senat-parlement-europeen>
27. ParlAPI (Regards Citoyens) : <https://github.com/regardscitoyens/parlapi>
28. BnF API Document (métadonnées Gallica, OAIRecord) : <https://api.bnf.fr/fr/api-document-de-gallica>
29. BnF API IIIF (images Gallica) : <https://api.bnf.fr/fr/api-iiif-de-recuperation-des-images-de-gallica> · data.gouv : <https://www.data.gouv.fr/dataservices/api-gallica-iiif>
30. CLASIT (site injoignable le 21/10/2026) : <https://clasit.cnrs.fr/>
31. ParlParse (UK, précédent scraper/parser parlementaire) : <https://github.com/mysociety/parlparse> ; Parliament scraper (OpnTec, archivé 2017) : <https://github.com/OpnTec/parliament-scraper>

UI et serving :

32. Chainlit — dépôt (Apache-2.0) : <https://github.com/Chainlit/chainlit> ; auth overview : <https://docs.chainlit.io/authentication/overview> ; OAuth/OIDC : <https://docs.chainlit.io/authentication/oauth> ; éléments (PDF « RAG sources ») : <https://docs.chainlit.io/concepts/element> ; traduction : <https://docs.chainlit.io/customisation/translation>
33. Gradio — dépôt (Apache-2.0) : <https://github.com/gradio-app/gradio>
34. Streamlit — dépôt (Apache-2.0) : <https://github.com/streamlit/streamlit> ; auth OIDC manuelle : <https://docs.streamlit.io/develop/concepts/connections/authentication>
35. Vercel ai-chatbot — dépôt (Apache-2.0, front Next.js de référence) : <https://github.com/vercel/ai-chatbot>
36. OpenSearch — FAQ licence Apache-2.0 : <https://opensearch.org/faq/> ; requête hybride : <https://docs.opensearch.org/latest/query-dsl/compound/hybrid/> ; agent RAG : <https://docs.opensearch.org/latest/ml-commons-plugin/agents-tools/tools/rag-tool/> ; Dashboards (Apache-2.0) : <https://github.com/opensearch-project/opensearch-dashboards>
37. Vespa — dépôt (Apache-2.0) : <https://github.com/vespa-engine/vespa>
38. Ollama — dépôt (MIT) : <https://github.com/ollama/ollama> ; API OpenAI-compatible : <https://ollama.com/docs>
39. vLLM — dépôt (Apache-2.0) : <https://github.com/vllm-project/vllm> ; serveur OpenAI-compatible : <https://docs.vllm.ai/en/latest/serving/openai_compatible_server/>
40. LiteLLM — LICENSE (MIT + `enterprise/`) : <https://github.com/BerriAI/litellm> · <https://docs.litellm.ai/docs/proxy/enterprise>

Licences & moteurs de recherche :

41. Elastic — « Elasticsearch is open source. Again! » (AGPL en option, sept. 2024) : <https://www.elastic.co/blog/elasticsearch-is-open-source-again>
42. Elastic — FAQ licences (SSPL / Elastic License / AGPL) : <https://www.elastic.co/pricing/faq/licensing>
43. OpenSearch FAQ (Apache-2.0) : <https://opensearch.org/faq/>

Text-to-SQL :

44. Vanna — dépôt (MIT, v2 avec web component + FastAPI) : <https://github.com/vanna-ai/vanna> ; quickstart : <https://vanna.ai/docs/quick-start>
45. WrenAI — LICENSE multi-licence (core Apache-2.0) : <https://github.com/Canner/WrenAI/blob/main/LICENSE> ; docs : <https://docs.getwren.ai>

*Méthodologie : toutes les affirmations de licence proviennent des fichiers LICENSE bruts (raw.githubusercontent.com) ou des pages de dépôt GitHub ; les étoiles et dates de dernier push sont des relevés du 21/10/2026 (badges shields.io + API GitHub search + pages de dépôts). Les capacités fonctionnelles proviennent des README/docs officielles citées en regard.*
