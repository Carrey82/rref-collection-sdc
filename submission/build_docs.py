#!/usr/bin/env python3
"""Build the two mandatory SDC 2026 submission PDFs.

  SDC2026_RREFCOLLECTION_Preliminary.pdf      (Phase 1 Project Proposal)
  SDC2026_RREFCOLLECTION_TechDeclaration.pdf  (Technical Tools Declaration)

Both follow the official template section order. Every open-ended answer is
word-counted at build time against the limit printed in the template; the build
fails loudly instead of silently shipping an over-limit answer.

Run:  python3 submission/build_docs.py
"""
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

MYT = timezone(timedelta(hours=8))
TODAY = datetime.now(MYT).strftime("%d %B %Y")

HERE = Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

# ----------------------------------------------------------------------------
# Facts that only the team can supply. Rendered as a fill-in blank when empty,
# and listed again on stderr at the end of the build.
# ----------------------------------------------------------------------------
MEMBERS = "4"
LEADER_EMAIL = "2173083338@qq.com"
LEADER_PHONE = "+86 13906032500"
TEAMMATES = ["ZHANG JINHONG", "WANG ZHILIN", "HONG JUNHAN"]

TEAM = "RREF COLLECTION"
PROJECT = "CollectLoop"
DOMAIN = "Domain 2 — Orbyte Smart SME Challenge"
SDG = "SDG 8 — Decent Work and Economic Growth (primary); SDG 9 — Industry, Innovation and Infrastructure (secondary)"
LEADER = "XIE KAIRUI"
UNIVERSITY = "Xiamen University Malaysia"
LIVE_URL = "https://rref-collection-sdc.replit.app"
REPO_URL = "https://github.com/Carrey82/rref-collection-sdc"


def blank(width: int = 210) -> str:
    return f'<span class="fill" style="width:{width}px">&nbsp;</span>'


def val(x: str, width: int = 210) -> str:
    return x if x else blank(width)


# ----------------------------------------------------------------------------
# PRELIMINARY  (Phase 1 Project Proposal)
# ----------------------------------------------------------------------------
P21 = """A micro-wholesaler in Klang issues 60 to 80 invoices a month. Roughly one in six is paid
late. Chasing those invoices is nobody's job description: it belongs to the owner, squeezed
between deliveries and stock checks, in whatever five minutes are free.

Each reminder costs about twelve minutes - find the invoice, check whether it was already paid,
decide how firm to be this time, write it, verify the numbers, file it somewhere.

Because it is done in fragments, three failures follow. Tone drifts, so a customer three days
late receives the same blunt message as one sixty days late, and goodwill is spent for nothing.
Nothing is recorded, so when the owner is travelling nobody knows who was contacted, how firmly,
or what was agreed. And it is the first task dropped on a busy day, which pushes cash further
out - the one cost a micro-enterprise cannot absorb.

The costliest failure is the invisible one: the promise is never written down. Customers already
name payment dates on calls and in WhatsApp threads. Because those commitments live nowhere, the
owner either chases a customer who has already promised, spending goodwill on someone who is not
the problem, or forgets the one who broke a date they chose themselves. Neither is a writing
problem; both are a memory problem, and no reminder template fixes a memory problem.

This affects more than a million micro, small and medium enterprises in Malaysia, and the staff
whose salaries depend on receivables arriving on time."""

P22 = """CollectLoop is a collections assistant whose unit of work is the promise, not the invoice.
Every customer carries a small ledger: what was promised, for which date, through which channel,
by whom, and whether it was kept. Everything downstream is decided by that ledger, in
deterministic, unit-tested rules. No promise on record: draft the first message in the tone the
ageing bucket calls for. Promise still open: draft nothing, hold the invoice, and count the hold
as a real outcome. Promise broken: draft, and quote the customer's own date back at them. Two
breaches escalate the tone and multiply queue priority.

AI is used at exactly one point, deliberately: writing the prose. A language
model receives a restricted fact set - invoice number, amount, due date, days overdue, the
promise verbatim - and returns the body of one email. It does not choose who is chased, does not
set the tone, and cannot send. A person opens each draft in an editable box and approves or skips
it; both outcomes are written to an append-only log with a hash chain. If no model is configured,
or the endpoint fails, the system falls back to a hand-written template and labels the draft
source in the interface, so the product degrades instead of white-screening.

The Phase 1 workshops shaped three decisions. The GenAI API session set the model layer:
a system prompt with hard prohibitions, and an explicit fallback path. The database-architecture
session shaped the audit design, because a collections trail has to be tamper-evident, not merely
persisted. Cloud deployment is how this reaches judges as a public URL rather than a screenshot.
The stack is the Python standard library only, because the clearest lesson was that a
prototype dies at the dependency step far more often than at the logic step."""

P32 = """Design thinking was applied as narrowing decisions, not as a phase label.

Empathise: we interviewed a micro-wholesaler's owner about the last time a customer paid late.
The detail that changed the project was not the invoice - it was that three customers had already
named a date, on a call or in a chat, and that nobody could recall which.

Define: the problem statement became "the promise exists but never reaches the system", not
"reminders are slow to write". The second framing invites a template; the first one does not.

Ideate: we built the obvious version first - ask a model how urgent each customer is. It gave
different answers on identical inputs. Killing it and putting urgency in an ageing table made the
product both better and explainable to a judge in one sentence.

Prototype and test: rules first, model last. Forty-five unit tests cover the decision layer and
the intake validation, so tone and priority can be changed without a regression.

Deployment strategy: zero dependencies, one process, all configuration through environment
variables, and the rules in one file, so a second SME reuses the product by editing config rather
than code - which is what "Orbyte fit and reuse" requires."""

IMPACT_ROWS = [
    (
        "Receivables cycle "
        "<span class='sub'>(primary)</span>",
        "<b>SDG 8.3</b> - promote development-oriented policies that support micro-, small- and "
        "medium-sized enterprises.",
        "12 minutes of manual work per reminder; roughly 12 late invoices a month, so about "
        "2.4 hours of the owner's month, done in fragments and often skipped. Illustrative DSO "
        "on our synthetic book: 34 days.",
        "Minutes of human work per reminder; and share of would-be chases correctly suppressed "
        "because a promise is still open.",
        "12 min to 3 min per reminder (-75%), with at least 30% of the scanned queue held instead "
        "of chased.",
    ),
    (
        "Productivity "
        "<span class='sub'>(primary)</span>",
        "<b>SDG 8.2</b> - achieve higher levels of economic productivity through technological "
        "upgrading.",
        "Every reminder is typed from scratch, at 12 minutes each, by the person who should be "
        "selling. Zero reminders are logged, so no process can be improved later.",
        "Minutes recovered per month per SME; share of decisions that reach the append-only audit "
        "log.",
        "100% of approved or skipped drafts logged with a hash chain; 2.4 hours a month recovered "
        "per SME.",
    ),
    (
        "Access to finance "
        "<span class='sub'>(secondary)</span>",
        "<b>SDG 9.3</b> - increase the access of small-scale enterprises to credit.",
        "No receivables history exists in a form a lender would accept, so working-capital credit "
        "is priced on the owner's word.",
        "Count of exportable, tamper-evident payment-promise records per customer.",
        "One exportable per-customer promise history that a lender can audit, covering 100% of "
        "invoiced customers.",
    ),
]

IMPACT_NOTE = """<b>On the honesty of these numbers.</b> The 12-minute baseline comes from our own
interview notes and is stated as an assumption, not a measurement; the 60 to 80 invoice volume and
the one-in-six late rate are the owner's estimates. The 34-day DSO figure is illustrative on
synthetic data. Phase 2 measures the real values on the same book, so the KPI in the third column
is what we will report rather than a projection we cannot support. The MSME population figure is
from the Department of Statistics Malaysia, which reports that MSMEs make up 97.4% of business
establishments in Malaysia."""

STACK_PRELIM = [
    ("Language", "Python 3.11", "Backend, routing and all business logic"),
    ("Web layer", "Python standard library <code>http.server</code>", "Server-rendered HTML; no framework, no build step"),
    ("Templates", "Plain HTML + one CSS file", "Six pages; no client-side JavaScript at all"),
    ("Persistence", "JSON files on disk + append-only JSONL audit log", "Invoice book, runtime state, hash-chained decision log"),
    ("AI layer", "Any OpenAI-compatible chat completions endpoint", "Drafts one email body from a restricted fact set"),
    ("AI fallback", "Deterministic template in <code>src/llm.py</code>", "Keeps the product working with no model configured"),
    ("Integration", "Orbyte export adapter (<code>src/orbyte.py</code>)", "Orbyte field names become the system of record; replay mode by default"),
    ("Testing", "<code>unittest</code>, 45 tests, zero dependencies", "Decision rules, intake validation, security headers"),
    ("Hosting", "Replit Deployments (sponsor-provided Core)", "Public live URL for judges"),
    ("Version control", "Git + GitHub, Apache-2.0", "Public repository, full commit history"),
]

DIAGRAM = """
<svg viewBox="0 0 720 250" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <marker id="a" markerWidth="9" markerHeight="9" refX="7" refY="3.2" orient="auto">
      <path d="M0,0 L7,3.2 L0,6.4 z" fill="#475569"/>
    </marker>
  </defs>
  <rect x="8" y="10" width="704" height="230" rx="10" fill="#F8FAFC" stroke="#CBD5E1"/>
  <text x="22" y="32" font-family="Arial" font-size="11" fill="#64748B">BROWSER (owner)</text>

  <rect x="24" y="46" width="118" height="60" rx="7" fill="#EFF6FF" stroke="#2563EB" stroke-width="1.4"/>
  <text x="83" y="70" text-anchor="middle" font-family="Arial" font-size="11.5" font-weight="bold" fill="#0F172A">Dashboard</text>
  <text x="83" y="87" text-anchor="middle" font-family="Arial" font-size="9.5" fill="#475569">Run today's scan</text>

  <rect x="24" y="128" width="118" height="60" rx="7" fill="#EFF6FF" stroke="#2563EB" stroke-width="1.4"/>
  <text x="83" y="152" text-anchor="middle" font-family="Arial" font-size="11.5" font-weight="bold" fill="#0F172A">Review page</text>
  <text x="83" y="169" text-anchor="middle" font-family="Arial" font-size="9.5" fill="#475569">editable draft</text>

  <rect x="24" y="204" width="118" height="26" rx="6" fill="#FFFFFF" stroke="#CBD5E1"/>
  <text x="83" y="221" text-anchor="middle" font-family="Arial" font-size="9.5" fill="#475569">/upload · /ai · /audit</text>

  <line x1="142" y1="76" x2="196" y2="76" stroke="#475569" stroke-width="1.2" marker-end="url(#a)"/>
  <text x="169" y="68" text-anchor="middle" font-family="Arial" font-size="8.5" fill="#64748B">POST /scan</text>
  <line x1="196" y1="150" x2="142" y2="150" stroke="#475569" stroke-width="1.2" marker-end="url(#a)"/>
  <text x="169" y="142" text-anchor="middle" font-family="Arial" font-size="8.5" fill="#64748B">draft</text>

  <rect x="198" y="40" width="150" height="180" rx="8" fill="#FFFFFF" stroke="#94A3B8" stroke-dasharray="4 3"/>
  <text x="273" y="32" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold" fill="#475569">src/app.py</text>

  <rect x="212" y="54" width="122" height="34" rx="6" fill="#F1F5F9" stroke="#CBD5E1"/>
  <text x="273" y="75" text-anchor="middle" font-family="Arial" font-size="10" fill="#0F172A">1 routing</text>

  <rect x="212" y="96" width="122" height="34" rx="6" fill="#F1F5F9" stroke="#CBD5E1"/>
  <text x="273" y="117" text-anchor="middle" font-family="Arial" font-size="10" fill="#0F172A">2 fetch</text>

  <rect x="212" y="138" width="122" height="34" rx="6" fill="#F1F5F9" stroke="#CBD5E1"/>
  <text x="273" y="159" text-anchor="middle" font-family="Arial" font-size="10" fill="#0F172A">3 rules + 4 draft</text>

  <rect x="212" y="180" width="122" height="30" rx="6" fill="#F1F5F9" stroke="#CBD5E1"/>
  <text x="273" y="200" text-anchor="middle" font-family="Arial" font-size="10" fill="#0F172A">5 record</text>

  <line x1="348" y1="66" x2="404" y2="66" stroke="#475569" stroke-width="1.2" marker-end="url(#a)"/>
  <line x1="348" y1="113" x2="404" y2="113" stroke="#475569" stroke-width="1.2" marker-end="url(#a)"/>
  <line x1="348" y1="155" x2="404" y2="155" stroke="#475569" stroke-width="1.2" marker-end="url(#a)"/>
  <line x1="348" y1="195" x2="404" y2="195" stroke="#475569" stroke-width="1.2" marker-end="url(#a)"/>

  <rect x="406" y="46" width="140" height="42" rx="6" fill="#FFFFFF" stroke="#CBD5E1"/>
  <text x="476" y="63" text-anchor="middle" font-family="Arial" font-size="10" fill="#0F172A">invoices.json</text>
  <text x="476" y="78" text-anchor="middle" font-family="Arial" font-size="8.5" fill="#64748B">or Orbyte export</text>

  <rect x="406" y="96" width="140" height="42" rx="6" fill="#FFF7ED" stroke="#F59E0B" stroke-width="1.4"/>
  <text x="476" y="113" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold" fill="#0F172A">LLM endpoint</text>
  <text x="476" y="128" text-anchor="middle" font-family="Arial" font-size="8.5" fill="#92400E">prose only · optional</text>

  <rect x="406" y="146" width="140" height="42" rx="6" fill="#FFFFFF" stroke="#CBD5E1"/>
  <text x="476" y="163" text-anchor="middle" font-family="Arial" font-size="10" fill="#0F172A">logic.py</text>
  <text x="476" y="178" text-anchor="middle" font-family="Arial" font-size="8.5" fill="#64748B">buckets · tone · score</text>

  <rect x="406" y="188" width="140" height="32" rx="6" fill="#ECFDF5" stroke="#059669"/>
  <text x="476" y="208" text-anchor="middle" font-family="Arial" font-size="9.5" fill="#065F46">audit_log.jsonl (hash chain)</text>

  <rect x="578" y="96" width="126" height="42" rx="6" fill="#EFF6FF" stroke="#2563EB"/>
  <text x="641" y="113" text-anchor="middle" font-family="Arial" font-size="10" font-weight="bold" fill="#0F172A">Replit</text>
  <text x="641" y="128" text-anchor="middle" font-family="Arial" font-size="8.5" fill="#475569">Deployments</text>
  <line x1="548" y1="117" x2="576" y2="117" stroke="#475569" stroke-width="1.2" marker-end="url(#a)"/>
  <text x="641" y="163" text-anchor="middle" font-family="Arial" font-size="8.5" fill="#64748B">$PORT · 0.0.0.0</text>
  <text x="641" y="178" text-anchor="middle" font-family="Arial" font-size="8.5" fill="#64748B">secrets in env</text>
</svg>"""

# ----------------------------------------------------------------------------
# TECH DECLARATION
# ----------------------------------------------------------------------------
T21 = """CollectLoop is one Python process that serves server-rendered HTML; there is no separate
frontend build and no client-side JavaScript. Requests enter src/app.py, which routes seven
endpoints: dashboard, intake, the AI explainer, review, audit, reset, and the scan trigger.

The operational path has five stages. (1) Trigger: the owner presses "Run today's scan", which
posts to /scan. (2) Fetch: store.py loads the invoice book from JSON on disk, or src/orbyte.py
normalises an Orbyte export into the same internal shape. (3) Logic: logic.py computes ageing
buckets, a priority score and a queue summary, deciding who is chased, who is held and in which
tone. (4) Drafting and approval: llm.py builds a fact-restricted prompt and calls an
OpenAI-compatible chat endpoint, or falls back to a template; the draft arrives in an editable
review page and waits for a human click. (5) Record: store.append_audit writes the decision, the
final text and the previous entry's hash to an append-only JSONL log.

Hosting is Replit Deployments; the process binds 0.0.0.0 and reads $PORT. State, audit log and
credentials stay outside the repository."""

T22 = [
    ("Python 3.11", "PSF-2.0", "Language and runtime for the whole application"),
    ("Python standard library (<code>http.server</code>, <code>json</code>, <code>hashlib</code>, <code>urllib</code>, <code>html</code>)",
     "PSF-2.0", "Web server, JSON persistence, audit hash chain, model HTTP call, HTML escaping"),
    ("<code>unittest</code> (standard library)", "PSF-2.0", "45 tests: decision rules, intake validation, security headers"),
    ("No third-party runtime library", "-", "Deliberate: the prototype installs nothing, so deployment cannot fail on a dependency"),
    ("Apache License 2.0", "Apache-2.0", "Licence we publish our own code under"),
]

T31 = [
    ("OpenAI-compatible Chat Completions API<br><span class='sub'>(provider and model configurable; <code>gpt-4o-mini</code> class in the default config)</span>",
     "Free tier / pay-as-you-go, configured by the team. No SDC sponsor GenAI credit was issued to or used by this team.",
     "Writes the body of one reminder email from a restricted fact set. Optional: with no key configured the system uses a deterministic template and labels the source in the UI."),
    ("Orbyte platform (Domain 2 sponsor) - export schema, not a live API",
     "No credentials issued; Orbyte's Open API is roadmap on their side",
     "We model our internal records on Orbyte's field names and ship an adapter (<code>src/orbyte.py</code>) plus a synthetic export sample. <b>No Orbyte endpoint has been called.</b> <code>ORBYTE_MODE=live</code> deliberately raises NotImplementedError."),
]

T32 = [
    ("Replit - Deployments (Autoscale)", "Replit Core, sponsor-provided (issued to the team leader)",
     "Hosts the prototype; serves the public <code>*.replit.app</code> URL and runs <code>python3 src/app.py</code>"),
    ("Replit Secrets", "Replit Core", "Holds <code>LLM_API_KEY</code> if one is configured; never in the repository"),
    ("WorkBuddy Sites (static/app hosting)", "Free tier",
     "Secondary public URL used if the Replit deployment is unavailable during judging"),
    ("GitHub", "Free (public repository)", "Source control, commit history, public judge access, Apache-2.0 licence"),
    ("RunPod", "Not used", "No GPU workload: no training, no fine-tuning, no self-hosted inference. <code>runpod/handler.py</code> returns <code>not_implemented</code> by design."),
]

T41 = [
    ("OpenAI-compatible chat model (<code>gpt-4o-mini</code> class; exact model set by <code>LLM_MODEL</code>)",
     "api.openai.com or any compatible provider", "Provider terms of service; pre-trained weights, not redistributed",
     "Pre-trained, used as a hosted API. No fine-tuning, no self-hosted weights."),
    ("No model is embedded in this build",
     "-", "-",
     "In the submitted deployment no API key is configured, so every draft on the live URL comes from the deterministic template. The model call is wired (<code>src/llm.py</code>) and the <code>/ai</code> page states the current mode openly."),
]

T42 = [
    ("<code>data/invoices.json</code> - 7 synthetic invoices and customer histories",
     "Self-authored, synthetic", "N", "Synthetic",
     "Committed in the repository. Every company, person, email and amount is invented, including reserved <code>.example</code> domains."),
    ("<code>data/orbyte_export.sample.json</code> - synthetic Orbyte export",
     "Self-authored, synthetic", "N", "Synthetic",
     "Models Orbyte's documented field names so the adapter can be reviewed. Contains no real customer data."),
]

T43 = [
    ("WorkBuddy (agentic coding assistant)", "Major",
     "Repository scaffolding, HTTP routing and template layer, unit tests, security headers, documentation drafting, and the generation of these submission PDFs"),
    ("GitHub Copilot (GitHub Student account)", "Minor",
     "In-editor completion and small refactors while reviewing the code"),
]

T43_REVIEW = """Every AI-generated change was reviewed against a test suite before acceptance: 45
unittest cases cover the decision rules, intake validation and security headers, and all 45 pass on
the submitted commit. Anything a judge could question sits in plain files we can defend line by
line - the ageing buckets and tone ladder in src/logic.py, the prompt in src/llm.py. We also
rejected two AI suggestions: a Flask-based framework layer that broke deployment, and letting the
model choose urgency, because it gave different answers for identical inputs. The team owns every
claim here."""

T51 = [
    ("Replit Core (cloud platform and deployment credits)", "Orbyte / SDC 2026 sponsor agreement (issued per participant to the team leader)",
     "Hosts the deployed prototype and the public live URL; secrets storage; the deployment that judges open"),
    ("SDC Phase 1 workshops (GenAI API, database architecture, cloud deployment)", "SDC / XMUM AI Club",
     "Shaped the model layer, the audit design and the deployment approach; no workshop code is embedded"),
    ("Orbyte platform (Domain 2 sponsor)", "SDC Domain 2 sponsor",
     "Domain brief, data model and field naming. No API credentials were issued and no Orbyte endpoint was called."),
]

T52 = """The Replit deployment was essential at submission time: it is the address judges open, and
it satisfies Handbook 10.6 proof of use. It is not essential to the product. There are no
proprietary calls - the application is one Python process with zero dependencies, and porting it to
any container host took minutes, which is exactly what we did when the first Replit publish failed:
the same commit now also runs on a second public host. Orbyte matters as a data contract, not as a
runtime dependency, so its absence constrains the integration, not the prototype."""

T61 = """No real user data is collected, stored or transmitted. The invoice book, customer names,
emails and amounts in data/invoices.json are synthetic; emails use the reserved .example domain.
The intake form at /upload accepts six typed fields and stores them in a local JSON file on the
hosting instance. There is no account system, no login, no analytics and no application cookies. When a model is configured, only the fact set needed to draft one email is sent
to the provider - invoice number, amount in MYR, due date, days overdue and the customer's recorded
promise, which is already synthetic; no free-text personal notes, and no API key in the browser.
The append-only audit log stores the decision, the final draft text and a hash chain on the same
instance. Retention: until the demo is reset (/reset or a redeploy), after which the runtime state
is gone."""

T62 = """Four limitations are known and stated rather than hidden. Hallucination: the model only
writes prose from a closed fact set and cannot invent amounts, dates or legal threats; a human
approves every send, and sending itself is deliberately unwired. Provider dependency and rate
limits: the call has a timeout and falls back to a template, and the interface labels which source
produced the draft, so the demo degrades visibly instead of white-screening. Explainability: tone
and priority are deterministic rules in one file, not model output, so any decision can be
reproduced and argued. Data layer: JSON files are not concurrency-safe and are single-tenant, which
is acceptable for one SME's book and not for multi-user deployment; the Orbyte integration is an
adapter with no live endpoint, and no OCR or QR intake is implemented. Synthetic data means the
measured business impact is illustrative, not evidence."""

TECH_CHECK = [
    "All APIs, cloud services, AI tools, models, and datasets used in the project are declared in this document.",
    "All third-party code, datasets, and models are used in accordance with their licenses, and attribution is provided where required.",
    "No API keys, passwords, or other credentials are exposed in the code repository, prototype, or this document.",
    "Any use of generative-AI tools for development has been disclosed and reviewed by the team.",
    "Any use of official SDC sponsor resources has been declared in Section 5.",
    "The prototype described here is accessible to judges through the links provided in Section 1.",
    "All fields in this template have been completed within the word limits stated.",
]

PRELIM_CHECK = [
    "All team members have completed the mandatory GenAI, Database, and Cloud Deployment upskilling workshops.",
    "The project concept addresses a verified real-world problem mapped directly to one or more UN SDGs.",
    "The proposed solution targets a functional, deployed application rather than a theoretical business case study.",
    "All fields in this template have been completed within the word limits stated.",
]

# ----------------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------------
CSS = """
@page { size: A4; margin: 16mm 15mm 14mm 15mm; }
* { box-sizing: border-box; }
body { margin:0; font-family: Arial, Helvetica, sans-serif; font-size:10pt; line-height:1.5;
       color:#0F172A; -webkit-print-color-adjust:exact; print-color-adjust:exact; }
h1 { font-size:19pt; margin:0 0 2mm; letter-spacing:-0.3px; }
.titleband { border-top:4px solid #2563EB; padding-top:5mm; margin-bottom:6mm; }
.eyebrow { font-size:8pt; letter-spacing:1.6px; text-transform:uppercase; color:#2563EB; font-weight:bold; }
.subtitle { font-size:9.5pt; color:#475569; margin-top:1.5mm; }
h2 { font-size:11.5pt; margin:7mm 0 3mm; padding:2.2mm 3mm; background:#EFF6FF;
     border-left:3.5px solid #2563EB; page-break-after:avoid; }
h2 .num { color:#2563EB; margin-right:2.5mm; }
h3 { font-size:10pt; margin:4.5mm 0 1.8mm; color:#0F172A; page-break-after:avoid; }
p { margin:0 0 2.6mm; text-align:justify; }
.prompt { color:#64748B; font-style:italic; font-size:9pt; margin:0 0 2mm; }
table { width:100%; border-collapse:collapse; margin:2mm 0 3mm; page-break-inside:avoid; }
th, td { border:0.6pt solid #CBD5E1; padding:1.9mm 2.4mm; font-size:9pt; vertical-align:top; text-align:left; }
th { background:#F1F5F9; font-size:8pt; letter-spacing:0.4px; text-transform:uppercase; color:#475569; }
td.k { background:#F8FAFC; font-weight:bold; width:26%; font-size:9pt; }
.sub { font-size:8pt; color:#64748B; font-weight:normal; }
.fill { display:inline-block; border-bottom:0.9pt solid #94A3B8; height:4mm; }
code { font-family:"Courier New", monospace; font-size:8.6pt; background:#F1F5F9; padding:0 1px; }
ol, ul { margin:0 0 2.6mm; padding-left:6mm; }
li { margin-bottom:1.4mm; text-align:justify; }
.box { border:0.6pt solid #CBD5E1; background:#F8FAFC; padding:3mm 3.5mm; margin:3mm 0; font-size:9pt; }
.note { font-size:8.5pt; color:#475569; }
.check { list-style:none; padding-left:0; }
.check li { margin-bottom:2.2mm; }
.check .bx { color:#2563EB; font-weight:bold; margin-right:2mm; }
.sig { margin-top:8mm; display:flex; gap:14mm; }
.sig div { flex:1; border-top:0.8pt solid #0F172A; padding-top:1.6mm; font-size:8.5pt; color:#475569; }
.diagram { margin:3mm 0 4mm; }
.diagram svg { width:100%; height:auto; }
.foot { margin-top:7mm; border-top:0.6pt solid #CBD5E1; padding-top:2mm; font-size:8pt; color:#94A3B8; }
.pb { page-break-before:always; }
"""


def h2(num: str, title: str) -> str:
    return f'<h2><span class="num">{num}</span>{title}</h2>'


def table(headers, rows, keyed=False) -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = []
    for r in rows:
        cells = "".join(
            f'<td class="k">{c}</td>' if (keyed and i == 0) else f"<td>{c}</td>"
            for i, c in enumerate(r)
        )
        body.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def checks(items) -> str:
    lis = "".join(f'<li><span class="bx">&#9745;</span>{i}</li>' for i in items)
    return f'<ul class="check">{lis}</ul>'


def paras(text: str) -> str:
    return "".join(f"<p>{re.sub(r'[ \t]*\n[ \t]*', ' ', p).strip()}</p>" for p in text.split("\n\n"))


def title(kind: str, kicker: str, headline: str, sub: str) -> str:
    return (
        '<div class="titleband">'
        f'<div class="eyebrow">SDC 2026 &middot; XMUM AI Club &middot; {kind}</div>'
        f'<h1>{headline}</h1>'
        f'<div class="subtitle">{kicker} &middot; {sub} &middot; Submission deadline 25 October 2026</div>'
        "</div>"
    )


def identity_rows():
    return [
        ("Team Name", TEAM),
        ("Project / Solution Name", PROJECT),
        ("Name (Leader)", LEADER),
        ("Email &amp; Phone (Leader)", f"{val(LEADER_EMAIL, 190)} &nbsp; {val(LEADER_PHONE, 120)}"),
        ("University Affiliation(s)", UNIVERSITY),
        ("Live Prototype URL", LIVE_URL),
        ("Code Repository URL (public / access granted to judges)", REPO_URL),
    ]


def build_preliminary() -> str:
    impact = IMPACT_ROWS
    rows = "".join(
        f"<tr><td class='k' style='width:20%'>{cat}</td><td style='width:26%'>{sdg}</td>"
        f"<td style='width:20%'>{base}</td><td style='width:17%'>{kpi}</td>"
        f"<td style='width:17%'>{target}</td></tr>"
        for cat, sdg, base, kpi, target in impact
    )
    return f"""<div class="doc">
{title("Phase 1 Preliminary", "Project Proposal", "CollectLoop", TEAM)}
{h2("1", "Team and Project Overview")}
{table(
    ["Field", "Response"],
    [
        ("Team Name", TEAM),
        ("Selected Domain", DOMAIN),
        ("Selected SDG Track (1-17)", SDG),
        ("Project / Solution Name", PROJECT),
        ("Name (Leader)", LEADER),
        ("Email &amp; Phone (Leader)", f"{val(LEADER_EMAIL, 180)} &nbsp;&nbsp; {val(LEADER_PHONE, 110)}"),
        ("University Affiliation(s)", UNIVERSITY),
        ("Number of Team Members", val(MEMBERS, 60)),
    ],
)}
<div class="box note"><b>In one sentence.</b> CollectLoop chases the promise, not the invoice: it keeps
every verbal payment commitment on record, drafts the reminder only when the promise is gone, and
stays silent - on purpose - while it is still good.</div>

{h2("2", "Executive Summary &amp; Problem Statement")}
<h3>2.1. The Problem Context</h3>
<div class="prompt">Describe the specific, real-world challenge your team is tackling. Who is affected, and why does it matter? [Maximum 250 words]</div>
{paras(P21)}

<h3>2.2. The Proposed AI Solution</h3>
<div class="prompt">High-level overview: how does the application apply AI to the problem above, and which SDC Phase 1 workshop tools does it leverage? [Maximum 300 words]</div>
{paras(P22)}

<div class="pb"></div>
{h2("3", "Technical Architecture &amp; Implementation Plan")}
<h3>3.1. Conceptual Tech Stack</h3>
<div class="prompt">Technologies, frameworks, APIs and databases used to build a functional, deployed prototype.</div>
{table(["Layer", "Technology", "Role"], STACK_PRELIM, keyed=True)}
<div class="diagram">{DIAGRAM}</div>
<div class="box"><b>Official SDC sponsor GenAI API or Cloud Platform?</b> Yes - <b>Replit Core</b>,
issued to the team leader under the sponsor agreement. It hosts the deployed prototype and the
public live URL judges open. <b>Orbyte</b> (Domain 2 sponsor) supplied the domain brief and data
contract; no Orbyte API credentials were issued, so the adapter runs on a synthetic export and no
Orbyte endpoint has been called. No sponsor GenAI credit was used. <b>RunPod: not used</b> - there
is no GPU workload in this prototype.</div>

<h3>3.2. Design-Thinking &amp; Deployment Strategy</h3>
<div class="prompt">How the team applied design thinking to make the solution viable, usable and deployable by Phase 2. [Maximum 200 words]</div>
{paras(P32)}

<div class="pb"></div>
{h2("4", "Preliminary Environmental &amp; SDG Impact Framework")}
<div class="prompt">Baseline and target for judges to assess Innovation, Creativity and Feasibility. Numbers are estimated or cited where measurement is not yet possible.</div>
<table>
  <thead><tr>
    <th style="width:20%">Metric Category</th><th style="width:26%">Target SDG Sub-Target(s)</th>
    <th style="width:20%">Current Problem Baseline</th><th style="width:17%">Core Measurable KPI</th>
    <th style="width:17%">Phase 2 Impact Target</th>
  </tr></thead>
  <tbody>{rows}</tbody>
</table>
<div class="box note">{IMPACT_NOTE}</div>
<div class="box note"><b>What we deliberately do not claim.</b> No SDG 12 or 13 claim: removing paper
reminders is real but too small to measure, and claiming it would be a label rather than an
outcome. No SDG 10 claim: helping small businesses is not the same as reducing inequality between
groups of people.</div>

{h2("5", "Eligibility &amp; Readiness Checklist")}
{checks(PRELIM_CHECK)}

{h2("6", "IP &amp; Originality Declaration")}
<h3>6.1. Pre-Existing / Prior-Owned Work</h3>
<p>Does this submission include code, design, research or other work created before the start of
this hackathon?</p>
<table><tbody>
  <tr><td class="k" style="width:22%">Answer</td><td><b>No.</b> All application code, templates,
  copy, the decision rules and this document were created during the SDC 2026 hackathon period.</td></tr>
</tbody></table>

<h3>6.2. Third-Party Code, Datasets, or Models</h3>
<p>Does the project use third-party code libraries, frameworks, datasets or pre-trained models that
the team did not create?</p>
{table(
    ["Name", "Type", "License", "Notes"],
    [
        ("Python 3.11 standard library", "Code", "PSF-2.0",
         "The only runtime dependency; used for HTTP, JSON, hashing and escaping. No pip install step."),
        ("<code>gpt-4o-mini</code> class chat model (optional, via OpenAI-compatible API)", "Model",
         "Provider terms of service", "Pre-trained, called as a hosted API; not redistributed, not fine-tuned."),
        ("Synthetic invoice book and Orbyte export sample", "Dataset", "Self-authored, synthetic",
         "Invented for this project; no real personal data."),
    ],
)}

<h3>6.3. Employment-Related IP Conflicts</h3>
<p>Is any team member bound by an agreement under which an employer could claim ownership of work
created during this hackathon?</p>
<table><tbody>
  <tr><td class="k" style="width:22%">Answer</td><td><b>No.</b> All members are students and are not
  bound by any such employment, internship or consulting agreement.</td></tr>
</tbody></table>

{h2("7", "Declaration")}
<p>By submitting this proposal, the team leader confirms that the information provided is accurate to
the best of the team's knowledge and that the project is original work created during the SDC 2026
hackathon period.</p>
<div class="sig">
  <div>Signature - {LEADER}, Team Leader, {TEAM}</div>
  <div>Date - {TODAY}</div>
</div>
<div class="foot">SDC2026_{TEAM.replace(' ', '')}_Preliminary.pdf &middot; {TEAM} &middot; {PROJECT} &middot; {LIVE_URL}</div>
</div>"""


def build_declaration() -> str:
    return f"""<div class="doc">
{title("Technical Tools Declaration", "Technical Tools Declaration", "Declared Tools &amp; Resources", TEAM)}
<div class="box note"><b>Instructions followed.</b> Every API, cloud service, AI tool, dataset, model
and sponsor resource used to build CollectLoop is declared below. Where a category does not apply we
have written "None" or "Not used" rather than leaving the field blank. No API keys or secrets appear
in this document.</div>

{h2("1", "Team and Project Overview")}
{table(["Field", "Response"], identity_rows(), keyed=True)}

{h2("2", "Architecture &amp; Technology Stack")}
<h3>2.1. System Architecture Overview</h3>
<div class="prompt">How the declared components connect end-to-end. [Maximum 200 words]</div>
{paras(T21)}
<div class="diagram">{DIAGRAM}</div>

<h3>2.2. Languages, Frameworks &amp; Libraries</h3>
<div class="prompt">Main languages, frameworks and third-party libraries the team did not create.</div>
{table(["Name &amp; Version", "License", "Purpose in Project"], T22, keyed=True)}

<div class="pb"></div>
{h2("3", "APIs &amp; Cloud Services")}
<h3>3.1. External APIs</h3>
<div class="prompt">Every external API the solution calls. No keys or secrets are included.</div>
{table(["API and Provider", "Access Tier", "Purpose in Project"], T31, keyed=True)}

<h3>3.2. Cloud Platforms &amp; Deployment</h3>
<div class="prompt">Every cloud service used for hosting, storage, databases, authentication or compute.</div>
{table(["Service &amp; Provider", "Plan / Region", "Purpose in Project"], T32, keyed=True)}

<div class="pb"></div>
{h2("4", "AI Tools, Models &amp; Datasets")}
<h3>4.1. AI Models Used in the Solution</h3>
<div class="prompt">Every model embedded in or called by the application, pre-trained, fine-tuned or self-trained.</div>
{table(["Model &amp; Version", "Source / Provider", "License / Terms", "Usage"], T41, keyed=True)}

<h3>4.2. Datasets</h3>
<div class="prompt">All datasets used for training, fine-tuning, evaluation or in the running application.</div>
{table(["Dataset Name", "License", "Personal Data?", "Type", "Source / URL"], T42, keyed=True)}

<h3>4.3. AI-Assisted Development Tools</h3>
<p>Did your team use any generative-AI tool to help create code, design, text or other project
material? &nbsp; <b>&#9745; Yes</b> &nbsp; &#9744; No</p>
{table(["Tool &amp; Version", "Extent of Use", "Used For"], T43, keyed=True)}
<div class="prompt" style="margin-top:3mm">How the team reviewed, tested and took responsibility for AI-generated output. [Maximum 100 words]</div>
{paras(T43_REVIEW)}

<div class="pb"></div>
{h2("5", "Sponsor-Provided Resources")}
<p>Did your project use any official SDC sponsor-provided resource? &nbsp; <b>&#9745; Yes</b> &nbsp; &#9744; No</p>
{table(["Resource", "Sponsor", "How It Was Used"], T51, keyed=True)}
<div class="prompt" style="margin-top:3mm">Was the sponsor resource essential to core functionality, or could it be replaced? [Maximum 100 words]</div>
{paras(T52)}

{h2("6", "Security, Privacy &amp; Responsible Use")}
<h3>6.1. Data Handling &amp; Privacy</h3>
<div class="prompt">What user or personal data is collected, stored or sent to third parties, how is it protected, and how long is it kept? [Maximum 150 words]</div>
{paras(T61)}

<h3>6.2. Known Limitations &amp; Risks</h3>
<div class="prompt">Main technical limitations of the AI components and any mitigation implemented. [Maximum 150 words]</div>
{paras(T62)}

{h2("7", "Compliance &amp; Readiness")}
<div class="prompt">Tick all boxes that apply before submitting.</div>
{checks(TECH_CHECK)}

{h2("8", "Declaration")}
<p>By submitting this document, the team leader confirms that the information provided is complete and
accurate to the best of the team's knowledge, and that every API, cloud service, AI tool, dataset,
model and sponsor resource used in the project has been declared.</p>
<div class="sig">
  <div>Signature - {LEADER}, Team Leader, {TEAM}</div>
  <div>Date - {TODAY}</div>
</div>
<div class="foot">SDC2026_{TEAM.replace(' ', '')}_TechDeclaration.pdf &middot; {TEAM} &middot; {PROJECT} &middot; {REPO_URL}</div>
</div>"""


def count_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-]*", text))


def check(text: str, limit: int, label: str, errors: list) -> None:
    n = count_words(text)
    flag = "ok " if n <= limit else "OVER"
    print(f"  [{flag}] {label}: {n}/{limit} words")
    if n > limit:
        errors.append(label)


def build_pdf(name: str, body: str, errors: list) -> None:
    html_path = HERE / f"{name}.html"
    pdf_path = HERE / f"{name}.pdf"
    html_path.write_text(
        f'<!DOCTYPE html><html lang="en"><head><meta charset="utf-8">'
        f"<title>{name}</title><style>{CSS}</style></head><body>{body}</body></html>",
        encoding="utf-8",
    )
    subprocess.run(
        [CHROME, "--headless", "--no-sandbox", "--disable-gpu", "--no-pdf-header-footer",
         "--no-first-run", "--disable-extensions",
         f"--user-data-dir={HERE / '.chrome-profile'}",
         "--virtual-time-budget=3000", f"--print-to-pdf={pdf_path}", html_path.as_uri()],
        check=True, capture_output=True,
    )
    for tmp in (HERE / ".chrome-profile",):
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"  -> {pdf_path.name}  ({pdf_path.stat().st_size/1024:.0f} KB)")


def main() -> int:
    errors, empty = [], []
    print("Word limits (Preliminary):")
    check(P21, 250, "2.1 problem context", errors)
    check(P22, 300, "2.2 proposed solution", errors)
    check(P32, 200, "3.2 design thinking", errors)
    print("Word limits (Tech Declaration):")
    check(T21, 200, "2.1 architecture", errors)
    check(T43_REVIEW, 100, "4.3 review statement", errors)
    check(T52, 100, "5 sponsor essential?", errors)
    check(T61, 150, "6.1 data handling", errors)
    check(T62, 150, "6.2 limitations", errors)

    print("\nBuilding PDFs:")
    build_pdf(f"SDC2026_{TEAM.replace(' ', '')}_Preliminary", build_preliminary(), errors)
    build_pdf(f"SDC2026_{TEAM.replace(' ', '')}_TechDeclaration", build_declaration(), errors)

    for label, value in (("Number of Team Members", MEMBERS),
                         ("Leader email", LEADER_EMAIL),
                         ("Leader phone", LEADER_PHONE)):
        if not value.strip():
            empty.append(label)
    if empty:
        print("\n!! Left blank in the PDFs: " + ", ".join(empty))
        print("   Fill MEMBERS / LEADER_EMAIL / LEADER_PHONE at the top of this script and re-run.")
    if errors:
        print("\n!! Over the word limit: " + ", ".join(errors))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
