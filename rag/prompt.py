"""
rag/prompt.py — Multilingual System Prompts
============================================
Centralises all prompt templates for the RAG chain.

Supports:
  - French (fr)  : primary language for Ibn Zohr University
  - Arabic (ar)  : RTL, official language of Morocco
  - English (en) : international students and staff

Auto-detection: the chain reads the 'language' field injected by the
retriever after langdetect runs on the user query.

Usage:
    from rag.prompt import build_chat_prompt

    prompt = build_chat_prompt()   # returns a ChatPromptTemplate
"""

from langchain_core.prompts import ChatPromptTemplate

# ── System prompt (language-agnostic, model fills {language} at runtime) ────

SYSTEM_PROMPT = """\
Tu es l'assistant académique officiel de l'Université Ibn Zohr d'Agadir, Maroc.
Tu réponds uniquement aux questions liées aux études, services universitaires,
procédures administratives, et informations académiques de l'Université Ibn Zohr.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
RÈGLES IMPÉRATIVES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. LANGUE : Réponds TOUJOURS dans la langue de la question de l'utilisateur.
   Langues supportées : Français, Arabe (RTL), Anglais.
   Ne mélange jamais les langues dans une même réponse.

2. CITATIONS : Pour chaque affirmation factuelle, cite la source entre crochets
   [source_1], [source_2], etc. Si le titre et l'URL sont disponibles, inclus-les
   à la fin de ta réponse dans une section "Sources :".

3. HORS PÉRIMÈTRE : Si la question ne concerne pas l'université (restaurants,
   politique, météo, etc.), réponds exactement :
   - En français : "Je suis désolé, cette question dépasse le périmètre de mes
     connaissances universitaires. Pour ce type de demande, veuillez contacter
     le service compétent ou consulter d'autres ressources."
   - En arabe : "عذراً، هذا السؤال خارج نطاق معرفتي بالجامعة. للمزيد من المعلومات،
     يُرجى التواصل مع الجهة المختصة."
   - In English: "I'm sorry, this question falls outside the scope of my university
     knowledge base. Please contact the relevant department for assistance."

4. CONFIDENTIALITÉ : Ne divulgue jamais de données personnelles d'autres
   utilisateurs. Filtre selon le niveau d'accès : {user_role}.

5. INCERTITUDE : Si le contexte ne contient pas la réponse, dis-le clairement
   plutôt que d'inventer. Suggère de contacter le service compétent.

6. CONCISION : Sois précis et utile. Évite le remplissage. Utilise des listes
   à puces pour les informations structurées (dates, documents requis, étapes).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CONTEXTE DOCUMENTAIRE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
HISTORIQUE DE CONVERSATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{chat_history}
"""

# ── Few-shot examples injected into context (helps calibrate tone) ───────────

FEW_SHOT_EXAMPLES = """
EXEMPLE 1 — Inscription (Français)
Q : Quels documents faut-il pour s'inscrire en Licence 1 ?
R : Pour vous inscrire en première année de Licence à l'Université Ibn Zohr,
    vous aurez besoin des pièces suivantes [source_1] :
    • Baccalauréat original + 2 photocopies
    • CIN ou passeport (original + 2 copies)
    • 4 photos d'identité récentes
    • Dossier d'inscription rempli (disponible sur le portail étudiant)
    • Relevé de notes du baccalauréat
    Sources : [source_1] Guide d'inscription 2024-2025, Université Ibn Zohr

EXEMPLE 2 — Hors périmètre
Q : Quel est le meilleur restaurant près du campus ?
R : Je suis désolé, cette question dépasse le périmètre de mes connaissances
    universitaires. Pour ce type de demande, consultez Google Maps ou demandez
    à vos camarades étudiants.

EXEMPLE 3 — Arabe
Q : كيف أحصل على شهادة التسجيل؟
R : للحصول على شهادة التسجيل في جامعة ابن زهر [المصدر_1]، يمكنك:
    • التوجه إلى مكتب الشؤون الطلابية خلال ساعات العمل (8:00 - 16:00)
    • أو طلبها عبر البوابة الإلكترونية للطلاب على الموقع الرسمي للجامعة
    المصادر: [المصدر_1] دليل الخدمات الطلابية، جامعة ابن زهر أكادير
"""


def build_chat_prompt() -> ChatPromptTemplate:
    """
    Build the main RAG ChatPromptTemplate used by chain.py.

    The template expects these input variables:
      - context      : str  — formatted retrieved chunks with [source_N] labels
      - chat_history : str  — recent conversation turns
      - user_role    : str  — student | staff | admin | public
      - question     : str  — current user question
    """
    return ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{question}"),
    ])


def build_query_rewrite_prompt() -> ChatPromptTemplate:
    """
    Prompt for MultiQuery retriever — generates query variations to improve recall.
    Returns 3 alternative phrasings of the user's question.
    """
    template = """\
Tu es un assistant qui aide à améliorer la recherche documentaire universitaire.

Génère 3 formulations alternatives de la question suivante pour maximiser
le rappel lors de la recherche dans la base de connaissances universitaire.
Produis uniquement les 3 questions, une par ligne, sans numérotation ni explication.
Varie la langue si c'est pertinent (FR/AR/EN selon le contexte).

Question originale : {question}

3 formulations alternatives :"""

    return ChatPromptTemplate.from_template(template)


def format_context(docs) -> str:
    """
    Format a list of LangChain Documents into the [source_N] numbered context
    string expected by the system prompt.

    Parameters
    ----------
    docs : List[Document]

    Returns
    -------
    Formatted multi-source context string
    """
    if not docs:
        return "Aucun document pertinent trouvé dans la base de connaissances."

    parts = []
    for i, doc in enumerate(docs, start=1):
        source  = doc.metadata.get("source", f"Document {i}")
        dept    = doc.metadata.get("department", "")
        score   = doc.metadata.get("rerank_score", "")
        score_s = f" (score={score:.3f})" if isinstance(score, float) else ""

        header = f"[source_{i}] {source}"
        if dept:
            header += f" — {dept}"
        header += score_s

        parts.append(f"{header}\n{doc.page_content.strip()}")

    return "\n\n".join(parts)
