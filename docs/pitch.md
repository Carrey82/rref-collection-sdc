# CollectLoop — pitch & demo script

**Team:** RREF COLLECTION · **Domain 2** Orbyte Smart SME Challenge
**Status:** working prototype · Replit deployment · Apache-2.0

---

## 1. The one-liner (say this first, every time)

> A small supplier does not lose money because it cannot write a stern email.
> It loses money because **nobody remembers what the customer promised**.
> CollectLoop keeps that promise on record and only speaks up when the promise is gone.

If you only have 10 seconds:

> **We chase the promise, not the invoice.**

---

## 2. The 30-second version

> Mei runs a small hardware supply business. Twenty invoices are overdue and she spends
> roughly twelve minutes on each one: find the record, check whether it was paid, decide how
> hard to push, write the message, log it.
>
> But the expensive part is not the typing. It is that **three of her customers already told
> her a date**, and those dates live in a WhatsApp thread nobody reads again. So she either
> chases people who already promised — and damages a good relationship — or forgets to chase
> the one who broke a promise twice.
>
> CollectLoop is the layer that remembers. Every promise gets a ledger entry: who said it,
> when, on which channel, and whether it was kept. The system drafts a message **only when
> there is no promise left to wait for**, and the tone is chosen by the ledger — a customer
> who has kept 8 of 9 promises gets a gentle nudge; one who broke two dates gets the dates
> quoted back. A person still presses approve. Everything is logged.

---

## 3. Three-minute demo script

Rehearse this exactly. Total ≈ 2:40, leaving 20 s of slack.

| Time | On screen | Say this |
|---|---|---|
| 0:00–0:20 | Home page | "This is the queue of overdue money for a synthetic supplier. Five invoices, 51,350 ringgit. But look at the column in the middle — that is the product." |
| 0:20–0:40 | Point at **Promise** column | "Two customers promised a date and are inside it. Two broke a date they chose. Two never promised anything. Those are three completely different conversations." |
| 0:40–1:00 | Click **Why?** on Tan Hardware | "Twelve thousand ringgit, three days overdue — normally the first chase. But he promised the 26th and there are four days left. The system says: **nothing to send**. Chasing now buys nothing and costs goodwill." |
| 1:00–1:30 | Back, open **Sunrise Packaging** | "Twenty-eight thousand, thirty-seven days, and two dates he chose and missed. Read the draft — it quotes 18 October back at him and refuses another vague answer. That sentence is not the model being clever; it is the ledger." |
| 1:30–1:50 | Scroll the right panel | "This is the ledger: two entries, both broken, with the verbatim note, who logged it and when. A 0-of-2 promise record is why the tone escalated." |
| 1:50–2:10 | Record a promise on Greenleaf | "Now the human part. He calls and says payday is the 30th. I type three fields and save. The invoice is now on hold — the draft is discarded, because from here the right action is to wait." |
| 2:10–2:25 | Back to queue + audit | "One row moved to hold, the audit entry is written with my name. Every decision links to the previous one by hash, so nothing can be quietly rewritten." |
| 2:25–2:40 | Orbyte panel | "And this is not another standalone tool. Identity, approvals, audit trail and customer context come from Orbyte — we consume them rather than rebuild them. That is what makes it a module an SME can switch on." |

**Demo rules**
- Never open a terminal. Never show source code until someone asks.
- Click slowly. Judges need to read the chips.
- If the model is not configured, the banner says *template fallback* — **say it out loud**:
  "the wording layer is optional; the decision layer is deterministic". That turns a
  limitation into the strongest architectural point.

---

## 4. The six must-haves, mapped to evidence

| Must-have (official wording) | Where it lives | Evidence you can point at |
|---|---|---|
| **One clear SME problem** | Micro suppliers forgetting verbal payment promises | Hero line + the `Broken ×2` row |
| **Automated journey: trigger → data → logic → approval → logged outcome** | `POST /scan` → Orbyte export → `logic.py` → `/review` → `audit_log.jsonl` | Five steps are literally the five files; the audit page shows the chain |
| **Human control** | No send path exists in code; a promise can only be typed by a human | Review page: "Approve & log" is the only way forward; the form is the only way a hold is created |
| **Orbyte fit and reuse** | `src/orbyte.py` adapter + capability panel | Dashboard "How this plugs into Orbyte"; sample payload in Orbyte's field names |
| **Business benefit + SDG link** | 12 min → 1 min per invoice; promise-kept rate as a new KPI | "What the restraint is worth" panel; SDG 8.3 primary, 9.3 secondary |
| **Ease of learning** | One screen, one button, one three-field form | A shop owner needs no training: the only verbs are *run scan*, *approve*, *record promise* |

---

## 5. Questions they will ask

**"Isn't this just ChatGPT with a template?"**
> No. The decision — who to contact, when to stay silent, which tone — is deterministic and
> unit-tested (23 tests). The model only writes prose, and if you unplug it the product still
> works: the banner says *template fallback*. A chatbot cannot tell you "don't chase this one".

**"Are you actually integrated with Orbyte?"**
> We built the adapter against Orbyte's documented export shape and ship a replay payload, so
> the integration is real at the data-contract level. The live Open API is roadmap (Phase 4)
> and we have no sandbox credentials — so the code raises `NotImplementedError` rather than
> pretending. Switching to live is one environment variable, not a rewrite.

**"Where does the data come from?"**
> Synthetic, generated for this demo. No real personal data — that is a hard rule in the brief.

**"Why must a human click?"**
> Liability. An automated demand letter with a wrong date or a wrong customer is a legal
> problem, not an efficiency problem. The brief asks for human control; we made it physical —
> there is no send function anywhere in the codebase.

**"What happens when the customer breaks another promise?"**
> The breach counter multiplies priority (×1.6 per breach) and escalates the tone even if the
> invoice is young. Two breaches and a 10-day-old invoice is treated like an escalation.

**"How does this scale to many SMEs / how is it reusable?"**
> Rules live in data, not in code: aging buckets, tone ladder and breach multiplier are
> configuration. Another SME needs a different export mapping and their own thresholds, not a
> fork. Charging follows Orbyte's usage model — per decision, not per seat.

**"What's the biggest risk, and what's your fallback?"**
> Risk: promise data is only as good as the person who types it — if the shop owner doesn't
> record the promise, the product is blind. Fallback: the queue still works as a plain ageing
> list (that is the whole of v0), so the product degrades to "useful" rather than "broken".

---

## 6. What we do **not** claim

Say these out loud if asked. Volunteering the limits makes everything else credible.

- No email is actually sent — approving records a decision and the final text.
- No live Orbyte API — replay mode against a payload in their shape.
- No database — JSON + append-only log; swapping in an API is about 60 lines.
- No real customer data — synthetic only.
- The promise-kept rate is a demo metric, not yet validated against a real ledger.
