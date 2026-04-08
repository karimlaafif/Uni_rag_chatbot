import asyncio
import logging
import os
import time
from typing import Any, Dict, List, Tuple

import numpy as np
import pandas as pd
from datasets import Dataset
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

from benchmarks.test_dataset import MANUAL_TEST_DATASET
from config import settings
from rag.chain import RAGChatbot

logger = logging.getLogger(__name__)

# =============================================================================
#  CONFIGURATION DES MODÈLES À BENCHMARKER
#  Modifie cette liste pour ajouter/retirer des modèles.
# =============================================================================

MODELS_TO_BENCHMARK: List[Dict[str, str]] = [
    {
        "name":     "Mistral 7B (Local)",
        "provider": "ollama",
        "model":    "mistral:latest",
    },
    {
        "name":     "Phi-3 Mini (Local)",
        "provider": "ollama",
        "model":    "phi3",
    },
    # Décommente si tu as configuré OPENAI_API_KEY dans .env :
    # {
    #     "name":     "GPT-4o-mini",
    #     "provider": "openai",
    #     "model":    "gpt-4o-mini",
    # },
]


JUDGE_PROVIDER: str = "ollama"
JUDGE_MODEL:    str = "mistral:latest"   # modèle utilisé comme juge RAGAS


# =============================================================================
#  HELPERS — Construction des LLMs et embeddings
# =============================================================================

def _build_llm(provider: str, model: str):
    """
    Construit un LLM LangChain prêt à l'emploi.
    Utilisé à la fois pour les modèles benchmarkés et pour le juge RAGAS.
    """
    if provider == "openai":
        from langchain_openai import ChatOpenAI
        if not settings.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY manquante dans .env pour utiliser le provider 'openai'."
            )
        return ChatOpenAI(temperature=0, model=model)

    elif provider == "anthropic":
        from langchain_anthropic import ChatAnthropic
        if not settings.ANTHROPIC_API_KEY:
            raise ValueError(
                "ANTHROPIC_API_KEY manquante dans .env pour utiliser le provider 'anthropic'."
            )
        return ChatAnthropic(temperature=0, model=model)

    else:  # ollama (défaut)
        from langchain_community.chat_models import ChatOllama
        return ChatOllama(
            model=model,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.1,
        )


def _build_judge_llm() -> LangchainLLMWrapper:
    """
    Wraps le LLM juge dans le format attendu par RAGAS.
    RAGAS utilise ce LLM pour évaluer Faithfulness, Context Precision et Recall.
    """
    llm = _build_llm(JUDGE_PROVIDER, JUDGE_MODEL)
    return LangchainLLMWrapper(llm)


def _build_judge_embeddings() -> LangchainEmbeddingsWrapper:
    """
    Wraps les embeddings dans le format RAGAS.
    Utilisés par Answer Relevancy pour comparer la question et la réponse
    dans l'espace vectoriel (similarité sémantique).
    On réutilise nomic-embed-text — déjà présent dans le projet.
    """
    from langchain_community.embeddings import HuggingFaceEmbeddings
    embeddings = HuggingFaceEmbeddings(
        model_name="nomic-ai/nomic-embed-text-v1.5",
        model_kwargs={"trust_remote_code": True},
    )
    return LangchainEmbeddingsWrapper(embeddings)


def _compute_percentiles(latencies_ms: List[float]) -> Dict[str, int]:
    """
    Calcule les percentiles de latence p50 / p95 / p99.
    Ces valeurs reflètent l'expérience réelle des utilisateurs :
      p50 = temps médian (50% des requêtes sont plus rapides)
      p95 = 95% des requêtes sont sous ce seuil
      p99 = pire cas pratique (1% dépasse cette valeur)
    """
    arr = np.array(latencies_ms)
    return {
        "p50": int(np.percentile(arr, 50)),
        "p95": int(np.percentile(arr, 95)),
        "p99": int(np.percentile(arr, 99)),
    }


# =============================================================================
#  EXÉCUTION DES QUESTIONS SUR UN CHATBOT
# =============================================================================

async def _run_questions_on_chatbot(
    chatbot: RAGChatbot,
    questions: List[Dict[str, Any]],
    model_name: str,
) -> Tuple[List[Dict], List[float]]:
    
    records   = []
    latencies = []

    for i, item in enumerate(questions):
        logger.info(
            f"[{model_name}] Question {i + 1}/{len(questions)}: "
            f"{item['question'][:70]}..."
        )
        try:
            start_time = time.perf_counter()

            res = await chatbot.achat(
                query=item["question"],
                # Session unique par question pour éviter que la mémoire Redis
                # d'une question pollue la suivante.
                session_id=f"benchmark_{abs(hash(item['question']))}",
                user_role=item.get("user_role", "student"),
            )

            elapsed_ms = (time.perf_counter() - start_time) * 1000

            # ── Extraction du contexte textuel ─────────────────────────────
            # RAGAS a besoin du texte brut des chunks (pas juste les métadonnées).
            # chain.py expose maintenant "page_content" dans chaque source.
            contexts = [
                src.get("page_content", "")
                for src in res.get("sources", [])
                if src.get("page_content", "").strip()
            ]

            # Si aucun chunk n'a été récupéré, on met une chaîne vide pour
            # que RAGAS puisse quand même calculer les métriques (scores = 0).
            if not contexts:
                logger.warning(
                    f"  ⚠️  Aucun chunk récupéré pour cette question. "
                    "Vérifie que Qdrant contient des documents indexés."
                )
                contexts = [""]

            records.append({
                "question":     item["question"],
                "answer":       res["answer"],
                "contexts":     contexts,
                "ground_truth": item["ground_truth"],
            })
            latencies.append(elapsed_ms)

            logger.info(
                f"  ✓ Réponse obtenue en {elapsed_ms:.0f}ms "
                f"({len(contexts)} chunks contexte)"
            )

        except Exception as e:
            logger.error(f"  ✗ Erreur sur la question {i + 1}: {e}")
            # On garde l'entrée avec une réponse d'erreur pour ne pas casser
            # l'alignement des indices avec le dataset.
            records.append({
                "question":     item["question"],
                "answer":       f"[ERREUR D'INFÉRENCE: {str(e)}]",
                "contexts":     [""],
                "ground_truth": item["ground_truth"],
            })
            latencies.append(0.0)

    return records, latencies


# =============================================================================
#  CALCUL DES MÉTRIQUES RAGAS
# =============================================================================

def _evaluate_with_ragas(records: List[Dict]) -> Dict[str, float]:
    
    # Construction du dataset HuggingFace (format attendu par RAGAS 0.1.x)
    dataset = Dataset.from_dict({
        "question":     [r["question"]     for r in records],
        "answer":       [r["answer"]       for r in records],
        "contexts":     [r["contexts"]     for r in records],
        "ground_truth": [r["ground_truth"] for r in records],
    })

    logger.info("  Chargement du LLM juge et des embeddings pour RAGAS...")
    judge_llm        = _build_judge_llm()
    judge_embeddings = _build_judge_embeddings()

    # ── Configuration du LLM juge sur chaque métrique ─────────────────────
    # Chaque métrique RAGAS utilise le LLM pour ses jugements internes.
    faithfulness.llm            = judge_llm
    answer_relevancy.llm        = judge_llm
    answer_relevancy.embeddings = judge_embeddings   # AR utilise aussi les embeddings
    context_precision.llm       = judge_llm
    context_recall.llm          = judge_llm

    logger.info("  Évaluation RAGAS en cours (peut prendre quelques minutes)...")

    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
    )

    return {
        "faithfulness":      round(float(result["faithfulness"]),      4),
        "answer_relevancy":  round(float(result["answer_relevancy"]),  4),
        "context_precision": round(float(result["context_precision"]), 4),
        "context_recall":    round(float(result["context_recall"]),    4),
    }


# =============================================================================
#  BENCHMARK ASYNCHRONE PRINCIPAL
# =============================================================================

async def _run_full_benchmark(job_id: str, results_dict: dict) -> None:
    

    # ── 1. Validation du dataset ──────────────────────────────────────────
    questions = [
        item for item in MANUAL_TEST_DATASET
        if item.get("ground_truth")
        and "REMPLACE" not in item["ground_truth"].upper()
        and item.get("question", "").strip()
    ]

    if not questions:
        results_dict[job_id] = {
            "status": "failed",
            "error": (
                "Le dataset est vide ou contient uniquement des exemples placeholder. "
                "Ouvre benchmarks/test_dataset.py, remplace les ground_truths par "
                "de vraies réponses tirées de tes documents, et relance le benchmark."
            ),
        }
        return

    logger.info(
        f"[Benchmark {job_id}] "
        f"{len(questions)} questions valides — "
        f"{len(MANUAL_TEST_DATASET) - len(questions)} placeholders ignorés."
    )

    # ── 2. Initialisation du RAGChatbot partagé ───────────────────────────
    # On instancie une seule fois pour éviter de recharger CLIP (512 MB),
    # le cross-encoder et la connexion Qdrant à chaque modèle.
    logger.info("[Benchmark] Initialisation du RAGChatbot (chargement des modèles)...")
    try:
        chatbot = RAGChatbot()
    except Exception as e:
        results_dict[job_id] = {
            "status": "failed",
            "error": f"Impossible d'initialiser RAGChatbot : {e}",
        }
        return

    all_model_results = []

    # ── 3. Boucle sur chaque modèle ───────────────────────────────────────
    for model_config in MODELS_TO_BENCHMARK:
        model_name = model_config["name"]
        logger.info(f"\n{'─'*60}")
        logger.info(f"[Benchmark] Modèle : {model_name}")
        logger.info(f"{'─'*60}")

        # ── 3a. Swap du LLM ───────────────────────────────────────────────
        # On remplace uniquement le LLM sans toucher aux composants lourds
        # (Qdrant, CLIP, cross-encoder) — économie de temps et de mémoire.
        try:
            chatbot.llm = _build_llm(model_config["provider"], model_config["model"])
            logger.info(f"  LLM chargé : {model_config['provider']}/{model_config['model']}")
        except Exception as e:
            logger.error(f"  ✗ Impossible de charger le LLM {model_name} : {e}")
            all_model_results.append({
                "Model":               model_name,
                "faithfulness":        None,
                "answer_relevancy":    None,
                "context_precision":   None,
                "context_recall":      None,
                "quality_score":       None,
                "p50_latency_ms":      None,
                "p95_latency_ms":      None,
                "p99_latency_ms":      None,
                "questions_evaluated": 0,
                "error":               str(e),
            })
            continue

        # ── 3b. Exécution des questions ───────────────────────────────────
        try:
            records, latencies = await _run_questions_on_chatbot(
                chatbot, questions, model_name
            )
        except Exception as e:
            logger.error(f"  ✗ Erreur lors de l'exécution des questions : {e}")
            continue

        # ── 3c. Calcul des métriques RAGAS ────────────────────────────────
        # evaluate() est synchrone mais bloquant — acceptable ici car on est
        # dans une tâche de fond sans contrainte de latence.
        try:
            metrics = _evaluate_with_ragas(records)
        except Exception as e:
            logger.error(f"  ✗ Erreur RAGAS pour {model_name} : {e}")
            logger.error(
                "  💡 Vérifie que le juge LLM est accessible "
                f"({JUDGE_PROVIDER}/{JUDGE_MODEL})."
            )
            metrics = {
                "faithfulness":      0.0,
                "answer_relevancy":  0.0,
                "context_precision": 0.0,
                "context_recall":    0.0,
            }

        # ── 3d. Percentiles de latence ────────────────────────────────────
        valid_latencies = [l for l in latencies if l > 0]
        if valid_latencies:
            perf = _compute_percentiles(valid_latencies)
        else:
            perf = {"p50": 0, "p95": 0, "p99": 0}

        # ── Score qualité global ──────────────────────────────────────────
        # Formule : 30% fidélité + 30% pertinence réponse + 20% précision contexte
        #           + 20% rappel contexte
        # Seuil MVP : ≥ 0.70 (défini dans le README)
        quality_score = round(
            0.3 * metrics["faithfulness"]
            + 0.3 * metrics["answer_relevancy"]
            + 0.2 * metrics["context_precision"]
            + 0.2 * metrics["context_recall"],
            4,
        )

        all_model_results.append({
            "Model":               model_name,
            "faithfulness":        metrics["faithfulness"],
            "answer_relevancy":    metrics["answer_relevancy"],
            "context_precision":   metrics["context_precision"],
            "context_recall":      metrics["context_recall"],
            "quality_score":       quality_score,
            "p50_latency_ms":      perf["p50"],
            "p95_latency_ms":      perf["p95"],
            "p99_latency_ms":      perf["p99"],
            "questions_evaluated": len(records),
        })

        status_icon = "✅" if quality_score >= 0.70 else "⚠️ "
        logger.info(
            f"  {status_icon} {model_name} — "
            f"quality={quality_score:.3f} | "
            f"faithfulness={metrics['faithfulness']:.3f} | "
            f"p50={perf['p50']}ms p95={perf['p95']}ms"
        )

    # ── 4. Sauvegarde des résultats ───────────────────────────────────────
    if not all_model_results:
        results_dict[job_id] = {
            "status": "failed",
            "error":  "Aucun modèle n'a pu être évalué. Consulte les logs.",
        }
        return

    os.makedirs("benchmarks/results", exist_ok=True)
    df = pd.DataFrame(all_model_results)
    df.to_csv("benchmarks/results/benchmark_results.csv", index=False)
    df.to_html("benchmarks/results/benchmark_results.html", index=False)

    logger.info(
        f"\n[Benchmark {job_id}] ✅ Terminé. "
        f"Résultats dans benchmarks/results/"
    )

    results_dict[job_id] = {
        "status":              "completed",
        "table":               df.to_dict(orient="records"),
        "questions_evaluated": len(questions),
        "judge_llm":           f"{JUDGE_PROVIDER}/{JUDGE_MODEL}",
        "models_evaluated":    len(all_model_results),
    }


# =============================================================================
#  POINT D'ENTRÉE — appelé par FastAPI (POST /benchmark/run)
# =============================================================================

def run_benchmark_task(job_id: str, results_dict: dict) -> None:

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        loop.run_until_complete(_run_full_benchmark(job_id, results_dict))
    except Exception as e:
        logger.exception(f"[Benchmark {job_id}] Erreur fatale : {e}")
        results_dict[job_id] = {
            "status": "failed",
            "error":  str(e),
        }
    finally:
        loop.close()
