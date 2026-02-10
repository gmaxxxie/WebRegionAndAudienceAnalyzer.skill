import importlib.util
import unittest
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = ROOT / "web-region-audience-analyzer" / "scripts"


def load_module(module_name: str, path: Path):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DefaultMarkdownOutputPathTests(unittest.TestCase):
    def test_build_default_markdown_output_path_points_to_downloads(self):
        export_utils = load_module("export_utils", SCRIPTS_DIR / "export_utils.py")

        fake_home = "/tmp/test-home"
        url = "https://www.example.com/products"
        dt = datetime(2026, 2, 10, 20, 30, 40)

        output_path = export_utils.build_default_markdown_output_path(
            url=url,
            now=dt,
            home_dir=fake_home,
        )

        self.assertTrue(output_path.endswith(".md"))
        self.assertIn("/Downloads/", output_path)
        self.assertIn("example.com", output_path)
        self.assertIn("20260210-203040", output_path)


class MarkdownReportOptimizationTests(unittest.TestCase):
    def test_markdown_report_contains_executive_summary_and_next_actions(self):
        markdown_report = load_module(
            "generate_markdown_report",
            SCRIPTS_DIR / "generate_markdown_report.py",
        )

        sample = {
            "analyzedAt": "2026-02-10T10:00:00Z",
            "url": "https://www.example.com",
            "result": {
                "primaryRegionName": "United States",
                "primaryRegion": "US",
                "primaryLanguageName": "English",
                "primaryLanguage": "en",
                "likelyAudience": "Young professionals",
                "regionConfidence": 0.73,
            },
            "optimization": {
                "summary": {
                    "score": 58,
                    "grade": "C",
                    "totalIssues": 3,
                    "critical": 1,
                    "warnings": 2,
                    "info": 0,
                },
                "recommendations": [
                    {
                        "severity": "critical",
                        "category": "HTML",
                        "issue": "Missing hreflang",
                        "recommendation": "Add hreflang for key regions",
                    }
                ],
            },
        }

        report = markdown_report.generate_markdown_report(sample)

        self.assertIn("## 🧭 执行摘要", report)
        self.assertIn("## ✅ 建议优先处理", report)
        self.assertIn("关键问题 1 项", report)


if __name__ == "__main__":
    unittest.main()
