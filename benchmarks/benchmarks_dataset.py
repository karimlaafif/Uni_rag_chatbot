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

]
