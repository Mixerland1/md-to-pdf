import unittest
import tempfile
from pathlib import Path
from md_to_pdf.batch import collect_sources, plan_outputs
from md_to_pdf.cli import TEMPLATES, render_html, main
from pypdf import PdfReader

class BatchTests(unittest.TestCase):
    def test_discovery(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            a = root / "a.md"; a.write_text("# A")
            sub = root / "sub"; sub.mkdir()
            b = sub / "b.MARKDOWN"; b.write_text("# B")
            self.assertEqual(collect_sources([root, a]), [a])
            self.assertEqual(set(collect_sources([root], recursive=True)), {a, b})
    def test_collision_and_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); sub = root / "sub"; sub.mkdir()
            a, b = root / "a.md", sub / "a.md"
            a.touch(); b.touch()
            with self.assertRaises(ValueError):
                plan_outputs([a,b], output_dir=root)
            a.with_suffix(".pdf").touch()
            with self.assertRaises(ValueError):
                plan_outputs([a])
            self.assertEqual(plan_outputs([a], overwrite=True)[0][1], a.with_suffix(".pdf"))
    def test_templates_and_batch_cli(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); a = root / "a.md"; b = root / "b.md"
            a.write_text("# Alpha"); b.write_text("# Beta")
            self.assertEqual(len({render_html(a, template=t) for t in TEMPLATES}), 3)
            self.assertEqual(main([str(root), "--template", "business"]), 0)
            for p in (a, b):
                self.assertTrue(PdfReader(p.with_suffix(".pdf")).pages)
