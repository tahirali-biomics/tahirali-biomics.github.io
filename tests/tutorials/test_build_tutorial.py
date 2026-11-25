import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = ROOT / "scripts" / "tutorials" / "build_tutorial.py"
SPEC = importlib.util.spec_from_file_location("build_tutorial", MODULE_PATH)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)


class BuildTutorialTests(unittest.TestCase):
    def test_style_injection_is_idempotent_and_scoped(self):
        html = '<html><head></head><body class="nav-sidebar"><main></main></body></html>'
        once = builder.insert_style_link(html, "../styles-tutorial-code.css")
        twice = builder.insert_style_link(once, "../styles-tutorial-code.css")
        self.assertEqual(twice.count('id="tutorial-code-style"'), 1)
        self.assertEqual(twice.count("tutorial-code-ready"), 1)
        scripted = builder.insert_script_link(twice, "../tutorial-code-copy.js")
        scripted = builder.insert_script_link(scripted, "../tutorial-code-copy.js")
        self.assertEqual(scripted.count('id="tutorial-code-copy-script"'), 1)

    def test_legacy_body_preserved_inside_quarto_shell(self):
        with self.subTest("extract body content independent of selector/id"):
            parser = builder.BodyExtractor()
            parser.feed('<html><body><div class="section level2"><h2>Results</h2><img src="data:image/png;base64,AA=="></div></body></html>')
            result = "".join(parser.parts)
            self.assertIn('class="section level2"', result)
            self.assertIn('data:image/png;base64,AA==', result)

    def test_figure_map_requires_unique_exact_anchor_and_keeps_source_immutable(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "lesson.qmd"
            copied = root / "copy.qmd"
            figure = root / "figure.png"
            mapping = root / "figures.json"
            source.write_text("An exact caption point.\n", encoding="utf-8")
            copied.write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
            figure.write_bytes(b"png")
            mapping.write_text(json.dumps([{"after": "An exact caption point.", "image": "figure.png", "caption": "Existing output"}]), encoding="utf-8")
            builder.inject_figures(copied, source, mapping)
            self.assertEqual(source.read_text(encoding="utf-8"), "An exact caption point.\n")
            self.assertIn("![Existing output](figure.png)", copied.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
