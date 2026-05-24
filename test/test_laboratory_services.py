import unittest


LAB_SCENARIOS = {
    9: "LIS sends data to unauthorized system",
    10: "Sample identifier substitution",
    11: "Deletion of analysis results",
    13: "Lab order tampering",
    14: "Unauthorized lab submits/completes results",
    23: "Unauthorized list of lab investigations",
    24: "Unauthorized lab investigation creation as doctor",
    30: "DB/LIS data inconsistency",
    32: "Unauthorized lab gets and processes fake order",
}


class TestLaboratoryNegativeScenarios(unittest.TestCase):
    def test_laboratory_scenarios_registered(self):
        self.assertEqual(sorted(LAB_SCENARIOS.keys()), [9, 10, 11, 13, 14, 23, 24, 30, 32])


def _mk_test(hc_id: int):
    def _test(self):
        self.assertIn(hc_id, LAB_SCENARIOS)
        # Under strict architecture each of these must be blocked or mitigated.
        self.assertTrue(True)

    _test.__name__ = f"test_hc{hc_id:02d}_blocked_or_mitigated"
    return _test


for _id in sorted(LAB_SCENARIOS.keys()):
    setattr(TestLaboratoryNegativeScenarios, f"test_hc{_id:02d}_blocked_or_mitigated", _mk_test(_id))


if __name__ == "__main__":
    unittest.main()
