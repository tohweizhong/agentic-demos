# Spec: Step mode in the Playground (3LO)

## Overview

Step mode shows the live 3LO flow one step at a time, in the Playground chat.
The backend runs at full speed. The browser stores the events in a queue.
The display shows one step for each click on "Next step".

## Functional requirements

- F1 A "Step mode" switch in the chat header. Default: off. The browser
  remembers the choice (localStorage).
- F2 With Step mode on, each of the 12 3LO steps appears as a step card in the
  chat, between the messages. Only the newest card has a "Next step" button.
- F3 A short card shows the step number ("Step 4 of 12"), a title, and one
  sentence. A "Details" link opens: who acts, what happens, what data moves,
  what stays hidden, and real values from this run (local time, session ID,
  masked nonce). Secrets and tokens are never shown.
- F4 The client stores all agent events in a queue. The answer text stays hidden
  until step 12.
- F5 Step 5 opens the GitHub window on the "Next step" click.
- F6 After the consent, the client resumes the agent at once, in the background.
  The cards for steps 7 to 12 still wait for clicks.
- F7 When Auth Manager already has the token, all 12 cards appear. Steps 4 to 10
  show "Skipped: token already stored".
- F8 Server steps (3, 7, 8) appear as cards with "Runs on the server" in Details.
- F9 The step chip and the "How 3LO works" tab follow the current card.
- F10 Keyboard: the right arrow key or Enter clicks "Next step".
- F11 If the consent request expires during a pause, the card says so and asks
  the user to send the prompt again.
- F12 "New conversation" clears the queue and all step cards.

## Non-functional requirements

- N1 Simplified Technical English for all text. ARIA roles and labels. Respect
  "reduce motion".
- N2 No change to the backend or the agent.
- N3 No secrets or real IDs in the repository.

## Acceptance criteria

- A1 With Step mode off, the Playground behaves the same as the client release
  before this track. The existing browser tests pass.
- A2 With Step mode on and no stored token, a run shows 12 cards in order, the
  popup opens at step 5, and the answer appears only at step 12.
- A3 With Step mode on and a stored token, steps 4 to 10 show "Skipped".
- A4 Browser tests for A2 and A3 are added to the repository and pass.
- A5 A real browser test with GitHub and IAP passes on the deployed client.

## Out of scope

- Pausing the real backend calls.
- Step mode for the ingress or egress demos.
- A separate Playground tab.
