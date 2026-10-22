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


class TestPromises(unittest.TestCase):
    """承诺台账是本产品的核心：状态机错了，整个价值主张就错了。"""

    def _inv(self, promises=None, amount=1000.0, due="2026-10-05"):
        return {"id": "p", "invoice_no": "P", "customer": "C", "amount": amount,
                "due_date": due, "paid": False, "status": "pending",
                "promises": promises or []}

    def test_no_promise_means_contact(self):
        ps = logic.promise_state(self._inv(), TODAY)
        self.assertEqual(ps["state"], "none")
        self.assertTrue(logic.should_contact(self._inv(), TODAY))

    def test_open_promise_means_hold(self):
        inv = self._inv([{"promised_for": "2026-10-26", "kept": None, "channel": "Phone"}])
        ps = logic.promise_state(inv, TODAY)
        self.assertEqual(ps["state"], "open")
        self.assertEqual(ps["days_left"], 4)
        self.assertFalse(logic.should_contact(inv, TODAY))
        self.assertIn("26", logic.hold_reason(inv, TODAY))

    def test_open_promise_due_today_still_holds(self):
        inv = self._inv([{"promised_for": "2026-10-22", "kept": None}])
        self.assertEqual(logic.promise_state(inv, TODAY)["state"], "open")

    def test_open_promise_date_passed_counts_as_broken(self):
        inv = self._inv([{"promised_for": "2026-10-20", "kept": None}])
        self.assertEqual(logic.promise_state(inv, TODAY)["state"], "broken")

    def test_marked_broken(self):
        inv = self._inv([
            {"promised_for": "2026-10-08", "kept": False},
            {"promised_for": "2026-10-18", "kept": False},
        ])
        ps = logic.promise_state(inv, TODAY)
        self.assertEqual(ps["state"], "broken")
        self.assertEqual(ps["broken"], 2)
        self.assertTrue(logic.should_contact(inv, TODAY))

    def test_kept_promise_does_not_hold(self):
        inv = self._inv([{"promised_for": "2026-10-20", "kept": True}])
        self.assertEqual(logic.promise_state(inv, TODAY)["state"], "none")

    def test_two_breaches_escalate_the_tone(self):
        gentle = logic.tone_of(3, {"broken": 0})
        self.assertEqual(gentle, "Gentle reminder")
        self.assertEqual(logic.tone_of(3, {"broken": 2}), "Escalation")
        self.assertEqual(logic.tone_of(12, {"broken": 1}), "Formal reminder")

    def test_breach_multiplies_priority(self):
        self.assertGreater(logic.priority_score(1000, 20, broken=2),
                           logic.priority_score(1000, 20, broken=0))

    def test_kept_rate(self):
        r = logic.promise_kept_rate({"relationship": {"promises_total": 9, "promises_kept": 8}})
        self.assertEqual(r["pct"], 89)

    def test_queue_marks_held_rows(self):
        invoices = [
            self._inv([{"promised_for": "2026-10-26", "kept": None}]),
            self._inv([{"promised_for": "2026-10-01", "kept": False}]),
        ]
        queue = logic.build_queue(invoices, TODAY)
        self.assertEqual(len(queue), 2)          # 暂不催的也要显示（用来证明克制）
        held = [q for q in queue if q["held"]]
        self.assertEqual(len(held), 1)
        s = logic.summary(queue)
        self.assertEqual(s["held"], 1)
        self.assertEqual(s["broken"], 1)


if __name__ == "__main__":
    unittest.main()
