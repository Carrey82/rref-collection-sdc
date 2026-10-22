"""
CollectLoop · 逻辑层单测（零依赖，只用 unittest）
运行：python3 -m unittest discover -s tests -v
"""
import os
import sys
import unittest
from datetime import date

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import logic  # noqa: E402

TODAY = date(2026, 10, 22)


class TestDaysOverdue(unittest.TestCase):
    def test_positive(self):
        self.assertEqual(logic.days_overdue("2026-10-19", TODAY), 3)

    def test_not_due_yet_is_negative(self):
        self.assertEqual(logic.days_overdue("2026-10-28", TODAY), -6)

    def test_due_today_is_zero(self):
        self.assertEqual(logic.days_overdue("2026-10-22", TODAY), 0)


class TestBuckets(unittest.TestCase):
    def test_boundaries(self):
        cases = [
            (0, "Not due"),
            (1, "Gentle reminder"),
            (7, "Gentle reminder"),
            (8, "Formal reminder"),
            (30, "Formal reminder"),
            (31, "Escalation"),
            (60, "Escalation"),
            (61, "Pre-legal"),
            (400, "Pre-legal"),
        ]
        for days, expect in cases:
            with self.subTest(days=days):
                self.assertEqual(logic.bucket_of(days)[0], expect)

    def test_every_bucket_has_action(self):
        for days in (1, 10, 40, 100):
            self.assertTrue(logic.bucket_of(days)[1])


class TestPriority(unittest.TestCase):
    def test_zero_when_not_overdue(self):
        self.assertEqual(logic.priority_score(5000, 0), 0.0)

    def test_bigger_amount_ranks_higher(self):
        self.assertGreater(logic.priority_score(10000, 20), logic.priority_score(1000, 20))

    def test_older_ranks_higher(self):
        self.assertGreater(logic.priority_score(1000, 60), logic.priority_score(1000, 5))


class TestQueue(unittest.TestCase):
    def setUp(self):
        self.invoices = [
            {"id": "a", "invoice_no": "A", "customer": "X", "amount": 1000.0,
             "due_date": "2026-10-19", "paid": False, "status": "pending"},
            {"id": "b", "invoice_no": "B", "customer": "Y", "amount": 5000.0,
             "due_date": "2026-08-01", "paid": False, "status": "pending"},
            {"id": "c", "invoice_no": "C", "customer": "Z", "amount": 9999.0,
             "due_date": "2027-01-01", "paid": False, "status": "pending"},
            {"id": "d", "invoice_no": "D", "customer": "W", "amount": 9999.0,
             "due_date": "2026-08-01", "paid": True, "status": "pending"},
        ]

    def test_filters_not_due_and_paid(self):
        queue = logic.build_queue(self.invoices)
        ids = [q["id"] for q in queue]
        self.assertIn("a", ids)
        self.assertIn("b", ids)
        self.assertNotIn("c", ids)   # 未到期不该被催
        self.assertNotIn("d", ids)   # 已付款不该被催

    def test_sorted_by_priority(self):
        queue = logic.build_queue(self.invoices)
        prios = [q["priority"] for q in queue]
        self.assertEqual(prios, sorted(prios, reverse=True))

    def test_summary_counts_only_open(self):
        queue = logic.build_queue(self.invoices)
        s = logic.summary(queue)
        self.assertEqual(s["overdue_count"], 2)
        self.assertAlmostEqual(s["overdue_amount"], 6000.0)


class TestSavings(unittest.TestCase):
    def test_zero_approved(self):
        self.assertEqual(logic.savings_estimate(0)["minutes_saved"], 0)

    def test_ten_approved(self):
        # (12 - 1) * 10 = 110 分钟
        self.assertEqual(logic.savings_estimate(10)["minutes_saved"], 110)


if __name__ == "__main__":
    unittest.main()
