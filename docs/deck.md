# Pitch deck — executive-summary format

Mentor's wording, 2026-10-23: *"I want you to research how to create a pitch deck using the
format of executive summary… because clarity of proposal carries 20% of your mark."*

**Editing scope:** research and documentation only. This revision changes the proposal
narrative and evidence wording; it does not change the application, live-demo section,
PPTX, submission PDFs, or another member's implementation. Research notes and the
claim-verification checklist are in `wang-zhilin-research.md`.

An executive summary is not "short slides". It is **a deck where slide 1 alone would still let
a judge score you** — situation, complication, resolution, proof, ask. Every slide after it
exists only to defend one line of slide 1.

> **Rule for the whole deck: one assertion per slide, in the slide title.**
> If the title is a noun ("Our solution"), you have written a label, not a proposal.

---

## Slide 1 — Executive summary (the only slide that must work alone)

**Title:** Make the payment promise part of the next follow-up decision.

**On-slide copy — keep these five lines short:**

- **User:** small suppliers managing overdue customer invoices.
- **Problem:** a due date alone does not explain whether to wait or follow up.
- **Solution:** record the promise, hold or draft by rule, then ask a person to review.
- **Prototype:** manual entry → promise-aware decision → model/template draft → logged review.
- **Next evidence:** compare preparation time and factual accuracy with existing practice.

**Visible status line:** Synthetic-data prototype · approval logs only · impact not yet measured.

**Presenter notes — evidence mapping, not additional slide text:**

| Line | Supporting explanation | Requirement addressed |
|---|---|---|
| Situation | A small supplier needs to follow up overdue invoices, but payment promises may remain in calls or messages rather than the collection record. This is our target-user hypothesis, not a measured market statistic. | One clear problem |
| Complication | A reminder based only on the due date can overlook an open payment promise or fail to distinguish a broken one. | Problem–solution fit |
| Resolution | CollectLoop records promises, holds invoices with open promises, and prepares drafts for eligible overdue invoices without an open promise. A person reviews every draft. | Automated chain + human control |
| Proof | The prototype contains a manual-entry form, promise-aware rules, model-or-template drafting, review actions and a local audit log. The demonstration uses synthetic data and sends no messages. | Feasibility |
| Business | Proposed as an Orbyte-compatible module. Reduced preparation time and earlier collections are hypotheses to test in a pilot, not proven results. | Orbyte fit + SDG |

**Speaker line (about 20s; rehearse):** "CollectLoop helps small suppliers follow up overdue
invoices using the customer's payment promise, not just the due date. Rules decide whether
to wait or draft; AI or a template prepares the wording; a person reviews it. This prototype
logs decisions without sending messages."

---

## Slide 2 — The gap is between the call and the letter

**Title:** The same overdue invoice can need three different responses.

**Illustrative scenario — not a customer case study:** an unpaid invoice is overdue.
The promise state changes the appropriate next step:

| Recorded context | Rule-based response | Why it matters |
|---|---|---|
| No payment promise recorded | Prepare a reminder for review | Ask for a clear next step |
| Promise date has not passed | Hold new drafting | Avoid following up before the promised date |
| Promise date has passed | Prepare a reminder using the missed commitment | Give the reviewer the relevant history |

**Research question:** do suppliers lose this context often enough that recording it
reduces unnecessary follow-up work?

**Research hypothesis:** poorly timed reminders may create avoidable follow-up work and
strain customer relationships. The three-column example is fictional, not a customer
interview or proof that competitors lack promise tracking.

**Speaker line (25s):** "Our focus is the gap between a payment promise and the next reminder.
We record the commitment so the follow-up decision can use it. We still need customer
interviews to establish how often this problem occurs."

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

**Title:** Rules choose whether to draft. AI helps write it. People check it.

**On-slide copy:**

| Rules | Model or template | Person |
|---|---|---|
| Select eligible invoices and tone | Prepare reminder wording from recorded context | Check facts, edit, approve or skip |

**Visible status line:** Model output is not guaranteed accurate. Approval does not send.

**Presenter notes:**

- **Input:** invoice and customer details, dates, calculated overdue status, rule-selected tone
  and recorded promise context. These are supplied to the model as drafting context.
- **Output and value:** a reminder paragraph tailored to that context. The intended benefit
  is less manual composition, not a new prediction of credit risk or payment behaviour.
- **Boundary:** rules select eligible invoices and tone; the model does not update the ledger
  or send messages. Prompt instructions ask it not to invent facts, but cannot guarantee
  accuracy. A reviewer must check amounts, names, dates and unsupported statements.
- **Fallback:** without a configured model, or when the call fails, the prototype uses a
  template. Present this as template output, not evidence of a successful AI call.

**Why not let the model decide?** Eligibility and tone need traceable, repeatable rules.
Tests of those rules do not prove the accuracy of generated wording. Human review remains
necessary, and approval in this prototype only records a decision.

**Speaker line (30s):** "The AI writes the reminder; it does not decide who to chase.
Rules choose eligibility and tone, and a person checks the result. If the model is
unavailable, we show a template instead. No message is sent by this prototype."

**If asked “Why not just use templates?”:** "Templates are a valid baseline, and we already
support them. AI may help when wording needs to reflect different promise histories, but
we have not demonstrated that advantage yet. We will compare review time, corrections
and factual errors. If AI adds no value, the rule-and-template workflow is still useful."

---

## Slide 5 — Orbyte fit: reuse, not rebuild

**Title:** A proposed Orbyte module, demonstrated with replay data.

The repository includes a sample export and a mapping adapter. The current demonstration
reads replay data and writes local records; it does not establish live Orbyte identity,
approvals, audit, notifications or document-storage integration. The live API path is not
implemented. Platform capabilities and API availability need confirmation from current
provider documentation before a pilot.

**Positioning:** "We propose adding promise-aware follow-up to an existing SME workflow,
rather than asking the customer to replace their accounting system."

**Speaker line (25s):** "Today we demonstrate the adapter using a sample export. Live
integration is future work, not something we claim to have connected."

---

## Slide 6 — The money, in days not features

**Title:** Measure preparation time first; validate cash-flow impact in a pilot.

**On-slide copy:**

- Intended benefit: less preparation work without sacrificing factual accuracy.
- First comparison: manual writing vs template review vs AI-draft review.
- Report time **and** errors; a faster but less accurate draft is not a successful result.

**Presenter notes — illustrative arithmetic only:** show the following table only if there
is time to explain its assumptions. Do not use RM7,000 as a headline product result.

| Element | Number | Source of the number |
|---|---|---|
| Manual reminder | 12 min | Illustrative assumption; no timing dataset is supplied |
| Reviewed draft | 1 min | Illustrative assumption; includes review, not automatic approval |
| Time example | 20 reminders × (12 − 1) min = **220 min**, about **3.7 hours** | Scenario arithmetic, not measured savings |
| Cash-flow example | RM30,000 monthly credit sales ÷ 30 days × 7 days = **RM7,000** | Assumes steady sales and a 7-day reduction in collection time; not observed impact |
| Pricing | Invoice-volume pricing is one option to test | Proposed business model, not existing sales or a provider-approved offer |

**Say it as an example, never as a finding:** "If a supplier has RM30,000 in monthly credit
sales and collects seven days earlier, a simplified 30-day-month calculation suggests
RM7,000 less tied up in receivables. We have not shown that CollectLoop produces that change."
This is a working-capital illustration, not additional revenue or profit. Do not mix this
scenario with RM300,000 annual sales, which would require a different calculation.

**SDG link:** reducing administrative burden and supporting cash-flow management could
support small-enterprise productivity (SDG 8). This is an intended contribution, not a
measured employment or development outcome.

**Research ask (about 15s; optional closing wording):** "Our next step is to test this with
small suppliers: does recording promises improve follow-up decisions, and does AI reduce
review effort compared with templates? We are seeking feedback and pilot participants,
not claiming proven collection gains."

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
| "How do you deploy this?" | The repository runs a Python web server. Ask the deployment owner to confirm the current published URL and hosting configuration; this imported project has no successful published build as checked on 24 October 2026. No cold-start benchmark is supplied. |
| "Front end and back end?" | Server-rendered HTML templates and CSS, served by a Python standard-library HTTP server. |
| "Do you have a database?" | The prototype stores state in JSON and audit entries in a local hash-linked log. This is not proof of production durability, access control or tamper-proof storage. |
| "Security?" | The code defines security headers. The mentor reported D+ and suggested B+; no current published-site result has been verified. Header presence alone does not establish application security. |

## Appendix B — accessibility (it is part of the judging, per the mentor)

The following are existing implementation features, not a WCAG conformance assessment.
Navigation, keyboard access, text contrast, zoom and responsive behaviour still require
verification by the frontend/testing owners.

- Skip link, `aria-current` on nav, `role="status"` on result banners, `scope="col"` + caption
  on the table, visible focus rings on every control.
- Base type 15.2px, table 14.2px, nav 14.6px (was 11–13px).
- No colour-only meaning: status is a word plus a colour.

## Appendix C — mentor feedback and evidence boundaries

| Mentor said | Documentation response / evidence boundary | Where to see it |
|---|---|---|
| "Follow WCAG, it's part of judging" | Describe existing features without claiming conformance; implementation remains with its owner | Appendix B |
| "Explain the AI feature" | Explain input, drafting output, rule boundaries, fallback and human review | Slide 4 |
| "At least let people upload an invoice" | Existing `/upload` is manual data entry, not file upload, OCR or a camera | Research notes |
| "Try to target B+" (Observatory) | Distinguish the target from a verified scan result | Appendix A |
| "Use executive summary format" | State problem, solution, evidence, value and limits concisely | Slide 1 |
