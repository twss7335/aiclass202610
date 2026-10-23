"""The static site must publish existing artifacts without changing their values."""

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"


class StaticSiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        subprocess.run([sys.executable, "scripts/build_static_site.py"], cwd=ROOT, check=True)

    def test_metrics_are_exact_copies_with_sources(self):
        published = json.loads((DOCS / "results.json").read_text(encoding="utf-8"))
        for project, path in {
            "iris": "results/metrics.json",
            "ai4i": "results/ai4i/metrics.json",
        }.items():
            self.assertEqual(published[project]["source"], path)
            self.assertEqual(published[project]["metrics"],
                             json.loads((ROOT / path).read_text(encoding="utf-8")))

    def test_every_existing_figure_is_copied_byte_for_byte(self):
        sources = sorted((ROOT / "results").rglob("*.png"))
        self.assertTrue(sources)
        for source in sources:
            target = DOCS / "figures" / source.relative_to(ROOT / "results")
            self.assertEqual(target.read_bytes(), source.read_bytes(), str(source))

    def test_reports_render_and_local_images_exist(self):
        for name in ("iris_study", "ai4i_study"):
            source = ROOT / "paper" / f"{name}.md"
            html_path = DOCS / "reports" / f"{name}.html"
            html = html_path.read_text(encoding="utf-8")
            self.assertIn("<article", html)
            self.assertIn(source.read_text(encoding="utf-8").splitlines()[0][2:], html)
            for target in re.findall(r'<img[^>]+src="([^"]+)"', html):
                self.assertTrue((html_path.parent / target).is_file(), target)

    def test_homepage_loads_results_json_without_build_framework(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        js = (DOCS / "site.js").read_text(encoding="utf-8")
        self.assertIn('src="site.js"', html)
        self.assertIn('fetch("results.json")', js)
        self.assertIn('id="iris-metrics"', html)
        self.assertIn('id="ai4i-metrics"', html)
        for target in re.findall(r'href="([^"]+)"', html):
            if not target.startswith(("https://", "http://", "#")):
                self.assertTrue((DOCS / target).is_file(), target)

    def test_generated_model_data_is_separate_from_handwritten_inference(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        app = (DOCS / "app.js").read_text(encoding="utf-8")
        model_asset = DOCS / "model-data.js"
        exporter = (ROOT / "scripts" / "export_frontend_models.py").read_text(encoding="utf-8")
        self.assertTrue(model_asset.is_file(), "Generated model asset must exist")
        self.assertLess(html.index('src="model-data.js"'), html.index('src="app.js"'))
        self.assertLess(len(app), 20_000, "Handwritten app.js must not contain embedded models")
        self.assertNotIn("MODEL_DATA_START", app)
        self.assertNotIn("re.subn", exporter)
        self.assertIn('"model-data.js"', exporter)

    def test_result_cards_have_local_decorative_images_with_blur(self):
        html = (DOCS / "index.html").read_text(encoding="utf-8")
        for name in ("iris", "ai4i"):
            self.assertIn(f'class="summary-art summary-art--{name}" aria-hidden="true"', html)
            self.assertIn(f'assets/{name}-card-v1.png', html)
            self.assertTrue((DOCS / "assets" / f"{name}-card-v1.png").is_file())
        self.assertIn("filter: blur(14px)", html)
        self.assertIn("mask-image: linear-gradient", html)


if __name__ == "__main__":
    unittest.main()
