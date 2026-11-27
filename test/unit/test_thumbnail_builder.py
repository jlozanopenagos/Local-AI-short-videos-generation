"""
test/unit/test_thumbnail_builder.py — Unit tests for Stage F chalkboard thumbnail rendering and prompt construction.
"""
import tempfile
import unittest
from pathlib import Path
# pyrefly: ignore[missing-import]
from PIL import Image, ImageDraw

# pyrefly: ignore [missing-import]
from video_creation._F_thumbnail_image_generation.core.thumbnail_renderer import (
    clean_thumbnail_title,
    detect_chalkboard_bounds,
    extract_thumbnail_title,
    render_thumbnail_chalkboard,
    sanitize_thumbnail_title,
)


class TestThumbnailChalkboardRenderer(unittest.TestCase):
    def test_clean_thumbnail_title_preserves_stress_and_fixes_quotes(self):
        """Verify heteronym stress casing is preserved and trailing unmatched quotes are closed."""
        self.assertEqual(
            clean_thumbnail_title("REcord vs reCORD: The Native Secret"),
            "REcord vs reCORD: The Native Secret",
        )
        self.assertEqual(
            clean_thumbnail_title("The Secret to Saying 'Piece of Cake"),
            "The Secret to Saying 'Piece of Cake'",
        )

    def test_extract_thumbnail_title_prioritizes_script_title(self):
        """Verify extract_thumbnail_title uses content_metadata.script.title with fallback to target_expression."""
        state_with_title = {
            "content_metadata": {
                "target_expression": "Break a leg",
                "script": {"title": "The Secret Theater Phrase: Break a Leg"},
            }
        }
        self.assertEqual(
            extract_thumbnail_title(state_with_title),
            "The Secret Theater Phrase: Break a Leg",
        )

        state_fallback = {
            "content_metadata": {
                "target_expression": "Break a leg",
            }
        }
        self.assertEqual(extract_thumbnail_title(state_fallback), "Break a leg")

    def test_detect_chalkboard_bounds_in_synthetic_thumbnail(self):
        with Image.new("RGB", (576, 1024), "#af8761") as image:
            ImageDraw.Draw(image).rectangle((65, 100, 515, 550), fill="#285640")
            x1, y1, x2, y2 = detect_chalkboard_bounds(image)
            self.assertGreater(x2 - x1, 300)
            self.assertGreater(y2 - y1, 200)
            self.assertLess(y2, 820)

    def test_render_thumbnail_chalkboard_creates_576x1024_image(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            model_path = Path(tmp_dir) / "model.png"
            Image.new("RGB", (576, 1024), "#285640").save(model_path)
            dest_colon = Path(tmp_dir) / "thumb_colon.png"
            out1 = render_thumbnail_chalkboard(
                model_path, "The Secret Theater Phrase: Break a Leg", dest_colon
            )
            self.assertTrue(out1.exists())
            with Image.open(out1) as im1:
                self.assertEqual(im1.size, (576, 1024))

            dest_single = Path(tmp_dir) / "thumb_single.png"
            out2 = render_thumbnail_chalkboard(
                model_path, "STOP Saying OBject vs obJECT Wrong!", dest_single
            )
            self.assertTrue(out2.exists())
            with Image.open(out2) as im2:
                self.assertEqual(im2.size, (576, 1024))


    def test_sanitize_thumbnail_title_latin_languages(self):
        """Verify English clichés and leakage are stripped or replaced with clean target expression."""
        # Italian: strip English suffix cliché
        self.assertEqual(
            sanitize_thumbnail_title("In bocca al lupo: The Native Secret", "italian", "In bocca al lupo"),
            "In bocca al lupo",
        )
        # Spanish: strip English suffix cliché
        self.assertEqual(
            sanitize_thumbnail_title("Costar un ojo de la cara: The Native Secret", "spanish", "Costar un ojo de la cara"),
            "Costar un ojo de la cara",
        )
        # French: strip English suffix cliché
        self.assertEqual(
            sanitize_thumbnail_title("Poser un lapin: The Native Secret", "french", "Poser un lapin"),
            "Poser un lapin",
        )
        # Italian: 100% English title replaced with clean target expression title
        self.assertEqual(
            sanitize_thumbnail_title("The Secret Italian Phrase for Good Luck", "italian", "In bocca al lupo"),
            "In bocca al lupo",
        )
        # Already native titles preserved untouched
        self.assertEqual(
            sanitize_thumbnail_title("Poser un Lapin : L'expression des natifs", "french", "Poser un lapin"),
            "Poser un Lapin : L'expression des natifs",
        )
        self.assertEqual(
            sanitize_thumbnail_title("Solo 21 Lettere: Il Segreto dell'Alfabeto Italiano", "italian", "L'alfabeto italiano"),
            "Solo 21 Lettere: Il Segreto dell'Alfabeto Italiano",
        )
        # English scripts remain untouched
        self.assertEqual(
            sanitize_thumbnail_title("Break a leg: The Native Secret", "english", "Break a leg"),
            "Break a leg: The Native Secret",
        )

    def test_clean_thumbnail_and_sanitize_title_strip_category_prefixes(self):
        """Leading video-type labels (Quiz:, In Action:, Fun Fact:, etc.) are stripped everywhere."""
        # pyrefly: ignore[missing-import]
        from video_creation._A_video_scripts.core.metadata_builder import sanitize_title

        cases = [
            ("Quiz: Break a leg", "Break a leg"),
            ("Quiz : Poser un lapin", "Poser un lapin"),
            ("Game: PREsent vs preSENT", "PREsent vs preSENT"),
            ("Expression: Break a leg", "Break a leg"),
            ("Expresión: Tomar el pelo", "Tomar el pelo"),
            ("Fun Fact: Silent Letters", "Silent Letters"),
            ("Dato Curioso: Signos invertidos", "Signos invertidos"),
            ("Roleplay: At the Cafe", "At the Cafe"),
            ("In Action: Break a leg", "Break a leg"),
            ("En Acción: Estar frito", "Estar frito"),
            ("En Action : Tomber dans les pommes", "Tomber dans les pommes"),
            ("In Azione: Avere le mani bucate", "Avere le mani bucate"),
            ("Origin: Ojalá", "Ojalá"),
            ("Origen: Sobremesa", "Sobremesa"),
            ("Origine: Ciao", "Ciao"),
            ("[Quiz] Avere le mani bucate", "Avere le mani bucate"),
        ]
        for raw, expected in cases:
            self.assertEqual(clean_thumbnail_title(raw), expected)
            self.assertEqual(sanitize_title(raw), expected)
            self.assertEqual(
                extract_thumbnail_title({"content_metadata": {"script": {"title": raw}}}),
                expected,
            )

        # Mid-title natural words must NOT be stripped
        self.assertEqual(
            clean_thumbnail_title("Poser un Lapin : L'expression des natifs"),
            "Poser un Lapin : L'expression des natifs",
        )
        self.assertEqual(
            sanitize_title("Poser un Lapin : L'expression des natifs"),
            "Poser un Lapin : L'expression des natifs",
        )


class TestMasterThumbnailTemplateMatrix(unittest.TestCase):
    def test_resolve_all_20_canonical_master_templates(self):
        # pyrefly: ignore[missing-import]
        from config import THUMBNAIL_MODELS_DIR
        # pyrefly: ignore[missing-import]
        from video_creation._F_thumbnail_image_generation.service import resolve_thumbnail_templates

        resolved_paths = set()
        for lang in ("english", "french", "italian"):
            for cat in ("expression", "game", "roleplay", "fun_facts"):
                entries = resolve_thumbnail_templates(lang, cat, THUMBNAIL_MODELS_DIR)
                self.assertEqual(len(entries), 1, f"{lang}/{cat} -> {entries}")
                variant, path = entries[0]
                self.assertIsNone(variant)
                self.assertEqual(path.name, "template.png")
                self.assertTrue(path.is_file(), path)
                resolved_paths.add(path.resolve())

        for cat in ("expression", "game", "roleplay", "fun_facts"):
            entries = resolve_thumbnail_templates("spanish", cat, THUMBNAIL_MODELS_DIR)
            self.assertEqual([v for v, _ in entries], ["latam", "spain"])
            for variant, path in entries:
                self.assertEqual(path.name, f"{variant}.png")
                self.assertTrue(path.is_file(), path)
                resolved_paths.add(path.resolve())

        self.assertEqual(len(resolved_paths), 20)

    def test_generate_thumbnail_single_and_dual_spanish_variants(self):
        from unittest.mock import MagicMock, patch
        # pyrefly: ignore[missing-import]
        from config import THUMBNAIL_MODELS_DIR
        # pyrefly: ignore[missing-import]
        from video_creation._F_thumbnail_image_generation.service import generate_thumbnail_for_script

        mock_sm = MagicMock()
        with tempfile.TemporaryDirectory() as tmp:
            out_base = Path(tmp)

            # English Game -> 1 thumbnail.png
            en_state = {
                "id": "EG01",
                "content_metadata": {
                    "language": "english",
                    "video_type": "game",
                    "script": {"title": "Theater Superstitions: Break a Leg!"},
                },
                "status": {},
                "assets": {},
            }
            with patch(
                "video_creation._F_thumbnail_image_generation.service.get_script_output_dir",
                side_effect=lambda sid, lang, _b, video_type=None: out_base / lang / (video_type or "default") / f"script_{sid}",
            ):
                ok_en = generate_thumbnail_for_script(
                    en_state, state_mgr=mock_sm, base_dir=out_base, input_images_dir=THUMBNAIL_MODELS_DIR
                )
            self.assertTrue(ok_en)
            en_thumb = Path(en_state["assets"]["thumbnail_path"])
            self.assertEqual(en_thumb.name, "thumbnail.png")
            self.assertTrue(en_thumb.is_file())
            self.assertNotIn("thumbnail_variants", en_state["assets"])
            with Image.open(en_thumb) as im_en:
                self.assertEqual(im_en.size, (576, 1024))

            # Spanish scripts across all 4 categories -> 2 distinct PNGs (LatAm + Spain)
            for sid, vtype, title in (
                ("SE01", "expression", "Tomar el pelo: Cómo se usa"),
                ("SG01", "game", "Desafío Español: ¿Qué Significa?"),
                ("SR01", "roleplay", "En el Restaurante"),
                ("SF01", "fun_facts", "Curiosidad del Español: El Origen"),
            ):
                with self.subTest(script_id=sid, video_type=vtype):
                    es_state = {
                        "id": sid,
                        "content_metadata": {
                            "language": "spanish",
                            "video_type": vtype,
                            "script": {"title": title},
                        },
                        "status": {},
                        "assets": {},
                    }
                    with patch(
                        "video_creation._F_thumbnail_image_generation.service.get_script_output_dir",
                        side_effect=lambda s, lang, _b, video_type=None: out_base / lang / (video_type or "default") / f"script_{s}",
                    ):
                        ok_es = generate_thumbnail_for_script(
                            es_state, state_mgr=mock_sm, base_dir=out_base, input_images_dir=THUMBNAIL_MODELS_DIR
                        )
                    self.assertTrue(ok_es)
                    variants = es_state["assets"]["thumbnail_variants"]
                    self.assertEqual(sorted(variants.keys()), ["latam", "spain"])
                    latam_p = Path(variants["latam"])
                    spain_p = Path(variants["spain"])
                    self.assertEqual(latam_p.name, "thumbnail_latam.png")
                    self.assertEqual(spain_p.name, "thumbnail_spain.png")
                    self.assertTrue(latam_p.is_file() and spain_p.is_file())
                    self.assertEqual(es_state["assets"]["thumbnail_path"], str(latam_p))
                    self.assertNotEqual(latam_p.read_bytes(), spain_p.read_bytes())
                    with Image.open(latam_p) as il, Image.open(spain_p) as isp:
                        self.assertEqual(il.size, (576, 1024))
                        self.assertEqual(isp.size, (576, 1024))

    def test_category_text_stays_strictly_inside_panel_bounds_preserving_artwork(self):
        # pyrefly: ignore[missing-import]
        from PIL import ImageChops
        # pyrefly: ignore[missing-import]
        from config import THUMBNAIL_MODELS_DIR
        # pyrefly: ignore[missing-import]
        from video_creation._F_thumbnail_image_generation.core.thumbnail_renderer import (
            resolve_panel_bounds,
        )

        with tempfile.TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            for cat in ("expression", "game", "roleplay", "fun_facts"):
                with self.subTest(category=cat):
                    tpl = THUMBNAIL_MODELS_DIR / "english" / cat / "template.png"
                    dest = tmp_dir / f"test_{cat}.png"
                    render_thumbnail_chalkboard(
                        tpl,
                        "Category Focus: Quick Interactive Phrase Title That Wraps Cleanly",
                        dest,
                        target_size=(576, 1024),
                        category=cat,
                    )
                    with Image.open(tpl) as orig, Image.open(dest) as rendered:
                        orig_scaled = orig.convert("RGBA").resize((576, 1024), Image.Resampling.LANCZOS)
                        rendered_rgba = rendered.convert("RGBA")
                        x1, y1, x2, y2 = resolve_panel_bounds(rendered_rgba, category=cat)
                        diff = ImageChops.difference(orig_scaled, rendered_rgba)
                        bbox = diff.getbbox()
                        self.assertIsNotNone(bbox, f"No text pixels rendered for {cat}")
                        dx1, dy1, dx2, dy2 = bbox
                        self.assertGreaterEqual(dx1, x1 - 1)
                        self.assertGreaterEqual(dy1, y1 - 1)
                        self.assertLessEqual(dx2, x2 + 2)
                        self.assertLessEqual(dy2, y2 + 2)

    def test_explicit_thumbnail_title_overrides_script_title_and_preserves_text(self):
        """Explicit content_metadata.thumbnail_title overrides script title and preserves custom colons/English."""
        state = {
            "id": "SR08",
            "content_metadata": {
                "language": "spanish",
                "target_expression": "estar embarazada",
                "thumbnail_title": "Origin: Break the Habit",
                "script": {"title": "En Acción: embarazada"},
            },
        }
        self.assertEqual(extract_thumbnail_title(state), "Origin: Break the Habit")


if __name__ == "__main__":
    unittest.main()
