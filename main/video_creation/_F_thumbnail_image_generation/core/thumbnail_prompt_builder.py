from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

# Master Prompt provided by the user for Tito
_MASTER_TITO_PROMPT = """\
A consistent recurring character named Tito, the official mascot of LingoVerse.

Tito is a charming small orange tabby cat designed in a clean modern 2D cartoon illustration style. He has a warm orange coat with subtle darker orange tabby stripes, a cream-colored muzzle and cream-colored belly, large expressive dark brown eyes, a small rounded pink nose, a tiny friendly mouth, prominent triangular cat ears with soft pink inner ears, and three simple whiskers extending from each side of his face.

Tito has a distinctive rounded head, slightly chubby cheeks, a compact cute body, short rounded paws, and a gently curved striped tail. His proportions are intentionally consistent: relatively large head, compact body, short legs, rounded paws, and a friendly cartoon silhouette.

Tito wears his signature small round glasses with thin dark frames and pale blue reflective lenses. The glasses are an important permanent part of Tito's identity.

Tito's personality is shy but affectionate, curious, intelligent, gentle, playful, and genuinely enthusiastic about helping people learn. His expression should always feel warm, approachable, slightly shy and naturally charming. He is never aggressive, arrogant, intimidating, angry, or excessively excited.

Tito must remain unmistakably the same character in every image. Preserve his exact facial identity, head shape, ear shape, eye placement, glasses, muzzle, orange fur coloration, tabby markings, body proportions, and overall silhouette.

Clean 2D cartoon illustration, polished vector-like shapes, smooth dark outlines, controlled expressive facial features, soft flat colors with subtle shading, crisp edges, professional educational animation aesthetic, modern language-learning brand illustration, charming but not overly childish, no photorealism, no 3D rendering, no realistic fur.

Tito should look like the exact same mascot character appearing repeatedly throughout an established professional YouTube language-learning brand.\
"""


class ThumbnailPromptBuilder:
    """Builds the positive prompt for the thumbnail using the Master Tito Prompt."""

    @staticmethod
    def build_prompt(chalkboard_text: str, language_label: str) -> str:
        """
        Constructs the ComfyUI positive prompt with Tito in a classroom setting
        and the specific expression written on the chalkboard.
        """
        prompt = f"""\
A flawless, exact 1:1 replica of the provided reference image, maintaining the exact same character, the exact same background, identical colors, and identical composition. Do not alter, add, or remove any objects or characters.

The ONLY difference is that the classroom chalkboard MUST clearly display the following exact text:

"{chalkboard_text.upper()}"

Ensure the text is highly legible on the chalkboard. ABSOLUTELY DO NOT change the cat, the background, or any other elements in the scene. The scene must remain identical to the reference image.
"""
        return prompt
