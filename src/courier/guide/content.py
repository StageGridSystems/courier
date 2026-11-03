"""Step-by-step guide copy for the How-to tab."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GuideSection:
    title: str
    body_html: str


GUIDE_SECTIONS: list[GuideSection] = [
    GuideSection(
        title="1. Create a Google Cloud project",
        body_html="""
        <ol>
          <li>Open <b>Google Cloud Console</b> and sign in with the same Google account
              you will send from.</li>
          <li>Create a new project (or pick an existing one). Give it a clear name
              such as <i>Courier Mail</i>.</li>
          <li>Select that project in the top project picker.</li>
        </ol>
        """,
    ),
    GuideSection(
        title="2. Enable the Gmail API",
        body_html="""
        <ol>
          <li>Go to <b>APIs &amp; Services → Library</b>.</li>
          <li>Search for <b>Gmail API</b> and click <b>Enable</b>.</li>
        </ol>
        """,
    ),
    GuideSection(
        title="3. Configure the OAuth consent screen",
        body_html="""
        <ol>
          <li>Open <b>APIs &amp; Services → OAuth consent screen</b>.</li>
          <li>Choose <b>External</b> (unless you use Google Workspace and prefer Internal).</li>
          <li>Fill in app name (Courier), support email, and developer contact.</li>
          <li>Scopes: you can leave defaults here; Courier requests <code>gmail.send</code>
              and basic email profile at sign-in time.</li>
          <li>While the app is in <b>Testing</b> mode, add yourself under
              <b>Test users</b>. Only listed test users can sign in.</li>
        </ol>
        """,
    ),
    GuideSection(
        title="4. Create a Desktop OAuth client",
        body_html="""
        <ol>
          <li>Go to <b>APIs &amp; Services → Credentials → Create credentials →
              OAuth client ID</b>.</li>
          <li>Application type: <b>Desktop app</b>.</li>
          <li>Name it (for example <i>Courier Desktop</i>) and create.</li>
          <li>Download the JSON file. This is your client secret file for Courier.</li>
        </ol>
        <p><b>Do not</b> use a service account JSON. Service accounts need Workspace
        domain-wide delegation. Courier uses the installed-app OAuth flow with a
        Desktop client so mail is sent as <i>you</i>.</p>
        """,
    ),
    GuideSection(
        title="5. Connect Courier",
        body_html="""
        <ol>
          <li>Open the <b>Authentication</b> tab.</li>
          <li>Drag and drop the Desktop client JSON, or pick it with Browse,
              or enter client ID / secret manually.</li>
          <li>Click <b>Sign in with Google</b>. A browser window opens; approve access.</li>
          <li>Confirm the status card shows connected as your address.</li>
        </ol>
        """,
    ),
    GuideSection(
        title="6. Build an audience",
        body_html="""
        <ol>
          <li>Open <b>Audience</b>.</li>
          <li>Type addresses into the chip field (Enter, comma, semicolon, or space commits).</li>
          <li>Or paste a blob of text to extract emails, or import CSV / XLSX / XLS / TXT.
              Courier scans every cell and pulls valid addresses.</li>
          <li>Review the import preview (new, duplicates, invalid) before adding.</li>
          <li>Maintain a suppression / unsubscribe list; those addresses are always excluded.</li>
        </ol>
        """,
    ),
    GuideSection(
        title="7. Compose, test, and send",
        body_html="""
        <ol>
          <li>Open <b>Compose / Send</b>. Write a subject and HTML body.
              Use merge fields like <code>{{email}}</code>.</li>
          <li>Set a display name and optional reply-to. Attachments must stay under
              Gmail’s ~25 MB message limit.</li>
          <li>Add admin addresses under <b>Settings → Test audience</b>.</li>
          <li>Click <b>Send test to admins</b> first.</li>
          <li><b>Send to audience</b> opens a confirmation with count, subject, and
              estimated time. You can cancel, preview, send to test audience, or send to all.</li>
          <li>Watch progress, pause / resume / cancel, then export results CSV if needed.</li>
        </ol>
        """,
    ),
    GuideSection(
        title="Limits",
        body_html="""
        <ul>
          <li>Consumer Gmail: roughly <b>500 messages per day</b>.</li>
          <li>Google Workspace: roughly <b>2,000 messages per day</b> (plan-dependent).</li>
          <li>Courier defaults to 1 email every 2 seconds and a daily cap of 400
              (conservative). Raise carefully in Settings.</li>
          <li>Sudden large volume to cold lists triggers spam filters and account review.</li>
        </ul>
        """,
    ),
    GuideSection(
        title="Deliverability and anti-spam basics",
        body_html="""
        <ul>
          <li>Send only to people who expect mail from you. Never buy lists.</li>
          <li>Include a clear unsubscribe path (Courier’s default footer helps).</li>
          <li>Use a recognizable From name and a monitored Reply-To.</li>
          <li>Warm up: start small, then grow. Prefer Workspace for business mail.</li>
          <li>Avoid misleading subjects, URL shorteners in bulk, and huge image-only bodies.</li>
          <li>Honor suppressions immediately.</li>
        </ul>
        """,
    ),
    GuideSection(
        title="Troubleshooting",
        body_html="""
        <ul>
          <li><b>Access blocked / app not verified</b>: consent screen still in Testing;
              add your Google account as a test user.</li>
          <li><b>Service account JSON rejected</b>: use a Desktop OAuth client instead.</li>
          <li><b>invalid_client</b>: wrong client secret or type (need Desktop / installed).</li>
          <li><b>429 / rate limit</b>: Courier backs off and retries; lower send rate.</li>
          <li><b>Daily limit</b>: wait until tomorrow or use a Workspace account with higher quota.</li>
          <li><b>Token errors after sleep</b>: open Authentication and sign in again.</li>
          <li>Check the log file in your Courier data folder for crash details
              (no secrets are written there).</li>
        </ul>
        """,
    ),
]
