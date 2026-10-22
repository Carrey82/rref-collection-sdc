# CollectLoop

> An SME-safe collections loop: the system drafts every overdue-payment reminder,
> a human approves each one, and nothing leaves the building unlogged.

---

## Team Information

| Field | Details |
| --- | --- |
| **Team Name** | RREF COLLECTION |
| **Team Domain** | Domain 2 — Orbyte Smart SME Challenge |
| **SDG Track** | **SDG 8** — Decent Work and Economic Growth *(primary)* · **SDG 9** — Industry, Innovation and Infrastructure *(secondary)* |
| **Team Leader** | `TODO: 填姓名` |
| **University** | Xiamen University Malaysia |
| **Number of Members** | `TODO: 填人数` |

## Links

| Resource | Link |
| --- | --- |
| GitHub Repository | https://github.com/`TODO-username`/rref-collection-sdc |
| Replit Project | https://replit.com/@`TODO-username`/rref-collection-sdc |
| Live Demo | https://`TODO`.replit.app |
| RunPod Endpoint | Not used — no GPU workload in this prototype |
| Slide Deck | `TODO` |
| Demo Video | `TODO` |

---

## Overview

### Problem

A small wholesaler in Klang issues 60–80 invoices a month. Roughly one in six is paid late,
and chasing them is the owner's job — squeezed between deliveries and stock checks, in
whatever five minutes are free.

Each reminder takes about 12 minutes: find the invoice, check whether it was already paid,
work out how firmly to write it this time, write it, verify the numbers, and file it somewhere.
Because it is done in fragments, three things break:

1. **Tone drifts.** A customer who is 3 days late gets the same blunt message as one who is
   60 days late, and goodwill is spent for nothing.
2. **Nothing is recorded.** When the owner is away, nobody knows which customers were
   contacted, how firmly, or what was promised.
3. **It is the first task dropped.** Late reminders mean later cash, which is exactly the
   problem an SME cannot absorb.

### Solution

CollectLoop runs the deterministic part automatically and stops before the part that
needs judgement.

It sweeps the invoice book, sorts by real urgency (amount × √days overdue), places each
customer in an ageing bucket, and drafts a reminder in the tone that bucket calls for.
Then it **stops**. A person opens each draft, edits it if the tone is wrong, and either
approves or skips the customer. Every decision is written to an append-only log with a
hash chain, so the record cannot be quietly edited later.

### Key Features

- **Rule-based urgency, not vibes** — ageing buckets and priority scoring live in one
  testable file (`src/logic.py`), so a judge can ask "why this tone?" and get a file path.
- **Drafts, never sends** — the model writes the email body; a human clicks approve.
  Sending is deliberately left unwired in this prototype.
- **Graceful degradation** — if the model is unreachable or unconfigured, the system falls
  back to a hand-written template. The demo never white-screens.
- **Append-only audit trail** — who approved what, when, with the final text, plus the
  previous entry's hash.
- **Skipping is a first-class action** — "don't chase this customer" is recorded with the
  same weight as "chase them".

### Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | Server-rendered HTML + CSS (no build step, no framework) |
| Backend | Python 3.11 · standard library `http.server` |
| Database | JSON files on disk (`data/invoices.json`, `data/state.json`, `data/audit_log.jsonl`) |
| AI | Any OpenAI-compatible chat endpoint, with deterministic template fallback |
| GPU / Compute | **None** — no training, no fine-tuning, no GPU inference |
| Hosting / Dev | Replit (Deployment) |

> **Zero third-party dependencies on purpose.** The most common way a hackathon demo dies is
> a failed `pip install`. This runs on a bare Python 3.11.

---

## Mapping to the six Domain 2 must-haves

| # | Requirement | Where it lives | How to show it in 15 seconds |
| --- | --- | --- | --- |
| 1 | **One clear pain point** | This README, *Problem* | "The owner chases overdue invoices 12 minutes at a time, from memory." |
| 2 | **Complete chain: trigger → fetch → logic → approval → record** | `POST /scan` → `store.load_state` → `logic` + `llm` → `/review` → `store.append_audit` | Click *Run today's scan*, open one draft, approve it, open *Audit log*. Four clicks, whole chain. |
| 3 | **Human in the loop** | `templates/review.html`, `decide()` in `src/app.py` | The draft is in an editable box. Nothing is sent until *Approve & log* is pressed. |
| 4 | **Fits Orbyte and is reusable** | Single container, `.env`-configured, no vendor lock-in | "Any SME with an invoice list can point this at their own book — the rules are one file." |
| 5 | **Business benefit + SDG link** | *SDG alignment* below; savings panel on the dashboard | Dashboard prints hours saved from approvals you just made. |
| 6 | **Low learning cost** | One screen, one button, one review page | A first-time user needs no documentation: the queue says what is overdue, the review page says what to do. |

---

## Project Structure

```
.
├── src/
│   ├── app.py          # HTTP entry: routing, pages, 5-stage chain wiring
│   ├── logic.py        # ageing buckets, priority score, summary (pure, unit-tested)
│   ├── llm.py          # draft generation + deterministic fallback
│   └── store.py        # JSON state + append-only audit log with hash chain
├── templates/          # server-rendered pages (index, review, audit, error, reset)
├── static/style.css    # single stylesheet, no build step
├── data/
│   ├── invoices.json   # synthetic seed data (committed)
│   ├── state.json      # runtime state (gitignored)
│   └── audit_log.jsonl # audit trail (gitignored)
├── tests/test_logic.py # unittest, zero dependencies
├── runpod/handler.py   # placeholder — not used, see module docstring
├── submission/         # submission PDFs and proof-of-use screenshots
├── .replit             # Replit run + deployment config
├── .env.example        # environment variables (no secrets)
├── LICENSE             # Apache License 2.0
└── README.md
```

## Architecture

```
                 ┌──────────────────────── Replit (this app) ────────────────────────┐
                 │                                                                    │
  owner clicks   │   ① trigger        ② fetch          ③ logic         ④ approval   │
  "Run scan"  ───┼──► POST /scan ──► invoices.json ──► buckets + ──► review page ──┤
                 │                                        priority      (editable)  │
                 │                                           │              │       │
                 │                                           ▼              ▼       │
                 │                                   ┌──────────────┐  approve /    │
                 │                                   │ LLM API      │  skip         │
                 │                                   │ (draft only) │              │
                 │                                   └──────┬───────┘              │
                 │                          fallback: template│                     │
                 │                                           ▼                     │
                 │                        ⑤ append-only audit_log.jsonl (hash chain)│
                 └────────────────────────────────────────────────────────────────────┘
```

The model sits at exactly one point — drafting prose. It cannot fetch data, cannot choose
the tone bucket, and cannot send. Everything a judge might call "the decision" is either
a rule in `logic.py` or a click by a human.

---

## How to Run

### Option 1 — Replit (recommended, this is also our compliance path)

1. Open the Replit project, or **Create Repl → Import from GitHub**.
2. Open the **Secrets** panel (🔒) and add the three variables from `.env.example`.
   *Skip this and the app still runs, using template copy.*
3. Press **Run**. Replit reads `.replit` and starts `python3 src/app.py`.
4. **Deploy** → you get a public `*.replit.app` URL.

### Option 2 — Local

```bash
git clone https://github.com/TODO-username/rref-collection-sdc.git
cd rref-collection-sdc
cp .env.example .env          # optional; fill LLM_API_KEY if you want model drafts
python3 src/app.py            # → http://localhost:8080
```

No `pip install` step. That is not an oversight.

### Run the tests

```bash
python3 -m unittest discover -s tests -v
```

### Reset the demo

Visit `/reset` (or delete `data/state.json`). Do this right before recording, so the
first frame is clean.

---

## How We Use Replit *(required)*

- **Development & hosting.** The prototype is deployed with Replit Deployments; the Live
  Demo link above is that deployment, not a static mock.
- **Configuration.** API keys live in Replit Secrets, never in the repository.
- **Port handling.** The server binds `0.0.0.0` and reads `$PORT`, so the deployment is
  reachable — the single most common reason a Replit deployment looks "broken".
- **Note on account ownership.** Per the official rules, Replit Core is issued per
  participant. In this team only the leader's account holds the credit, and the project,
  deployment and proof of use all sit on that one account, named after the team.
  Proof of use: `submission/SDC2026_RREFCOLLECTION_Replit_POU.pdf`.

## How We Use RunPod *(required)*

**Not used.** CollectLoop has no GPU workload: no training, no fine-tuning, no self-hosted
inference. Drafting is a single LLM API call of a few hundred tokens. Under Participant
Handbook §9.3, RunPod is mandatory only for GPU work, so this project is exempt.

We kept `runpod/handler.py` as an honest placeholder rather than a decorative shell:
it returns `not_implemented` and explains why. Declaration reads
**"Not used in current prototype — no GPU workload."**

---

## SDG alignment

We claim **two** goals, not five, and we say what we are *not* claiming.

### Primary — SDG 8: Decent Work and Economic Growth

| Target | How CollectLoop contributes | How we would measure it |
| --- | --- | --- |
| **8.3** — Promote development-oriented policies that support … micro-, small- and medium-sized enterprises | Shortens the cash-conversion cycle of a micro-wholesaler, which is the binding constraint on whether it can pay staff on time | Days-sales-outstanding (DSO) before vs after; in our synthetic book, 5 of 7 invoices sit in a bucket that would previously have been chased late or not at all |
| **8.2** — Achieve higher levels of economic productivity through … technological upgrading | Moves ~12 minutes of typing per invoice into ~1 minute of review, without adding headcount | Minutes per reminder (12 → 1), hours saved per month at 60 invoices |

The part that matters for SDG 8 rather than "efficiency" in the abstract: the person doing
this work is usually the owner, and the hours recovered are evenings, not payroll.

### Secondary — SDG 9: Industry, Innovation and Infrastructure

| Target | How CollectLoop contributes |
| --- | --- |
| **9.3** — Increase the access of small-scale industrial and other enterprises to … credit | Faster receivables means less reliance on short-term borrowing to cover the gap. The audit trail is also the evidence file a lender asks for when an SME applies for working-capital credit |

### What we deliberately do not claim

- **No SDG 12 / 13 claim.** We are not claiming a measurable environmental benefit.
  Removing paper reminders is real but tiny, and we cannot measure it. Claiming it would
  be a label, and this is exactly the failure mode the domain brief warns about.
- **No SDG 10 claim.** "Helps small businesses" is not the same as reducing inequality
  between groups of people.

Every number above is either computed live in the dashboard or stated as an assumption
with its basis (12-minute manual baseline is from our own interview notes; DSO figures
are illustrative on synthetic data, not a measured result).

---

## Responsible AI

- **Synthetic data only.** Every company, name, email and amount in `data/invoices.json`
  is invented. No real personal data is present, per the competition data rules.
- **The model cannot send.** It produces the body text of a draft. Approval is a human
  action on a separate request.
- **The model cannot invent facts.** The prompt is restricted to the facts passed in
  (invoice number, amount, due date, days overdue) and forbids inventing payment details,
  discounts or legal threats. If it returns anything, it is still shown to a human first.
- **Failures degrade, they do not lie.** If the API is down, the system falls back to a
  template and says so on the review screen (`draft_source`), rather than presenting
  model output that does not exist.
- **Everything is logged, including refusals.** Skipping a customer is recorded.

---

## Challenges & Learnings

- **We removed our framework.** The first build used Flask; deployment failed on a
  dependency mismatch. Rewriting the routing on `http.server` took 30 lines and made the
  demo depend on nothing. Lesson: for a 24-hour build, dependency count is a risk budget.
- **The model was the least important part.** Our first version asked the model to decide
  how urgent each customer was. It was inconsistent between runs, and unexplainable to a
  judge. Moving that decision into an ageing table made the system better *and* made it
  demonstrable.
- **"Human in the loop" is a UI decision, not a sentence in a pitch.** It only became true
  when the draft arrived in an editable box with a required click, and when skipping was
  logged too.

## Future Improvements

- [ ] Wire a real email provider behind the approve button, with a dry-run mode
- [ ] Two-way sync with the invoice system instead of a JSON seed
- [ ] Per-customer escalation memory ("promised to pay on the 20th" becomes a fact next time)
- [ ] Optional local classifier on RunPod to predict which accounts actually pay late
- [ ] Multi-user roles: owner approves above a threshold, assistant approves below

## Team

| Name | Role | GitHub |
| --- | --- | --- |
| `TODO` | Team Lead / Backend & hosting | [@TODO](https://github.com/TODO) |
| `TODO` | Frontend & UX | [@TODO](https://github.com/TODO) |
| `TODO` | Research, PRD & demo video | [@TODO](https://github.com/TODO) |

---

## Submission Checklist

- [x] Team name, domain and SDG track filled in
- [ ] Slide deck link added
- [ ] Demo video link added
- [x] Replit used, with proof of use in `submission/`
- [x] RunPod evaluated and declared not used (no GPU workload)
- [ ] Preliminary submission completed (`SDC2026_RREFCOLLECTION_Preliminary.pdf`)
- [ ] Technology declaration completed (`SDC2026_RREFCOLLECTION_TechDeclaration.pdf`)
- [ ] Submission files renamed with the team name
- [x] "How to Run" steps verified on a clean Replit import
- [x] No API keys or secrets committed to the repository
- [x] `LICENSE` contains the Apache License 2.0

## License

Licensed under the [Apache License 2.0](LICENSE).
