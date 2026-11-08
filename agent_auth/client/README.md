# Sample UI client for Agent Identity and Auth Manager

This folder holds a copy of the sample UI client from the open source
[adk-python](https://github.com/google/adk-python/tree/main/contributing/samples/integrations/gcp_auth/client)
repository. The original files keep their Apache 2.0 license header.

The client does three things:

1. It sends chat messages to a remote agent on Agent Runtime.
2. When the agent sends an `adk_request_credential` event, it opens the consent
   popup and stores the consent nonce in a cookie.
3. It hosts the `/validateUserId` callback. Auth Manager sends the browser to
   this URL after the user gives consent. The client then calls
   `credentials:finalize`, and Auth Manager stores the user token in its vault.

> [!NOTE]
> This client uses FastAPI. The repository rule says "no FastAPI for a
> production-shaped backend". This folder is an exception. It is a copy of the
> upstream sample, and it is a test harness only. It is not a production
> backend.

## Changes from the upstream sample

| File | Change |
|---|---|
| `main.py` | The `/chat` endpoint uses the `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and `AGENT_ID` environment values when the UI sends empty values. |
| `main.py` | The `__main__` block reads `HOST` and `PORT`. |
| `main.py` | Behind IAP, `/chat`, `/validateUserId`, and `/commit` take the user ID from the `X-Goog-Authenticated-User-Email` header. They ignore the user ID from the form and from cookies. Without the header, the upstream behaviour applies, and the server logs one warning. |
| `main.py` | New `/whoami` endpoint. It returns the IAP user email, or `iap: false` when there is no IAP header. |
| `static/script.js` | The page calls `/whoami`. Behind IAP, it shows the IAP email in the User ID field and disables the field. |
| `main.py` | New "Demo controls" endpoints: `GET /demo/config`, `POST /demo/reset-consent`, and `GET /demo/access-summaries`. They act only for the IAP user, and return 403 without the IAP header. |
| `static/index.html`, `static/script.js`, `static/style.css` | New collapsible "Demo controls" panel with a terminal-style output box and an access summary table. |
| `main.py`, `static/index.html`, `static/script.js` | Project ID and Location are dropdowns. New `GET /config` endpoint returns the options from `PROJECT_OPTIONS` and `LOCATION_OPTIONS` (comma-separated). The defaults are `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION`. |
| `static/script.js` | The access summary table shows times in the browser local time with the zone, and in UTC. The output box keeps the raw API JSON in UTC. The zone name comes from the browser language (for example `SGT` for en-SG, `GMT+8` for en-US). |
| `main.py`, `static/script.js` | Robust resume after consent. The `/validateUserId` success page sends a same-origin signal (BroadcastChannel, `window.opener.postMessage`, and a localStorage event), then closes itself. The main page resumes the agent exactly once, on the first signal or when the popup closes. Before this change, the page resumed only when the popup closed. If the user did not close the popup, the agent did not resume. |
| `static/index.html`, `static/script.js`, `static/style.css` | Loading states in the chat: typing dots before the first event, a spinner while the consent popup is open, and a spinner after consent until the first answer text. After 30 seconds, a note says that the first run can take up to 2 minutes. An error removes all spinners. |
| `static/index.html`, `static/script.js`, `static/style.css` | Two tabs in the main area: "Playground" and "How 3LO works". The second tab draws the 12-step 3LO flow as an inline SVG, highlights the current step of the Playground run, lists the steps as text, and shows a timings table of the last run (browser memory only). A chip in the header shows the current step as text. |
| `static/script.js` | Fix: the chat never shows an empty bubble. The typing dots stay until there is text. A tool call changes the status line ("The agent is calling a tool: NAME..."). A bubble that ends with no text is removed. |
| `static/script.js`, `static/vendor/` | Agent answers render as Markdown when the stream ends (plain text while it streams). The client uses vendored copies of marked and DOMPurify, not a CDN. Raw HTML from the model is escaped, and DOMPurify sanitizes the result. Images are not rendered. Links open in a new tab with `rel="noopener noreferrer"`. |
| `static/index.html`, `static/script.js` | New "New conversation" button. It clears the chat, the step chip, and the timings. The next message starts a new agent session. It does not remove the GitHub token that Auth Manager stores. To remove the token, use Demo controls, Reset Auth Manager consent. |
| `static/style.css` | Fix: the 3LO diagram showed as a thin strip, because the scrolling flex panel shrank it. The panel children now keep their size. |
| `static/index.html`, `static/script.js`, `static/style.css` | New "Step mode" switch and step cards. See [Step mode](#step-mode). |
| `tests/` | New browser tests (fake agent, headless Chrome) and backend unit tests. See [tests/README.md](tests/README.md). |
| `static/index.html`, `static/script.js`, `static/style.css` | Layout: tabs under the title, a real "Step mode" switch, presentation mode, an "Auth Manager" tab, folded step cards, and a split view with a compact 3LO diagram. See [Layout](#layout). |
| `Dockerfile` | New file. It runs the client on Cloud Run. |

## Step mode

Step mode shows the live 3LO flow one step at a time, in the Playground chat.
Turn it on with the "Step mode" switch in the chat header. It is off by
default. The browser remembers the choice.

- The backend runs at full speed. The page keeps the agent events in a queue.
- Each of the 12 3LO steps shows as a card in the chat. Only the newest card
  has a "Next step" button. The button waits until the data for the next step
  is ready, and shows the reason.
- Each card has a short sentence and a "Details" link: who acts, what happens,
  what data moves, what stays hidden, where it runs, and real values from the
  run (local time, session ID, masked nonce). The cards never show a token.
- The click that shows step 5 opens the GitHub window. After the consent, the
  client resumes the agent at once, in the background. The cards for steps 7
  to 12 still wait for clicks. The answer shows at step 12.
- When Auth Manager already has the token, steps 4 to 10 say "Skipped: token
  already stored".
- If the consent request is older than 10 minutes at the step 5 click, the
  card says that it expired. Send the prompt again.
- The right arrow key or Enter clicks "Next step". The step chip and the
  "How 3LO works" diagram follow the current card.
- "New conversation" removes the cards and clears the queue.

With Step mode off, the Playground works as before.

## Layout

- **Header:** the tabs are under the title. The "Step mode" switch and
  "New conversation" are on the right.
- **Presentation mode:** the button in the configuration panel header folds
  the panel to a thin bar, and unfolds it. The browser remembers the choice.
- **Tabs:** "Playground", "How 3LO works", and "Auth Manager". The
  "Auth Manager" tab is information only. It makes no API call.
- **Folded cards:** in Step mode, only the current card stays open. Each past
  card is one line, for example "✓ Step 3: The agent asks Auth Manager for a
  token". A click, Enter, or Space opens the card again.
- **Split view:** in Step mode, the chat is on the left, and a compact 3LO
  diagram with short labels is on the right. On a window narrower than
  1100 px, the compact view is a strip above the chat. The current step is
  marked in the compact view, the strip, and the "How 3LO works" tab.
- With Step mode off, the chat uses the full width.

## Vendored libraries

`static/vendor/` holds unchanged copies of marked 15.0.12 (MIT) and DOMPurify
3.2.6 (Apache 2.0 or MPL 2.0), with their license files. See
[static/vendor/README.md](static/vendor/README.md).

## Security

Behind IAP, the user ID is the email of the person that IAP verified. Each
person gets a separate token in Auth Manager. Without IAP, the client uses one
user ID from the form (`default_user_id` by default), and every person who can
open the client acts as that user. Do not give the client public access. The
sub-demos deploy it on Cloud Run behind Identity-Aware Proxy (IAP).

The client reads only the IAP email header. For more protection, a production
client must also verify the signed `X-Goog-IAP-JWT-Assertion` header.

## Run on your machine

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
export GOOGLE_CLOUD_PROJECT=YOUR_PROJECT_ID
export GOOGLE_CLOUD_LOCATION=us-central1
export AGENT_ID=YOUR_ENGINE_ID
.venv/bin/uvicorn main:app --port 8080
```

Open `http://localhost:8080`. Use `localhost`, not `127.0.0.1`. The agent
continue URI must match the client URL.

## Demo controls (demo only)

The settings sidebar has a collapsible "Demo controls" panel. A presenter
uses it to repeat the consent flow.

| Control | API call | Equivalent gcloud command |
|---|---|---|
| Reset Auth Manager consent | `POST .../authProviders/PROVIDER:revokeAuthorization` with body `{"userId": IAP_EMAIL}` | `gcloud alpha agent-identity auth-providers revoke-authorization PROVIDER --location=LOCATION --user-id=IAP_EMAIL` |
| Show access summary | `GET .../locations/LOCATION/accessSummaries` | `gcloud agent-identity access-summaries list --location=LOCATION` |

- The server makes the API calls with the client service account. No endpoint
  runs a shell or a subprocess.
- The reset acts only for the IAP user. The page cannot send another user ID.
- The output box shows the command, the HTTP status, and the raw API response.
- The panel also links to the GitHub OAuth app settings (`GITHUB_APP_URL`).
  The GitHub token revoke stays manual. GitHub's revoke API needs the user
  token, and only Auth Manager holds that token.

> [!WARNING]
> A production client must not expose these actions. The access summary shows
> the user IDs of all users of the project.
