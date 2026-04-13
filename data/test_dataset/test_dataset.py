"""
benchmarks/test_dataset.py — Jeu de données de test manuel pour RAGAS
======================================================================
✅ Toutes les ground_truths sont renseignées avec des réponses réelles
   tirées des documents indexés (Guide de l'étudiant UIZ 2024-2025).
"""

MANUAL_TEST_DATASET = [

    # ─── CATÉGORIE : INSCRIPTIONS ─────────────────────────────────────────────

    {
        "question": "Quelles sont les dates limites d'inscription pour le semestre d'automne ?",
        "ground_truth": (
            "Pour l'année universitaire 2024-2025, les délais d'inscription à l'Université Ibn Zohr sont : "
            "filières à accès ouvert du 15 juillet au 31 août 2024 ; filières sélectives (ENCG, ENSA, EST) "
            "selon les résultats des concours de juin-juillet 2024 ; inscriptions tardives exceptionnelles "
            "jusqu'au 15 septembre 2024. Pour les réinscriptions, la période principale est du 1er juillet "
            "au 15 septembre 2024, et une période exceptionnelle avec pénalité de 100 MAD du 16 au 30 septembre."
        ),
        "user_role": "student",
    },
    {
        "question": "Quels sont les documents requis pour l'inscription en première année de licence ?",
        "ground_truth": (
            "Pour s'inscrire en L1 à l'UIZ, il faut fournir : le Baccalauréat original + 4 photocopies, "
            "le relevé de notes du baccalauréat + 4 copies, la CIN originale + 4 copies, "
            "l'acte de naissance (moins de 3 mois) + 2 copies, 8 photos d'identité récentes (fond blanc 3.5x4.5cm), "
            "le dossier d'inscription rempli (disponible sur www.uiz.ac.ma), "
            "un justificatif de domicile récent. Les étudiants étrangers ajoutent une attestation d'équivalence "
            "du baccalauréat délivrée par le Ministère de l'Éducation Nationale marocain."
        ),
        "user_role": "student",
    },
    {
        "question": "Comment se déroule la réinscription pour les étudiants déjà inscrits ?",
        "ground_truth": (
            "La réinscription à l'UIZ se fait en 5 étapes : 1) Se connecter à portail.uiz.ac.ma, "
            "2) Vérifier et mettre à jour ses informations, 3) Générer le bordereau de paiement, "
            "4) Payer les frais en ligne ou au bureau, 5) Imprimer la confirmation. "
            "Délais : période principale du 1er juillet au 15 septembre 2024 ; période exceptionnelle "
            "avec pénalité de 100 MAD du 16 au 30 septembre. Après le 30 septembre, dérogation du Doyen requise. "
            "Condition de passage en L2 : avoir validé au moins 36 crédits sur 60."
        ),
        "user_role": "student",
    },

    # ─── CATÉGORIE : EXAMENS ──────────────────────────────────────────────────

    {
        "question": "Comment faire appel d'une note d'examen ?",
        "ground_truth": (
            "La procédure de réclamation de note à l'UIZ comporte 3 étapes : "
            "1) Demande de consultation de copie dans les 5 jours ouvrables après la publication des résultats, "
            "au bureau du Chef de Département avec la carte d'étudiant. "
            "2) Recours en révision dans les 5 jours suivant la consultation si une erreur est confirmée, "
            "via formulaire de recours + photocopie de la copie annotée. "
            "3) La Commission Pédagogique statue dans les 10 jours et notifie par email. "
            "Aucun recours n'est accepté après les délais. Les notes de CC ne sont pas révisables "
            "sauf erreur de calcul prouvée."
        ),
        "user_role": "student",
    },
    {
        "question": "Quel est le règlement concernant les absences aux examens ?",
        "ground_truth": (
            "À l'UIZ, la présence aux examens est obligatoire. L'absence non justifiée entraîne la note zéro (0/20). "
            "Les absences justifiées acceptées sont : certificat médical (dans les 48h), décès d'un parent de 1er degré, "
            "convocation officielle, accouchement. Procédure : informer scolarite@uiz.ac.ma immédiatement, "
            "puis déposer le justificatif original dans les 5 jours ouvrables. "
            "Retard de moins de 15 min : accès autorisé ; plus de 15 min : accès refusé et note zéro."
        ),
        "user_role": "student",
    },
    {
        "question": "Comment consulter ses résultats d'examens en ligne ?",
        "ground_truth": (
            "Les résultats sont consultables sur portail.uiz.ac.ma (login = numéro d'apogée, "
            "mot de passe initial = date de naissance JJMMAAAA). En cas d'oubli : support@uiz.ac.ma. "
            "Calendrier de publication 2024-2025 : S1 le 10 février 2025, S2 le 5 juillet 2025, "
            "rattrapage le 1er octobre 2025."
        ),
        "user_role": "student",
    },
    {
        "question": "When are the exam periods at Ibn Zohr University for 2024-2025?",
        "ground_truth": (
            "Exam periods at Ibn Zohr University 2024-2025: Semester 1 finals January 6-20 2025 (results February 10); "
            "Semester 2 finals June 2-16 2025 (results July 5); Makeup session September 8-22 2025 (results October 1). "
            "Assessment: 40% continuous assessment + 60% final exam. Passing grade: 10/20."
        ),
        "user_role": "student",
    },

    # ─── CATÉGORIE : SERVICES UNIVERSITAIRES ─────────────────────────────────

    {
        "question": "Comment obtenir une attestation de scolarité ?",
        "ground_truth": (
            "Pour obtenir une attestation de scolarité à l'UIZ : en personne au Service de la Scolarité "
            "avec la carte d'étudiant (délivrance immédiate) ; ou en ligne via portail.uiz.ac.ma "
            "(rubrique Services → Attestations, délai 48h). Format PDF officiel avec QR code. "
            "Gratuite jusqu'à 3 exemplaires par an. Horaires scolarité : Lun-Ven 8h30-12h30 et 14h30-16h30, Sam 9h-12h."
        ),
        "user_role": "student",
    },
    {
        "question": "Quelles sont les heures d'ouverture de la bibliothèque universitaire ?",
        "ground_truth": (
            "La BCUIZ (Bibliothèque Centrale UIZ) est ouverte : Lun-Ven 8h00-21h00, Sam 8h00-18h00. "
            "Fermée les dimanches et jours fériés, sauf pendant les examens (ouverture dim 9h-17h). "
            "Pendant les vacances : Lun-Ven 8h30-16h00. "
            "Services : prêt domicile (3 livres, 14 jours), salle lecture 200 places, salle groupe 50 places, "
            "Wi-Fi gratuit, 60 postes PC, accès JSTOR/ScienceDirect/Cairn. "
            "Contact : bibliotheque@uiz.ac.ma, +212 528 22 06 94."
        ),
        "user_role": "student",
    },
    {
        "question": "Quels sont les frais de scolarité à l'Université Ibn Zohr ?",
        "ground_truth": (
            "Frais de scolarité UIZ (université publique marocaine) : Licence 400 MAD/an ; "
            "Master 600 MAD/an ; Doctorat 400 MAD/an ; filières sélectives ENCG/ENSA/EST 6000 MAD/an. "
            "Paiement : en ligne via portail (carte bancaire/CMI), chèque à l'ordre du Régisseur UIZ, "
            "virement bancaire, ou espèces à la scolarité. Couverture CNOPS incluse."
        ),
        "user_role": "student",
    },
    {
        "question": "How do I access the student portal and what can I do there?",
        "ground_truth": (
            "The UIZ student portal is at portail.uiz.ac.ma (available 24/7). "
            "Login: apogee number (on student card); initial password: date of birth (DDMMYYYY). "
            "Forgot password: email support@uiz.ac.ma. Services available: grades and results, timetable, "
            "enrollment certificate download (certified PDF with QR code), transcript requests, "
            "annual re-enrollment, tuition fee payment, institutional email (@uiz.ac.ma), "
            "and Moodle e-learning access (elearning.uiz.ac.ma)."
        ),
        "user_role": "student",
    },

    # ─── CATÉGORIE : ARABE (test multilingue) ────────────────────────────────

    {
        "question": "ما هي مواعيد التسجيل في الفصل الدراسي الأول؟",
        "ground_truth": (
            "مواعيد التسجيل في جامعة ابن زهر 2024-2025: الشعب المفتوحة من 15 يوليو إلى 31 غشت 2024؛ "
            "الشعب الانتقائية (ENCG وENSA وEST) حسب نتائج المباريات يونيو-يوليو 2024؛ "
            "التسجيلات المتأخرة للحالات الاستثنائية حتى 15 شتنبر 2024. "
            "إعادة التسجيل: الفترة الرئيسية 1 يوليو - 15 شتنبر 2024، الفترة الاستثنائية (غرامة 100 درهم) 16-30 شتنبر."
        ),
        "user_role": "student",
    },
    {
        "question": "كيف يمكنني الحصول على شهادة التسجيل؟",
        "ground_truth": (
            "للحصول على شهادة التسجيل في جامعة ابن زهر: حضورياً بمصلحة التسجيل مع بطاقة الطالب (تسليم فوري)، "
            "أو إلكترونياً عبر portail.uiz.ac.ma (الخدمات ← الشهادات) في 48 ساعة. "
            "مجانية حتى 3 نسخ/سنة، بصيغة PDF رسمي مع رمز QR. "
            "ساعات المصلحة: الاثنين-الجمعة 8:30-12:30 و14:30-16:30، السبت 9:00-12:00."
        ),
        "user_role": "student",
    },
    {
        "question": "ما هي ساعات عمل المكتبة المركزية لجامعة ابن زهر؟",
        "ground_truth": (
            "ساعات عمل المكتبة المركزية لجامعة ابن زهر: الاثنين-الجمعة 8:00-21:00، السبت 8:00-18:00. "
            "مغلقة الأحد والعطل الرسمية، إلا خلال الامتحانات (فتح الأحد 9:00-17:00). "
            "خلال العطل: الاثنين-الجمعة 8:30-16:00. "
            "الخدمات: إعارة منزلية (3 كتب، 14 يوماً)، قاعة هادئة 200 مقعد، قاعة جماعية 50 مقعد، Wi-Fi مجاني."
        ),
        "user_role": "student",
    },
    {
        "question": "ما هي رسوم التسجيل في جامعة ابن زهر؟",
        "ground_truth": (
            "رسوم التسجيل في جامعة ابن زهر (جامعة عمومية): الإجازة 400 درهم/سنة؛ الماستر 600 درهم/سنة؛ "
            "الدكتوراه 400 درهم/سنة؛ الشعب الانتقائية ENCG/ENSA/EST 6000 درهم/سنة. "
            "طرق الدفع: عبر البوابة الإلكترونية، شيك بنكي، تحويل بنكي، أو نقداً بمصلحة التسجيل. "
            "التغطية الصحية CNOPS مشمولة."
        ),
        "user_role": "student",
    },

    # ─── CATÉGORIE : BOURSES ──────────────────────────────────────────────────

    {
        "question": "Quelles bourses sont disponibles pour les étudiants à l'UIZ ?",
        "ground_truth": (
            "Bourses disponibles à l'Université Ibn Zohr : "
            "1) Bourse Nationale d'Études : 750 MAD/mois (~9 mois/an) pour étudiants à revenus modestes "
            "avec bons résultats académiques. Dépôt dossier : juillet-septembre. "
            "2) Bourse d'Excellence : 1 500 MAD/mois pour mention Très Bien en Licence, attribution automatique. "
            "3) Aide d'Urgence : jusqu'à 3 000 MAD (unique) pour situations exceptionnelles, "
            "dossier au BOS (bos@uiz.ac.ma)."
        ),
        "user_role": "student",
    },

    # ─── CATÉGORIE : RÉSIDENCES ───────────────────────────────────────────────

    {
        "question": "Comment postuler pour une chambre en résidence universitaire ?",
        "ground_truth": (
            "Pour postuler à une résidence UIZ : résider à +50 km d'Agadir, revenu familial ≤ 4000 MAD/mois. "
            "Retirer le dossier au BOS ou sur le portail, le déposer avant le 30 juin. Résultats fin août. "
            "4 cités disponibles : Nord (800 places, mixte), Sud (500, femmes), Est (400, hommes), ENSA (300, mixte). "
            "Frais (repas inclus) : chambre simple 400 MAD/mois, chambre double 250 MAD/mois/étudiant."
        ),
        "user_role": "student",
    },

    # ─── CATÉGORIE : DISCIPLINE ───────────────────────────────────────────────

    {
        "question": "Quelles sont les sanctions en cas de fraude à l'examen ?",
        "ground_truth": (
            "Sanctions pour fraude aux examens à l'UIZ : 1ère infraction : note zéro + avertissement écrit. "
            "2ème infraction : exclusion de la session d'examens. Fraude grave (substitution d'identité, "
            "fraude organisée) : exclusion définitive + signalement aux autorités. "
            "Pour le plagiat : taux maximal 15% (vérifié par Compilatio), sanction : note zéro + "
            "convocation devant la Commission Disciplinaire."
        ),
        "user_role": "student",
    },

    # ─── CATÉGORIE : HORS PÉRIMÈTRE ──────────────────────────────────────────

    {
        "question": "Quel est le meilleur restaurant près du campus ?",
        "ground_truth": (
            "Cette question est hors du périmètre du chatbot universitaire. "
            "Le chatbot doit indiquer poliment qu'il ne peut répondre qu'aux questions liées "
            "aux études et services universitaires, et suggérer de consulter d'autres ressources."
        ),
        "user_role": "student",
    },
    {
        "question": "What is the weather like in Agadir?",
        "ground_truth": (
            "This question falls outside the university chatbot's scope. "
            "The chatbot should politely decline and indicate it can only answer questions "
            "related to university studies, services, and academic matters."
        ),
        "user_role": "student",
    },
]
