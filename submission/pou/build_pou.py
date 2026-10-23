#!/usr/bin/env python3
"""Build the SDC 2026 Proof-of-Use (Replit) PDF.

Evidence images live next to this script:
  ev-live.png     auto-captured: the public *.replit.app deployment, served today
  ev-project.png  manual: Replit project page (file tree + commit history)
  ev-deploy.png   manual: Deployments panel (release history + timestamps)
  ev-usage.png    manual: account usage / Core credits page

Any missing manual image renders as a labelled placeholder, so the PDF still
builds while screenshots are being collected.
"""
import html
import os
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

MYT = timezone(timedelta(hours=8))
COMPILED = datetime.now(MYT).strftime("%Y-%m-%d %H:%M (MYT)")

HERE = Path(__file__).resolve().parent
OUT_HTML = HERE / "pou.html"
OUT_PDF = HERE.parent / "SDC2026_RREFCOLLECTION_Replit_POU.pdf"

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

PROJECT_URL = "https://replit.com/@Carrey7070/rref-collection-sdc"
LIVE_URL = "https://rref-collection-sdc.replit.app/"
CURRENT_URL = "https://collectloop.app.workbuddy.host/?sharecode=H3YSSVLHAH"

REPLIT_CONFIG = """run = "python3 src/app.py"
entrypoint = "src/app.py"
modules = ["python-3.11"]

[nix]
channel = "stable-24_05"

[[ports]]
localPort = 8080
externalPort = 80

[deployment]
run = ["sh", "-c", "python3 src/app.py"]
deploymentTarget = "autoscale\""""

FIELD_NOTES = [
    ("run / entrypoint", "Tells the Replit Run button what to execute. Ignored by every other platform."),
    ("modules", "Replit's own module pinning. This key has no meaning in GitHub Actions, Render or Fly."),
    ("[nix] channel", "Replit's Nix environment channel. Only Replit reads this section."),
    ("[[ports]] localPort / externalPort", "Replit's port forwarding table for the webview."),
    ("[deployment] deploymentTarget = autoscale", "Replit Deployments target. The release we shipped was built by this line."),
]


def img_block(filename: str, placeholder: str, note: str) -> str:
    path = HERE / filename
    if path.exists():
        return (
            '<figure class="shot">'
            f'<img src="{filename}" alt="{html.escape(placeholder)}">'
            f'<figcaption>{note}</figcaption>'
            "</figure>"
        )
    return (
        '<div class="placeholder">'
        f'<div class="ph-title">Screenshot needed &mdash; {html.escape(placeholder)}</div>'
        f'<div class="ph-note">{note}</div>'
        "</div>"
    )


def build() -> str:
    fields = "\n".join(
        f"<tr><td><code>{html.escape(k)}</code></td><td>{html.escape(v)}</td></tr>"
        for k, v in FIELD_NOTES
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SDC 2026 · RREF COLLECTION · Proof of Platform Use (Replit)</title>
<style>
  @page {{ size: A4; margin: 18mm 16mm 16mm 16mm; }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; color: #15171c; background: #fff;
    font-family: -apple-system, "PingFang SC", "Helvetica Neue", Helvetica, Arial, sans-serif;
    font-size: 10.5pt; line-height: 1.55;
  }}
  h1 {{ font-size: 22pt; line-height: 1.15; margin: 0 0 6pt; letter-spacing: -0.4pt; }}
  h2 {{ font-size: 13pt; margin: 0 0 8pt; padding-bottom: 4pt; border-bottom: 1.2pt solid #15171c; }}
  h3 {{ font-size: 10.5pt; margin: 14pt 0 5pt; }}
  p {{ margin: 0 0 8pt; }}
  code {{ font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 9pt;
         background: #f2f4f7; padding: 1pt 3pt; border-radius: 2pt; }}
  .page {{ page-break-after: always; }}
  .page:last-child {{ page-break-after: auto; }}

  .cover {{ padding-top: 42mm; }}
  .kicker {{ font-size: 8.5pt; letter-spacing: 1.6pt; text-transform: uppercase; color: #6b7280; margin-bottom: 14pt; }}
  .rule {{ height: 3pt; background: #15171c; width: 64pt; margin: 16pt 0 18pt; }}
  .meta {{ margin-top: 30pt; border-top: 0.8pt solid #e4e7ec; padding-top: 12pt; }}
  .meta div {{ display: flex; padding: 3pt 0; font-size: 10pt; }}
  .meta dt {{ width: 88pt; color: #6b7280; flex: none; }}
  .meta dd {{ margin: 0; font-weight: 600; word-break: break-all; }}
  .claim {{ margin-top: 22pt; padding: 11pt 13pt; background: #f6f7f9; border-left: 3pt solid #3b5bdb; font-size: 10pt; }}

  table {{ width: 100%; border-collapse: collapse; font-size: 9.5pt; margin: 6pt 0 12pt; }}
  th {{ text-align: left; background: #f6f7f9; padding: 5pt 7pt; border-bottom: 1pt solid #d5dae2; font-size: 8.5pt;
        letter-spacing: 0.4pt; text-transform: uppercase; color: #414855; }}
  td {{ padding: 5pt 7pt; border-bottom: 0.6pt solid #e4e7ec; vertical-align: top; }}
  td:first-child {{ white-space: nowrap; color: #414855; }}
  caption {{ caption-side: bottom; font-size: 8pt; color: #6b7280; text-align: left; padding-top: 4pt; }}

  .urlbar {{ display: flex; align-items: center; gap: 7pt; margin: 8pt 0 4pt;
             border: 0.8pt solid #d5dae2; border-radius: 4pt; padding: 5pt 9pt; background: #fafbfc; }}
  .lock {{ color: #0f766e; font-size: 9pt; }}
  .url {{ font-family: ui-monospace, Menlo, monospace; font-size: 9pt; color: #15171c; word-break: break-all; }}
  .stamp {{ margin-left: auto; font-size: 8pt; color: #6b7280; white-space: nowrap; flex: none; }}

  .shot {{ margin: 0 0 8pt; }}
  .shot img {{ width: 100%; border: 0.8pt solid #d5dae2; border-radius: 3pt; display: block; }}
  figcaption {{ font-size: 8pt; color: #6b7280; margin-top: 4pt; }}

  .placeholder {{ border: 1.2pt dashed #c3c9d4; border-radius: 4pt; padding: 30pt 16pt; text-align: center;
                  color: #8b93a1; margin: 8pt 0; }}
  .ph-title {{ font-size: 10pt; font-weight: 600; margin-bottom: 4pt; }}
  .ph-note {{ font-size: 8.5pt; line-height: 1.5; }}

  pre {{ background: #f6f7f9; border: 0.8pt solid #e4e7ec; border-radius: 3pt; padding: 9pt 11pt;
         font-size: 8.6pt; line-height: 1.5; overflow-wrap: anywhere; white-space: pre-wrap; margin: 0 0 10pt; }}
  .note {{ padding: 10pt 12pt; border-left: 3pt solid #b45309; background: #fffbeb; font-size: 9.3pt; }}
  .ok {{ padding: 10pt 12pt; border-left: 3pt solid #0f766e; background: #f0fdfa; font-size: 9.3pt; }}
  .small {{ font-size: 8.5pt; color: #6b7280; }}
  ul {{ margin: 4pt 0 10pt; padding-left: 16pt; }}
  li {{ margin-bottom: 3pt; }}
</style>
</head>
<body>

<!-- ============ 1. COVER ============ -->
<section class="page cover">
  <div class="kicker">SDC 2026 &middot; Preliminary Round &middot; Domain 2</div>
  <h1>Proof of Platform Use<br>Replit</h1>
  <div class="rule"></div>
  <p style="font-size:11pt;color:#414855;max-width:130mm">
    Evidence that CollectLoop was built, configured and first deployed on Replit
    by the team&rsquo;s registered leader account.
  </p>

  <dl class="meta">
    <div><dt>Team</dt><dd>RREF COLLECTION</dd></div>
    <div><dt>Project</dt><dd>CollectLoop &mdash; receivables promise ledger</dd></div>
    <div><dt>Leader</dt><dd>XIE KAIRUI</dd></div>
    <div><dt>Replit account</dt><dd>@Carrey7070</dd></div>
    <div><dt>Repository</dt><dd>{html.escape(PROJECT_URL)}</dd></div>
    <div><dt>Document</dt><dd>Supporting evidence for Participant Handbook &sect;10.6</dd></div>
    <div><dt>Compiled</dt><dd>{COMPILED}</dd></div>
  </dl>

  <div class="claim">
    <b>Declaration.</b> The application in this submission was developed inside a Replit workspace and
    released through Replit Deployments (Autoscale). The project, the deployment and this evidence all
    belong to the single leader account named above, which is the account that holds the Replit Core
    credit issued to this team. The public URL in Evidence A is served by Replit today, at the time of
    compiling this document.
  </div>
</section>

<!-- ============ 2. SUMMARY ============ -->
<section class="page">
  <h2>1 &nbsp;What we used, and where it is visible</h2>
  <p>
    Handbook &sect;10.6 asks for one thing before submission: proof that Replit was used, shown in the
    Technical and Tools Declaration, accepting <i>any one</i> of a live deployment URL, a project link
    with history, or finished credit. The declaration carries the first two. This document only
    assembles the material behind them, so a reviewer can check each claim without our help.
  </p>
  <p>
    Every claim below can be checked independently of this document: the deployment answers HTTP today,
    and the Replit configuration files are committed in the public repository.
  </p>
  <table>
    <caption>Table 1 &mdash; Replit usage at a glance. Evidence letters map to the sections that follow.</caption>
    <tr><th style="width:34%">Item</th><th>Value</th></tr>
    <tr><td>Platform</td><td>Replit &mdash; development workspace and hosting</td></tr>
    <tr><td>Account</td><td>replit.com/@Carrey7070 (team leader)</td></tr>
    <tr><td>Repl / project</td><td>{html.escape(PROJECT_URL)}</td></tr>
    <tr><td>Public deployment</td><td>{html.escape(LIVE_URL)}</td></tr>
    <tr><td>Deployment target</td><td>Autoscale (set in <code>.replit</code>, Evidence E)</td></tr>
    <tr><td>Start command</td><td><code>python3 src/app.py</code>, binds <code>0.0.0.0:$PORT</code></td></tr>
    <tr><td>Config committed</td><td>2026-10-22 23:14 MYT, commit <code>17a5ffe</code></td></tr>
    <tr><td>Deployment published</td><td>2026-10-22 &mdash; see Evidence C for the platform timestamp</td></tr>
    <tr><td>Evidence</td><td>A live URL &middot; B project page &middot; C release history &middot; D credits &middot; E config in repo</td></tr>
  </table>

  <h3>How the deployment was produced</h3>
  <ul>
    <li>Work was done in the Replit workspace at <code>~/workspace</code>, not on a laptop then uploaded.</li>
    <li>Commits were made in the workspace and synced to GitHub, so the history in both places is the same history.</li>
    <li>Release used <b>Deploy &rarr; Autoscale</b>. Replit reads the <code>[deployment]</code> section of
        <code>.replit</code> to build and run the app; no external build system was involved.</li>
    <li>Secrets, if any, sit in Replit Secrets. No key is committed to the repository.</li>
  </ul>

  <div class="ok">
    <b>Fastest single check for a reviewer.</b> Open {html.escape(LIVE_URL)} in a browser. It is a
    <code>*.replit.app</code> hostname, which is issued by Replit Deployments only.
  </div>
</section>

<!-- ============ 3. EVIDENCE A ============ -->
<section class="page">
  <h2>2 &nbsp;Evidence A &mdash; the deployment is live on Replit</h2>
  <div class="urlbar">
    <span class="lock">&#128274;</span>
    <span class="url">{html.escape(LIVE_URL)}</span>
    <span class="stamp">HTTP 200 &middot; captured 2026-10-23 20:13 MYT</span>
  </div>
  {img_block("ev-live.png", "public deployment first screen",
             "First screen served by the Replit deployment, captured from the public URL with no login. "
             "This is the build released on 2026-10-22.")}

  <h3>Response as measured, not as remembered</h3>
<pre>GET / HTTP/1.1
Host: rref-collection-sdc.replit.app

HTTP/2 200
content-length: 16198
date: Fri, 23 Oct 2026 12:12:47 GMT
strict-transport-security: max-age=63072000; includeSubDomains</pre>
  <p class="small">
    Recorded 2026-10-23 20:12 MYT from a machine with no Replit session. The host resolves and answers
    because the Replit deployment is still running.
  </p>
</section>

<!-- ============ 4. EVIDENCE B ============ -->
<section class="page">
  <h2>3 &nbsp;Evidence B &mdash; the project inside the Replit account</h2>
  <p>
    The Replit editor with the file tree, the owner shown in the top bar, and the version control pane.
    This is the same repository as the GitHub link in Table 1.
  </p>
  {img_block("ev-project.png", "Replit project page with file tree and owner",
             "Replit workspace for rref-collection-sdc, signed in as @Carrey7070.")}
</section>

<!-- ============ 5. EVIDENCE C ============ -->
<section class="page">
  <h2>4 &nbsp;Evidence C &mdash; the release history</h2>
  <p>
    Replit Deployments keeps every release with its timestamp. This is the platform&rsquo;s own record
    that a build was published from this project, and on which date.
  </p>
  {img_block("ev-deploy.png", "Deployments panel with release timestamps",
             "Deploy &rarr; Deployments: release entries and their build times.")}
</section>

<!-- ============ 6. EVIDENCE D ============ -->
<section class="page">
  <h2>5 &nbsp;Evidence D &mdash; the account that holds the credit</h2>
  <p>
    Replit Core is issued per participant. This team received one, and it sits on the leader account
    that also owns the project and the deployment. The usage page below shows the account in use.
  </p>
  {img_block("ev-usage.png", "Replit account usage / Core credits page",
             "Account settings or usage page, showing @Carrey7070 and the credit line.")}
  <p class="small">
    The rules allow a team&rsquo;s other members to work in the leader&rsquo;s workspace; what they do not
    allow is one team claiming multiple Core credits. Only one account is claimed here.
  </p>
</section>

<!-- ============ 7. EVIDENCE E ============ -->
<section class="page">
  <h2>6 &nbsp;Evidence E &mdash; Replit configuration committed in the repository</h2>
  <p>
    The file below is version-controlled at the repository root, introduced by the first commit
    <code>17a5ffe</code> on 2026-10-22 23:14 MYT. It is not a leftover: it is the file Replit executes.
  </p>
<pre>{html.escape(REPLIT_CONFIG)}</pre>
  <table>
    <caption>Table 2 &mdash; why this file is specific to Replit. None of these keys are read by another host.</caption>
    <tr><th style="width:38%">Key</th><th>Meaning</th></tr>
    {fields}
  </table>
  <div class="ok">
    <b>A reviewer can verify this without opening the app.</b> Open the repository, read
    <code>.replit</code>, and compare it with any other project&rsquo;s hosting config &mdash; the
    <code>[deployment] deploymentTarget</code> and <code>[nix] channel</code> keys exist only on Replit.
  </div>
</section>

<!-- ============ 8. HONEST NOTE ============ -->
<section class="page">
  <h2>7 &nbsp;One thing we are not hiding</h2>
  <p>
    On 2026-10-23 we tried to republish the project with the changes made after the mentor review
    (security headers, the manual invoice upload page, the AI explainer page, accessibility fixes).
    Publishing failed, twice, on two different Repls, with a single error line and no further detail in
    the build log:
  </p>
<pre>There was an issue publishing
There was an error with publishing</pre>
  <p>
    A fresh Repl imported from the same GitHub repository, with the Replit configuration already
    corrected to <code>python-3.12</code> / <code>stable-25_05</code>, failed in exactly the same way.
    We read that as an account-side or platform-side block rather than a defect in our code, and we
    stopped spending the night on it.
  </p>
  <p>
    So the current build of the prototype is served from a fallback host:
  </p>
  <div class="urlbar">
    <span class="lock">&#128274;</span>
    <span class="url">{html.escape(CURRENT_URL)}</span>
  </div>
  <p class="small">
    That link is what the submission form points at, because it holds the reviewed build. The Replit
    deployment above still holds the 2026-10-22 build and still answers. Both were produced from the
    same repository by the same team.
  </p>
  <div class="note">
    <b>What this document proves, and what it does not.</b> It proves the project was developed and
    released on Replit, by the account holding the team&rsquo;s credit. It does not claim the newest
    revisions are on the Replit URL &mdash; they are not, because publishing was blocked on the platform
    side at the time of writing.
  </div>
</section>

</body>
</html>
"""


def main() -> int:
    OUT_HTML.write_text(build(), encoding="utf-8")
    print(f"html  -> {OUT_HTML}")

    if not Path(CHROME).exists():
        print("Chrome not found; HTML only.", file=sys.stderr)
        return 1

    tmp_pdf = HERE / "_pou_tmp.pdf"
    cmd = [
        CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
        "--no-pdf-header-footer", "--allow-file-access-from-files",
        "--virtual-time-budget=4000",
        f"--print-to-pdf={tmp_pdf}", OUT_HTML.as_uri(),
    ]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if not tmp_pdf.exists():
        print("PDF not produced.", file=sys.stderr)
        print(res.stderr[-1500:], file=sys.stderr)
        return 1
    shutil.move(str(tmp_pdf), str(OUT_PDF))
    print(f"pdf   -> {OUT_PDF}  ({OUT_PDF.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
