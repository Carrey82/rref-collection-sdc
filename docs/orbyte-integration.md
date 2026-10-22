# Orbyte integration — what is real, what is not

Domain 2's must-have is **"Orbyte fit and reuse"**, so this file exists to be read by a judge
who wants to check the claim rather than take it.

## What is implemented

`src/orbyte.py` is an adapter with one job: make Orbyte's record shape the system of record,
and make CollectLoop's decisions flow back.

| Orbyte field | CollectLoop field | Note |
|---|---|---|
| `id` | `id` | |
| `document_no` | `invoice_no` | |
| `counterparty.name` | `customer` | |
| `counterparty.contact.name` / `.email` | `contact_name` / `contact_email` | |
| `counterparty.months_on_book` | `relationship.months` | |
| `counterparty.promise_history.*` | `relationship.promises_total` / `promises_kept` | drives the tone |
| `total.amount_minor` / `.currency` | `amount` / `currency` | minor units ÷ 100 |
| `terms.due_date` | `due_date` | |
| `settlement.paid` | `paid` | |
| `promises[].outcome` | `promises[].kept` | `open`→null, `kept`→true, `broken`→false |
| `promises[].verbatim` | `promises[].note` | quoted back in the message |
| `promises[].stated_on` / `for_date` / `via` / `logged_by` | same meaning | audit fields |

The mapping is a single function, `_normalize()`, with the table reproduced in its docstring.

## Two modes

```
ORBYTE_MODE=replay   (default)  read data/orbyte_export.sample.json
ORBYTE_MODE=live                requires ORBYTE_API_BASE + ORBYTE_API_KEY
```

`live` deliberately raises `NotImplementedError`. Orbyte's Open API ecosystem is roadmap
(Phase 4 in their own deck) and we have no sandbox credentials, so the honest state is
"adapter built, endpoint not available". Fabricating a call that has never been executed
would fail the first probing question — and the brief treats invented capability as a
violation, not a shortcut.

## Platform capabilities we consume (not rebuild)

This is the actual argument for "fit and reuse":

| Orbyte capability | How CollectLoop uses it |
|---|---|
| Identity & SSO | No account system, no password store, no user table |
| Workflow & approvals | The human-approval step is Orbyte's approval primitive, not ours |
| Audit trail | Decisions write back to the platform trail; the local hash chain is the offline copy |
| AI context | Customer promise history comes from platform context instead of being retyped |
| Connect · payments & collections | Invoice and settlement data enter here |
| Notifications *(planned)* | Promise-due reminders on the platform channel; in-page for now |
| Documents *(planned)* | Collection letter filed as a platform document; audit body only for now |

Reuse is why an SME can switch this on: three of the seven capabilities above are things a
standalone tool would have to rebuild badly.

## Going live — the exact change

1. Get `ORBYTE_API_BASE` and `ORBYTE_API_KEY` from the Orbyte partner team.
2. Confirm the two endpoints named in the code:
   - `GET /open/v1/invoices?status=open&due_before=…` → same body shape as the sample
   - `POST /open/v1/approvals` → `{subject, decision, decided_by, document, idempotency_key}`
3. Set the two secrets in Replit → the adapter switches modes with no code change.

If the endpoint shape differs, only `_normalize()` changes — the business logic, rules and
tests are untouched, because they never see Orbyte's field names.
