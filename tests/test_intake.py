"""
intake.py 的单测 —— 手动上传发票的校验。

跑法：cd rref-collection-sdc && python3 -m unittest discover -s tests -q
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

import intake  # noqa: E402


GOOD = {
    "invoice_no": "INV-2026-0501",
    "customer": "Syarikat Jaya Sdn Bhd",
    "contact_name": "Ms. Lim",
    "contact_email": "accounts@jaya.example",
    "amount": "12,500.00",
    "due_date": "2026-09-30",
    "currency": "myr",
}


class TestClean(unittest.TestCase):
    def test_accepts_minimal_valid_invoice(self):
        inv, errors = intake.clean({"invoice_no": "INV-1", "customer": "A", "amount": "10",
                                    "due_date": "2026-09-01"})
        self.assertEqual(errors, [])
        self.assertEqual(inv["amount"], 10.0)
        self.assertEqual(inv["currency"], "MYR")
        self.assertEqual(inv["status"], "pending")
        self.assertEqual(inv["promises"], [])
        self.assertTrue(inv["uploaded"])

    def test_commas_in_amount_are_tolerated(self):
        inv, errors = intake.clean(dict(GOOD))
        self.assertEqual(errors, [])
        self.assertEqual(inv["amount"], 12500.0)

    def test_currency_is_upper_cased(self):
        inv, _ = intake.clean(dict(GOOD))
        self.assertEqual(inv["currency"], "MYR")

    def test_invoice_number_is_upper_cased(self):
        inv, _ = intake.clean(dict(GOOD, invoice_no="inv-2026-0501"))
        self.assertEqual(inv["invoice_no"], "INV-2026-0501")

    def test_rejects_missing_fields(self):
        _, errors = intake.clean({})
        joined = " ".join(errors)
        self.assertIn("Invoice number", joined)
        self.assertIn("Customer", joined)
        self.assertIn("Amount", joined)
        self.assertIn("Due date", joined)

    def test_rejects_duplicate_invoice_number(self):
        _, errors = intake.clean(dict(GOOD), existing_nos=["INV-2026-0501"])
        self.assertTrue(any("already in the ledger" in e for e in errors))

    def test_rejects_non_numeric_amount(self):
        _, errors = intake.clean(dict(GOOD, amount="twelve thousand"))
        self.assertTrue(any("must be a number" in e for e in errors))

    def test_rejects_zero_and_negative_amount(self):
        for bad in ("0", "-50"):
            _, errors = intake.clean(dict(GOOD, amount=bad))
            self.assertTrue(errors, bad)

    def test_rejects_absurd_amount(self):
        _, errors = intake.clean(dict(GOOD, amount="999999999999"))
        self.assertTrue(any("too large" in e for e in errors))

    def test_rejects_bad_date(self):
        _, errors = intake.clean(dict(GOOD, due_date="30/09/2026"))
        self.assertTrue(any("Due date" in e for e in errors))

    def test_rejects_bad_email_but_allows_empty(self):
        _, errors = intake.clean(dict(GOOD, contact_email="not-an-email"))
        self.assertTrue(any("email" in e for e in errors))
        _, errors = intake.clean(dict(GOOD, contact_email=""))
        self.assertEqual(errors, [])

    def test_rejects_invoice_number_with_spaces(self):
        _, errors = intake.clean(dict(GOOD, invoice_no="INV 2026 01"))
        self.assertTrue(errors)

    def test_future_due_date_is_allowed(self):
        inv, errors = intake.clean(dict(GOOD, due_date="2027-01-15"))
        self.assertEqual(errors, [])
        self.assertEqual(inv["due_date"], "2027-01-15")


class TestNextId(unittest.TestCase):
    def test_derives_readable_id_from_last_four_digits(self):
        self.assertEqual(intake.next_id("INV-2026-0501"), "inv-0501")

    def test_avoids_collision(self):
        self.assertEqual(intake.next_id("INV-2026-0501", ["inv-0501"]), "inv-0501-2")

    def test_survives_empty_number(self):
        self.assertTrue(intake.next_id("").startswith("inv-"))


if __name__ == "__main__":
    unittest.main()
