"""
Usage dans n'importe quel module :
    from shared_models import get_clip_model

    clip_model, clip_preprocess, clip_tokenizer = get_clip_model()
"""

import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# ── État interne du singleton ─────────────────────────────────────────────────
# Ces variables sont au niveau module : une seule instance par processus Python.
_clip_model       = None
_clip_preprocess  = None
_clip_tokenizer   = None


def get_clip_model():
    """
    Retourne l'instance partagée de CLIP (ViT-B-32, poids OpenAI).

    Premier appel  → charge le modèle en mémoire (~600 MB VRAM si GPU dispo)
    Appels suivants → retourne immédiatement l'instance déjà en mémoire

    Retourne
    --------
    (clip_model, clip_preprocess, clip_tokenizer)
    """
    global _clip_model, _clip_preprocess, _clip_tokenizer

    if _clip_model is None:
        logger.info(
            "Chargement de CLIP ViT-B-32 (premier appel — ~600 MB)... "
            "Les appels suivants seront instantanés."
        )
        import open_clip
        _clip_model, _, _clip_preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="openai"
        )
        _clip_tokenizer = open_clip.get_tokenizer("ViT-B-32")
        logger.info("CLIP chargé et mis en cache (singleton).")
    else:
        logger.debug("CLIP déjà en mémoire — réutilisation du singleton.")

    return _clip_model, _clip_preprocess, _clip_tokenizer
