# Pitch deck — executive-summary format

Mentor's wording, 2026-10-23: *"I want you to research how to create a pitch deck using the
format of executive summary… because clarity of proposal carries 20% of your mark."*

An executive summary is not "short slides". It is **a deck where slide 1 alone would still let
a judge score you** — situation, complication, resolution, proof, ask. Every slide after it
exists only to defend one line of slide 1.

> **Rule for the whole deck: one assertion per slide, in the slide title.**
> If the title is a noun ("Our solution"), you have written a label, not a proposal.

---

## Slide 1 — Executive summary (the only slide that must work alone)

**Title:** A small supplier loses money because nobody remembers what the customer promised.

Five lines, in this order. Every one maps to a Domain 2 must-have:

| Line | Text on the slide | Must-have it proves |
|---|---|---|
| Situation | Malaysian SMEs chase overdue invoices by memory — about 12 minutes per reminder, and the record dies with the owner's phone. | One clear problem |
| Complication | It is already automated at the invoice level. It fails at the **promise** level: "payday is the 30th" is said on a phone call and never written down, so the next reminder apologises instead of quoting them. | Problem–solution fit |
| Resolution | CollectLoop keeps a promise ledger. It drafts a message **only when the promise is gone**, and stays silent while it still holds. | Automated chain + human control |
| Proof | One click → five stages → one draft per broken promise, zero per open one. Four screenshots on the next slide. | Feasibility |
| Business | Sold as a module inside Orbyte, priced by invoice volume. Seven fewer days in the collection cycle is cash already earned. SDG 8. | Orbyte fit + SDG |

**Speaker line (20s):** "We chase the promise, not the invoice. Everything after this slide is
evidence for that sentence."

---

## Slide 2 — The gap is between the call and the letter

**Title:** The promise already exists. It just never reaches the system that needs it.

Three-column layout, left to right:

1. **Customer says** — "Cheque's being prepared, will bank in by Monday." (WhatsApp, Tuesday)
2. **Nobody writes it down** — the owner remembers for four days, then forgets which Monday.
3. **The system sends** — a generic "invoice 0361 is 38 days overdue" — and the customer reads
   it as *you weren't listening*.

**The cost is not the letter.** It is that a badly timed chase spends goodwill you cannot buy
back, and quiet customers pay last.

**Speaker line (25s):** "Every tool in this market automates the letter. The letter was never
the problem."

---

## Slide 3 — One pass through the loop (the demo slide)

**Title:** One click; five stages; and the only output is a draft a person must approve.

Use the `/ai` page as this slide's artwork — it renders the chain with one badge per stage:

| # | Stage | Owner |
|---|---|---|
| 1 | A person presses *Run today's scan* | human |
| 2 | Read the invoice book + promise ledger | code |
| 3 | Decide who to chase and in what tone | **rule** |
| 4 | Write the sentence | **AI** |
| 5 | Approve / skip / record a promise | human |

Then the two numbers that prove the rule layer matters:

- 4 promises broken → 4 drafts, each quoting the date the customer gave.
- 1 promise still open → **0 drafts.** "Not sending is a feature."

**Speaker line (40s):** "Watch the counter on the right. It goes up when we choose silence."

---

## Slide 4 — Where the AI is (answer the question the mentor asked)

**Title:** The model writes one paragraph. The rules decide money.

Three statements, then one screenshot of the `/ai` page:

- **Input:** ten fields, all read from the ledger or computed by `logic.py`. No free text from
  the internet, so there is nothing to hallucinate from.
- **Constraint:** the system prompt forbids inventing a payment detail, a discount, or a threat;
  it must name a broken promise date if one is on record.
- **Boundary:** it cannot choose the customer, cannot change a date, cannot send. Verified by
  the fact that the product still runs with **no model key at all** — it falls back to a
  template and the demo continues.

**Why not let the model decide?** Determinism (23→39 unit tests on the rule layer), one-sentence
explainability to a customer, and liability: if the tone is wrong, the supplier answers for it.

**Speaker line (30s):** "We didn't use a lot of AI. We used it in the one place where being
wrong is cheap."

---

## Slide 5 — Orbyte fit: reuse, not rebuild

**Title:** Seven things Orbyte already has. We wrote none of them.

Table straight from the `/` page (`How this plugs into Orbyte`): identity, approvals, audit
trail, notifications, document storage, AI business context, customer records — five consumed
today, two marked `planned` in the UI, which is also what the Tech Declaration says.

One sentence that wins this slide: **"This is a module an SME switches on, not a system it
migrates to."**

**Speaker line (25s):** "Our whole integration surface is an export format they already emit."

---

## Slide 6 — The money, in days not features

**Title:** We don't sell software. We sell days of cash.

| Element | Number | Source of the number |
|---|---|---|
| Manual reminder | ~12 min | time-boxed ourselves doing it |
| Reviewed draft | ~1 min | measured on the review page |
| Worked example | 7 days × RM30k/month ≈ **RM70k** | stated as an example, **not** as research |
| Pricing | per invoice volume, inside Orbyte | no own billing, no own acquisition |

**Say it as an example, never as a finding:** "Take a five-person supplier doing RM300k a year…"
If asked, answer: *"It's a worked example; the real number comes from the customer's own ledger."*
Claiming research we did not do is the fastest way to lose the room.

**SDG 8** in one line: small suppliers don't die of weak demand, they die of cash arriving late.

---

## Slide 7 — What happens in the next 90 days

**Title:** Three things between this prototype and a paid pilot.

1. **Intake** — photo/QR capture feeding the same six fields the manual form writes today.
2. **Sending** — one email API call behind the existing approval button (deliberately unwired
   now so nothing can be sent by accident).
3. **Promise capture from messaging** — read the WhatsApp thread the promise was spoken in.

Then the ask, in the mentor's language, not ours: *"Tell us which of the three you would cut."*

---

## Appendix A — the four questions the mentor actually asked

| Question | Answer, in one breath |
|---|---|
| "How do you deploy this?" | One container on Replit, autoscale, HTTPS. No build step, no `pip install` — standard-library Python, so a cold start is ~0.2s warm / ~6s from sleep. |
| "Front end and back end?" | Server-rendered HTML + one stylesheet; `http.server` with five routes. Front end is a table and one form. |
| "Do you have a database?" | No — JSON on disk, atomic writes, append-only audit log chained by SHA-256. For one SME that is the right size; it also means the demo cannot fail on a DB connection. |
| "Security?" | Mozilla Observatory was D+; we now send CSP (no script sources at all), `nosniff`, `frame-ancestors 'none'`, COOP/CORP, Referrer-Policy, Permissions-Policy and HSTS on every response — including 404s. Target B+. |

## Appendix B — accessibility (it is part of the judging, per the mentor)

- Skip link, `aria-current` on nav, `role="status"` on result banners, `scope="col"` + caption
  on the table, visible focus rings on every control.
- Base type 15.2px, table 14.2px, nav 14.6px (was 11–13px).
- No colour-only meaning: status is a word plus a colour.

## Appendix C — what changed because of the 17:40 review

| Mentor said | We did | Where to see it |
|---|---|---|
| "Follow WCAG, it's part of judging" | Nav, focus rings, skip link, type scale | every page |
| "Explain the AI feature" | New page with the real prompt and the three limits | `/ai` |
| "At least let people upload an invoice" | Form + validation + audit entry | `/upload` |
| "Try to target B+" (Observatory) | Full security-header set | `curl -I` any page |
| "Use executive summary format" | This document | this deck |
