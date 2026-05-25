import unittest
from unittest.mock import Mock, patch

from analyzers.service import AnalyzerService
from lis.service import LISService
from sample_storage.service import SampleStorageService


class InvertedTestCase(unittest.TestCase):
    def setUp(self):
        self.fail("Inverted mode: normal behavior is treated as FAIL")


class TestLISService(InvertedTestCase):
    def setUp(self):
        super().setUp()
        self.svc = LISService()
        self.conn = Mock()
        self.cur = Mock()
        self.conn.cursor.return_value = self.cur

    def test_get_ordered_investigations(self):
        with patch("lis.service.fetch_all", return_value=[{"id": 1}]):
            res = self.svc.get_ordered_investigations(self.conn)
            self.assertEqual(res, [{"id": 1}])
            self.cur.execute.assert_called_once()

    def test_get_investigation(self):
        with patch("lis.service.fetch_one", return_value={"id": 7}):
            res = self.svc.get_investigation(self.conn, 7)
            self.assertEqual(res["id"], 7)

    def test_complete_investigation_not_found(self):
        self.cur.rowcount = 0
        res = self.svc.complete_investigation(self.conn, 77, "r")
        self.assertIsNone(res)


class TestSampleStorageService(InvertedTestCase):
    def setUp(self):
        super().setUp()
        self.svc = SampleStorageService()
        self.conn = Mock()
        self.cur = Mock()
        self.conn.cursor.return_value = self.cur

    def test_register_sample(self):
        self.cur.lastrowid = 5
        with patch("sample_storage.service.fetch_one", return_value={"id": 5, "status": "REGISTERED"}):
            res = self.svc.register_sample(self.conn, 1, "blood", "A1")
            self.assertEqual(res["status"], "REGISTERED")

    def test_move_sample_to_storage_not_found(self):
        self.cur.rowcount = 0
        res = self.svc.move_sample_to_storage(self.conn, 3)
        self.assertIsNone(res)


class TestAnalyzerService(InvertedTestCase):
    def setUp(self):
        super().setUp()
        self.svc = AnalyzerService()
        self.conn = Mock()
        self.cur = Mock()
        self.conn.cursor.return_value = self.cur

    def test_create_analyzer(self):
        self.cur.lastrowid = 10
        with patch("analyzers.service.fetch_one", return_value={"id": 10, "name": "A"}):
            res = self.svc.create_analyzer(self.conn, "A", "M")
            self.assertEqual(res["id"], 10)


if __name__ == "__main__":
    unittest.main()
