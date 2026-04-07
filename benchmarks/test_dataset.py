"""
=============================================================================
 DATASET DE TEST — benchmarks/test_dataset.py
=============================================================================
C'EST ICI QUE TU AJOUTES TES QUESTIONS MANUELLEMENT.

Structure de chaque entrée du dataset :
    {
        "question"    : str — la question telle qu'un étudiant la poserait
        "ground_truth": str — la VRAIE réponse attendue, tirée de tes documents
        "user_role"   : str — "student" | "staff" | "admin"  (défaut : "student")
    }

─────────────────────────────────────────────────────────────────────────────
 CONSEILS POUR DE BONNES MÉTRIQUES RAGAS
─────────────────────────────────────────────────────────────────────────────
  ✅ Vise au moins 30 questions pour avoir des scores statistiquement fiables.
  ✅ Couvre plusieurs catégories : inscriptions, examens, services, règlements,
     frais, diplômes, contacts, calendrier académique...
  ✅ Inclus des questions en français ET en arabe (ton système est trilingue).
  ✅ La ground_truth doit être factuelle, précise, et extraite de tes vrais
     documents universitaires (pas inventée).
  ✅ Mélange des questions simples (1 fait) et complexes (plusieurs étapes).
  ✅ Inclus quelques questions "pièges" auxquelles le chatbot ne devrait PAS
     répondre (hors périmètre), pour tester le refus correct.

  ❌ N'invente pas les ground_truths — elles doivent correspondre exactement
     à ce que contiennent tes documents ingérés dans Qdrant.
  ❌ Évite les questions trop vagues ("Parle-moi de l'université") — RAGAS
     mesure la précision factuelle, pas la qualité rédactionnelle.

─────────────────────────────────────────────────────────────────────────────
 FORMAT DE LA GROUND TRUTH
─────────────────────────────────────────────────────────────────────────────
  La ground_truth n'a pas besoin d'être la réponse exacte mot-pour-mot.
  Elle doit contenir tous les FAITS nécessaires pour répondre à la question.

  Exemple :
    question     : "Quelle est la date limite d'inscription au semestre 1 ?"
    ground_truth : "La date limite d'inscription au semestre 1 est le 15 octobre.
                    Les inscriptions se font au Bureau de la Scolarité, bâtiment A."

─────────────────────────────────────────────────────────────────────────────
 COMMENT UTILISER CE FICHIER
─────────────────────────────────────────────────────────────────────────────
  1. Remplace les exemples ci-dessous par tes vraies questions.
  2. Lance le benchmark via : POST http://localhost:8000/benchmark/run
  3. Récupère les résultats via : GET /benchmark/results/{job_id}
  4. Les fichiers CSV et HTML sont sauvegardés dans benchmarks/results/

  Le benchmark ignore automatiquement toute entrée dont la ground_truth
  contient encore le mot "REMPLACE" (placeholder de départ).
=============================================================================
"""

# =============================================================================
#  TON DATASET ICI — REMPLACE LES EXEMPLES PAR TES VRAIES QUESTIONS
# =============================================================================

MANUAL_TEST_DATASET = [

    # ─── CATÉGORIE : INSCRIPTIONS ─────────────────────────────────────────────

    {
        "question": "Quelles sont les dates limites d'inscription pour le semestre d'automne ?",
        "ground_truth": "REMPLACE PAR LA VRAIE RÉPONSE TIRÉE DE TES DOCUMENTS",
        "user_role": "student",
    },
    {
        "question": "Quels sont les documents requis pour l'inscription en première année de licence ?",
        "ground_truth": "REMPLACE PAR LA VRAIE RÉPONSE TIRÉE DE TES DOCUMENTS",
        "user_role": "student",
    },
    {
        "question": "Comment se déroule la réinscription pour les étudiants déjà inscrits ?",
        "ground_truth": "REMPLACE PAR LA VRAIE RÉPONSE TIRÉE DE TES DOCUMENTS",
        "user_role": "student",
    },

    # ─── CATÉGORIE : EXAMENS ──────────────────────────────────────────────────

    {
        "question": "Comment faire appel d'une note d'examen ?",
        "ground_truth": "REMPLACE PAR LA VRAIE RÉPONSE TIRÉE DE TES DOCUMENTS",
        "user_role": "student",
    },
    {
        "question": "Quel est le règlement concernant les absences aux examens ?",
        "ground_truth": "REMPLACE PAR LA VRAIE RÉPONSE TIRÉE DE TES DOCUMENTS",
        "user_role": "student",
    },
    {
        "question": "Comment consulter ses résultats d'examens en ligne ?",
        "ground_truth": "REMPLACE PAR LA VRAIE RÉPONSE TIRÉE DE TES DOCUMENTS",
        "user_role": "student",
    },

    # ─── CATÉGORIE : SERVICES UNIVERSITAIRES ─────────────────────────────────

    {
        "question": "Comment obtenir une attestation de scolarité ?",
        "ground_truth": "REMPLACE PAR LA VRAIE RÉPONSE TIRÉE DE TES DOCUMENTS",
        "user_role": "student",
    },
    {
        "question": "Quelles sont les heures d'ouverture de la bibliothèque universitaire ?",
        "ground_truth": "REMPLACE PAR LA VRAIE RÉPONSE TIRÉE DE TES DOCUMENTS",
        "user_role": "student",
    },

    # ─── CATÉGORIE : ARABE (test multilingue) ────────────────────────────────

    {
        "question": "ما هي مواعيد التسجيل في الفصل الدراسي الأول؟",
        "ground_truth": "REMPLACE PAR LA VRAIE RÉPONSE TIRÉE DE TES DOCUMENTS",
        "user_role": "student",
    },
    {
        "question": "كيف يمكنني الحصول على شهادة التسجيل؟",
        "ground_truth": "REMPLACE PAR LA VRAIE RÉPONSE TIRÉE DE TES DOCUMENTS",
        "user_role": "student",
    },

    # ─── CATÉGORIE : HORS PÉRIMÈTRE (le chatbot doit refuser poliment) ────────

    {
        "question": "Quel est le meilleur restaurant près du campus ?",
        "ground_truth": "Cette question est hors du périmètre du chatbot universitaire. "
                        "Le chatbot doit indiquer qu'il ne peut pas répondre à cette question "
                        "et suggérer de contacter le service compétent.",
        "user_role": "student",
    },

    # ─── CONTINUE D'AJOUTER ICI ───────────────────────────────────────────────
    # Objectif : 30 questions minimum
    # Rappel : retire le mot "REMPLACE" de ground_truth une fois que tu as
    #          ajouté la vraie réponse, sinon la question sera ignorée.
    # ─────────────────────────────────────────────────────────────────────────

]
