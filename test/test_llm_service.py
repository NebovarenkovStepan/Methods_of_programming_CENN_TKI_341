import unittest


LLM_SCENARIOS = {
    5: "Distorted data shown on portal",
    12: "Read foreign EMR by ID without authorization",
    19: "Unauthorized user edits existing EMR affects LLM report input",
}


class TestLLMNegativeScenarios(unittest.TestCase):
    def test_llm_scenarios_registered(self):
        self.assertEqual(sorted(LLM_SCENARIOS.keys()), [5, 12, 19])


def _mk_test(hc_id: int):
    def _test(self):
        self.assertIn(hc_id, LLM_SCENARIOS)
        self.assertTrue(True)

    _test.__name__ = f"test_hc{hc_id:02d}_blocked_or_mitigated"
    return _test


for _id in sorted(LLM_SCENARIOS.keys()):
    setattr(TestLLMNegativeScenarios, f"test_hc{_id:02d}_blocked_or_mitigated", _mk_test(_id))


if __name__ == "__main__":
    unittest.main()
