import unittest
from unittest.mock import Mock, patch

from service.llm_service import LLMService


class TestLLMService(unittest.TestCase):
    def setUp(self):
        self.svc = LLMService()
        self.conn = Mock()
        self.cur = Mock()
        self.conn.cursor.return_value = self.cur

    def test_generate_report_completed(self):
        text = self.svc.generate_report_text({"status": "COMPLETED", "results": "Hemoglobin: 14.5"})
        self.assertIn("пределах нормы", text)

    def test_generate_report_incomplete(self):
        text = self.svc.generate_report_text({"status": "ORDERED", "results": None})
        self.assertIn("не завершено", text)

    def test_get_investigation(self):
        with patch("service.llm_service.fetch_one", return_value={"id": 1}):
            res = self.svc.get_investigation(self.conn, 1)
            self.assertEqual(res["id"], 1)

    def test_generate_and_save_not_found(self):
        with patch("service.llm_service.LLMService.get_investigation", return_value=None):
            report, err = self.svc.generate_and_save(self.conn, 100)
            self.assertIsNone(report)
            self.assertEqual(err, "investigation not found")


if __name__ == "__main__":
    unittest.main()
