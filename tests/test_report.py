import csv
import io
import json
import unittest

from jiramigrate import report

ROWS = [{"name": "Alice", "n": 3, "ok": True, "tags": ["a", "b"]}, {"name": "Bob\nSmith", "n": None, "ok": False}]
COLS = ("name", "n", "ok", "tags")


class ReportTests(unittest.TestCase):
    def test_table(self):
        lines = report.render(ROWS, COLS).splitlines()
        self.assertEqual(lines[0], "name       n  ok   tags")
        self.assertEqual(lines[2], "Alice      3  yes  a, b")
        self.assertEqual(lines[3], "Bob Smith     no")

    def test_csv_keeps_line_breaks(self):
        parsed = list(csv.reader(io.StringIO(report.render(ROWS, COLS, "csv"))))
        self.assertEqual(parsed[2][0], "Bob\nSmith")

    def test_json(self):
        self.assertEqual(json.loads(report.render(ROWS, COLS, "json")), ROWS)

    def test_markdown(self):
        rows = [{"name": "a|b", "n": 1, "ok": True, "tags": ["x"]}, {"name": "multi\nline", "n": None, "ok": False}]
        lines = report.render(rows, COLS, "markdown").splitlines()
        self.assertEqual(lines[0], "| name | n | ok | tags |")
        self.assertEqual(lines[1], "| --- | --- | --- | --- |")
        self.assertEqual(lines[2], "| a\\|b | 1 | yes | x |")
        self.assertEqual(lines[3], "| multi line |  | no |  |")

    def test_empty_and_unknown(self):
        self.assertEqual(report.render([], COLS), "(no rows)\n")
        with self.assertRaises(ValueError):
            report.render(ROWS, COLS, "xml")


if __name__ == "__main__":
    unittest.main()
