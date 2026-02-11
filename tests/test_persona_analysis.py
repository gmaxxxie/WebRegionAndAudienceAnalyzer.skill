import importlib.util
import unittest
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


class PersonaAnalysisLogicTests(unittest.TestCase):
    def setUp(self):
        self.analyzer = load_module(
            "analyze_webpage",
            SCRIPTS_DIR / "analyze_webpage.py",
        )

    def test_resolve_target_audience_prefers_user_input(self):
        resolved = self.analyzer.resolve_target_audience(
            user_input="北美年轻女性消费者",
            result={"likelyAudience": "English-speaking audience in United States"},
            ai_analysis={
                "targetAudience": {
                    "inferredAudience": "price-sensitive audience",
                    "finalAudience": "price-sensitive audience",
                }
            },
        )
        self.assertEqual(resolved["source"], "user_input")
        self.assertEqual(resolved["finalAudience"], "北美年轻女性消费者")

    def test_build_fallback_persona_analysis_without_user_input(self):
        result = {
            "primaryRegion": "US",
            "primaryRegionName": "United States",
            "primaryLanguage": "en",
            "primaryLanguageName": "English",
            "likelyAudience": "English-speaking audience in United States",
            "regionConfidence": 0.62,
        }
        evidence = {
            "htmlSignals": {"lang": "en", "hreflangTags": []},
            "contentSignals": {"currencySymbols": ["$"], "currencyCodes": ["USD"]},
        }
        persona = self.analyzer.build_fallback_persona_analysis(
            result=result,
            evidence=evidence,
            target_audience=None,
        )

        self.assertEqual(persona["audience"]["source"], "rule_based")
        self.assertIn("United States", persona["regionalPersona"]["regionName"])
        self.assertGreaterEqual(persona["personaFit"]["score"], 0)
        self.assertLessEqual(persona["personaFit"]["score"], 10)


if __name__ == "__main__":
    unittest.main()
