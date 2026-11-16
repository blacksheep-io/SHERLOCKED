# Entry, local access and appearance

Implementation and QA notes · 13 November 2026

SHERLOCKED opens with a clean branded CASE FILE NOIR landing page and static capability overview before the authenticated seven-module research workspace. The running project remains `C:\Users\NOYON\Documents\ChatGPT\SHERLOCKED`. Start it with the existing `START_SHERLOCKED.bat`; this feature does not require another project folder or a paid API key.

## Welcome and entry

The landing page presents the original detective artwork, a static overview of the laboratory's capabilities, sign-in actions and the light/dark appearance control. It does not expose report selectors, computed retrieval results or a report handoff into the lab.

**Enter the research lab** or **Investigator access** opens local sign-in. The login screen's **Overview** control returns to the landing page. After successful sign-in the existing Dashboard, Report Explorer, Analysis, Relationships, Research, Settings and separate Ashford Manor workflows remain available.

Source previews and actual retrieval remain inside the authenticated application. Report Explorer can still pass an inspected source to AI Analysis Workspace; the workspace retains its original Source preview or upload controls. Removing the public landing preview does not remove these research functions.

The public fictional-demonstration credentials are:

| Field | Value |
|---|---|
| Username | `demo` |
| Password | `sherlocked-demo` |

The login screen also lists them under **Local demonstration access**. Account initialization creates the demo account only when absent; it preserves an existing changed password. If a local password has been changed, the published default is no longer that account's password. No automatic reset is performed.

## What the local access gate does

`sherlocked/auth.py` stores accounts separately from report storage, at `<configured dataset directory>/local_access.sqlite3` (default `data/local_access.sqlite3`). It refuses to use the configured report-database path as the access store. Canonical reports, qrels and experiment artifacts are not account records.

New password hashes use PBKDF2-HMAC-SHA256 with 600,000 iterations and a random 32-byte salt. The encoded value records the algorithm, iteration count, salt and derived hash. Password verification uses a constant-time digest comparison. The public demo password appears in demonstration instructions/source intentionally; the access database stores its derived hash rather than plaintext.

Five failed attempts for the same normalized username within one minute trigger a one-minute lock. The basic failure throttle is stored locally and survives an application restart. Sign-in failures use a generic message; an unavailable access store denies access rather than bypassing the gate.

Successful access is held in the current Streamlit session. There is no remember-me token or durable browser login. A browser reload or a new session may require sign-in again. **Sign out** clears the session's access and analysis state, returns to the landing page and retains the appearance choice. It does not delete reports, saved experiments or exported files. Model/index caches are not credentials.

This is a local fictional-demo gate, not enterprise authentication or per-report authorization. No enterprise SSO, MFA, account-administration/password-reset UI, tenant isolation or persisted analyst-review workflow is added. Those remain future scope; this update does not establish public-deployment suitability or certification on another computer.

## Light and dark CASE FILE NOIR

The labelled appearance button is available on welcome, sign-in and authenticated workspace screens. It offers **Dark mode** while light is active, and **Light mode** while dark is active. The choice is session-scoped and is also written into the URL as `theme=light` or `theme=dark`, allowing a newly opened/reloaded URL to restore that appearance. Theme selection carries no login credential.

Examples for the default local port:

- [Open light appearance](http://127.0.0.1:8501/?theme=light)
- [Open dark appearance](http://127.0.0.1:8501/?theme=dark)

Both appearances retain the Noir ink/paper/oxblood/brass identity and the original detective SVG. Light uses warm paper with ink text; dark uses ink surfaces with ivory text and a readable rose accent. The navigation rail and relationship graph remain intentionally ink in both modes. Native dataframe and pale heatmap inserts remain paper-like document plates with ink text; their light cells are intentional rather than a claim that every pixel becomes dark. The original manor illustration likewise remains an archival paper plate.

`design.py` keeps physical brand colors separate from per-session appearance roles. Its chart helper adapts visible traces, labels and axes without changing values, coordinates, source spans or evidence metadata. Heatmap text remains ink on the pale measurement cells. The toggle must not recompute or reinterpret an already saved research result as a different method.

## Editing map

| File | Responsibility |
|---|---|
| `sherlocked/ui_entry.py` | Branded landing, static capability overview, login presentation and sign-out routing |
| `sherlocked/auth.py` | Separate local credential store, password derivation and failure throttle |
| `sherlocked/design.py` | Session/URL appearance selection, appearance control and chart adaptation |
| `assets/interface/sherlocked.css` | Entry layout, semantic surfaces, native-widget overrides and responsive rules |
| `sherlocked/ui.py` | Entry gate before authenticated workspace initialization and existing module shell |

Keep source strings escaped before HTML rendering. Keep appearance selection per session rather than mutating a global user identity. Preserve native control labels, keyboard focus, password masking and authenticated research source-selection continuity. Streamlit/BaseWeb selectors and native dataframe surfaces still require browser review when dependencies change. System fonts and bundled SVGs avoid remote font/image requirements; local font availability can still affect wrapping and Bangla rendering.

## Measurable acceptance checks

The checklist defines acceptance conditions. Executed checks and the current clean paper-landing capture are recorded separately in [NO_PREVIEW_CHANGE.md](NO_PREVIEW_CHANGE.md) and [entry verification](ENTRY_VERIFICATION.md). Earlier screenshots with a working landing preview remain historical and do not verify this revision.

| Check | Observable acceptance condition |
|---|---|
| Fresh entry | Opening a fresh session displays the welcome screen before authenticated workspace controls. |
| Clean landing | The welcome page shows branding, static capabilities, sign-in and appearance controls; no working preview, report selectors, computed leads or report-handoff action are present. |
| Entry controls | Enter the research lab and Investigator access open sign-in; Overview returns to the clean landing page. |
| Authenticated source preview | After sign-in, select English, Bangla and mixed reports in the research workspace; source preview/upload and actual retrieval remain functional. Report Explorer still carries its selected report into analysis. |
| Invalid sign-in | Incorrect credentials do not open the workspace and display a generic failure message. |
| Valid sign-in | The unchanged local demo credentials open the workspace; an existing changed hash is preserved rather than reset. |
| Failure throttle | In an isolated test access store, five failures within a minute deny subsequent attempts until the lock expires; the main demonstration account should not be deliberately locked during ordinary browsing. |
| Appearance continuity | Toggle on welcome, continue to login, enter the lab and visit all seven modules; the selected appearance remains consistent. |
| Reload continuity | The URL records the appearance; opening/reloading it restores that choice, while authentication may need to be repeated. |
| Intentional surfaces | Original source text, password fields, dropdowns, tooltips, chart labels and focus indicators remain readable; paper inserts and ink graph retain their intended contrast. |
| Sign-out | Sign out returns to welcome; reopening sign-in does not expose previous analysis/session credentials; the chosen appearance is retained. |
| Data preservation | Credentials live only in the separate access store; canonical reports, original report database, experiment history and authored Ashford corpus remain intact. |

The existing synthetic-data, heuristic-extraction, unreviewed-relationship and real-world-generalization limitations still apply. See [the design guide](CASE_FILE_NOIR.md) for the broader presentation architecture and [the user guide](../USER_GUIDE.md) for laboratory workflows.
