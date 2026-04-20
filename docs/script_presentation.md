# Script de présentation — Chatbot RAG Multimodal Ibn Zohr
*Durée estimée : 8 à 10 minutes*

---

## Introduction
*(~1 min)*

Bonjour à tous.

Je vais vous présenter mon projet de stage : la conception et le déploiement d'un chatbot intelligent pour le complexe universitaire Ibn Zohr.

Le constat de départ est simple : l'université produit chaque année un volume croissant de documents — règlements académiques, calendriers, guides étudiants, procédures administratives. Ces informations existent, mais elles sont dispersées, difficiles à retrouver, et les étudiants comme le personnel perdent beaucoup de temps à les chercher.

L'idée du projet, c'est de rendre toute cette connaissance instantanément accessible, dans les trois langues de l'université — français, arabe, anglais — en posant une simple question en langage naturel.

La technologie au cœur de cette solution, c'est le **RAG : Retrieval-Augmented Generation**.

---

## Pourquoi le RAG ?
*(~1 min 30)*

Avant d'entrer dans le détail technique, il faut expliquer pourquoi on choisit le RAG plutôt que d'autres approches.

La première alternative serait le **fine-tuning** : prendre un modèle de langage et le réentraîner sur les documents de l'université. Le problème, c'est que ça coûte des jours de GPU, et dès qu'un règlement change, il faut tout recommencer.

La deuxième alternative, c'est un **LLM seul**, sans base de connaissance. Le problème bien connu : les hallucinations. Le modèle invente des informations avec une confiance totale.

Le RAG résout les deux problèmes à la fois. Au lieu d'encoder la connaissance dans les poids du modèle, on la stocke dans une base de données vectorielle. À chaque question, on récupère les documents pertinents, on les donne au modèle comme contexte, et le modèle rédige une réponse fondée uniquement sur ces sources. Résultat : zéro hallucination sur les faits, mise à jour instantanée en ajoutant un fichier, et toutes les réponses sont citées et traçables.

---

## Les modèles utilisés
*(~2 min)*

Le projet utilise plusieurs modèles pour des rôles différents.

**Pour les embeddings textuels**, j'utilise **nomic-embed-text v1.5**, un modèle de 768 dimensions entraîné spécifiquement pour la recherche sémantique multilingue. Il transforme chaque chunk de document en un vecteur de nombres qui capture son sens. Deux textes proches sémantiquement auront des vecteurs proches dans l'espace mathématique — c'est ce qui permet de retrouver les bons documents même quand la question est formulée différemment.

En parallèle, j'utilise **BM25 via fastembed** pour les embeddings sparse. BM25, c'est l'algorithme de recherche classique par mots-clés — il excelle là où nomic peut être moins précis : les noms propres, les numéros d'articles, les codes spécifiques à l'université. Les deux approches sont fusionnées via une technique appelée Reciprocal Rank Fusion.

**Pour les images**, j'utilise **CLIP ViT-B-32** d'OpenAI. CLIP est un modèle multimodal qui peut représenter des images et du texte dans le même espace vectoriel, ce qui permet de poser une question textuelle et de retrouver des images pertinentes, ou l'inverse.

**Pour le reranking**, j'utilise **cross-encoder/ms-marco-MiniLM-L-6-v2**. C'est un modèle qui prend une paire question-document et lui attribue un score de pertinence très précis. Il est utilisé après la recherche initiale pour réordonner les 20 meilleurs candidats et ne garder que les 5 vraiment pertinents.

**Pour la génération de réponses**, le modèle principal est **Mistral 7B via Ollama**. C'est un LLM open source de 7 milliards de paramètres, sous licence Apache 2.0, qui tourne entièrement en local sur la machine GPU de l'université — zéro dépendance cloud, zéro donnée envoyée à l'extérieur. Le système inclut aussi une abstraction qui permet de basculer vers Phi-3 Mini ou GPT-4o-mini avec un simple changement de variable d'environnement, sans toucher au code.

---

## Le déroulé de la pipeline
*(~2 min 30)*

La pipeline se déroule en deux temps distincts : **l'ingestion** et **le traitement d'une requête**.

### Phase 1 — Ingestion des documents

Quand un administrateur soumet un nouveau document — PDF, DOCX, page web ou image — voici ce qui se passe :

**Étape 1 — Extraction.** Le texte est extrait selon le format : PyMuPDF pour les PDFs, python-docx pour les Word, BeautifulSoup pour les pages web. Pour les images, CLIP extrait directement un vecteur visuel.

**Étape 2 — Déduplication.** On calcule un hash SHA-256 du contenu. Si ce document est déjà indexé, on l'ignore. C'est ce qu'on appelle le delta ingestion — seuls les documents nouveaux ou modifiés sont traités.

**Étape 3 — Chunking sémantique.** C'est ici que j'ai fait un choix technique important. Plutôt que de couper le texte mécaniquement tous les 512 tokens — ce qui peut couper une idée en plein milieu — j'ai implémenté un **SemanticChunker** qui détecte les vrais changements de sujet. Il embed chaque phrase, calcule la similarité cosinus entre phrases consécutives, et place les coupures là où la similarité chute brutalement — c'est-à-dire là où le sujet change réellement.

**Étape 4 — Enrichissement de métadonnées.** Chaque chunk est enrichi : département, langue détectée, niveau d'accès (public, étudiant, personnel, admin), source, horodatage.

**Étape 5 — Indexation dans Qdrant.** Les chunks sont vectorisés et stockés dans la base vectorielle Qdrant avec leurs vecteurs denses, sparse, et éventuellement image.

### Phase 2 — Traitement d'une requête

Quand un étudiant pose une question :

**Étape 1 — Embedding de la requête.** La question est transformée en vecteur dense et sparse.

**Étape 2 — Hybrid search + RRF.** Qdrant lance simultanément une recherche sémantique et une recherche par mots-clés, puis fusionne les résultats avec Reciprocal Rank Fusion pour obtenir les 20 meilleurs candidats.

**Étape 3 — Reranking.** Le cross-encoder réduit ces 20 candidats aux 5 vraiment pertinents en analysant chaque paire question-document.

**Étape 4 — Génération.** Les 5 chunks sont injectés dans un prompt avec l'historique de conversation et le rôle de l'utilisateur. Mistral génère une réponse dans la langue de la question, avec les sources citées.

---

## Les choix technologiques
*(~1 min 30)*

L'ensemble du stack est pensé pour être entièrement **on-premise**, **open source**, et **maintenable** par l'équipe universitaire.

**Qdrant** comme base vectorielle : c'est la seule base de données vectorielle qui supporte nativement les vecteurs hybrides dense+sparse dans la même collection, avec un système de filtres sur les métadonnées. C'est ce qui nous permet d'implémenter le contrôle d'accès directement au niveau de la recherche.

**LangChain LCEL** comme orchestrateur : il chaîne toutes les étapes de la pipeline RAG de manière déclarative et traçable. Couplé à **LangSmith**, chaque appel est enregistré avec ses inputs, outputs et latences — indispensable pour déboguer et optimiser.

**FastAPI** pour l'API REST : génération automatique de documentation, validation Pydantic, rate limiting, et support natif de l'asynchronisme pour des performances maximales.

**Redis** pour la mémoire conversationnelle : les 10 derniers échanges de chaque session sont stockés en mémoire pour que le chatbot comprenne le contexte d'une conversation.

**Docker Compose** pour l'orchestration : les quatre services — FastAPI, Qdrant, Ollama, Redis — sont conteneurisés et démarrent avec une seule commande. Le déploiement est reproductible à l'identique sur n'importe quelle machine.

---

## Évaluation et benchmarks
*(~1 min)*

Pour mesurer objectivement la qualité du système, j'utilise le framework **RAGAS** — un standard d'évaluation conçu spécifiquement pour les systèmes RAG.

Il mesure quatre métriques : la **fidélité** (est-ce que la réponse ne contient que des informations présentes dans les documents ?), la **pertinence** (est-ce que la réponse répond vraiment à la question ?), la **précision du contexte** (est-ce que les bons chunks ont été récupérés ?) et le **rappel du contexte** (est-ce que tous les éléments nécessaires ont été trouvés ?).

Ces métriques sont calculées en lançant un dataset de questions réelles sur trois modèles — Mistral 7B, Phi-3 Mini et GPT-4o-mini comme référence — et en comparant les résultats. Le seuil minimal fixé pour valider le MVP est un score qualité de **0.70 sur 1**.

---

## Conclusion
*(~30 sec)*

Pour résumer : ce projet livre une infrastructure RAG complète, multimodale, multilingue, sécurisée et évaluable — déployable sur les serveurs de l'université sans dépendance à un cloud externe.

La prochaine étape est le déploiement sur la machine GPU universitaire, l'ingestion des premiers documents réels, et la validation des benchmarks RAGAS sur un dataset de questions représentatives.

Je suis disponible pour vos questions.

---
*Fin du script — durée estimée : 8 à 10 minutes selon le rythme*
