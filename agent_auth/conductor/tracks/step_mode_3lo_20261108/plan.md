# Plan: Step mode in the Playground (3LO)

## Phase 1: Test setup [checkpoint: 7cf6ac8]

- [x] Task: Add the browser test harness to the repository 7cf6ac8
  - [x] Add `client/tests/` with a fake agent server that emits the 3LO events
        (prompt, adk_request_credential, completion signal, answer).
  - [x] Add a headless Chrome runner (Playwright) and a README for the tests.
  - [x] Port the existing checks (resume once, no empty bubble, Markdown,
        New conversation, diagram height).
  - [x] Run them with Step mode off. All must pass (acceptance A1 baseline).
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Event queue and switch [checkpoint: d2b7b4a]

- [x] Task: Write failing tests for the switch and the queue 49d8bd7
  - [x] Switch is off by default, and its state persists after reload (F1).
  - [x] With Step mode on, events are queued and no answer text shows (F4).
- [x] Task: Implement the switch and the event queue d2b7b4a
  - [x] Add the "Step mode" switch to the chat header, with localStorage.
  - [x] Route agent events through a queue when Step mode is on.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Step cards [checkpoint: 7f9114c]

- [x] Task: Write failing tests for the cards ca35612
  - [x] 12 cards in order, only the newest has "Next step" (F2, A2).
  - [x] Short card and "Details" content, no secrets (F3).
  - [x] Popup opens on the step 5 click (F5). Resume runs in the background (F6).
  - [x] Stored token: steps 4 to 10 show "Skipped" (F7, A3).
  - [x] Keyboard: right arrow and Enter (F10). Expired consent message (F11).
  - [x] New conversation clears the queue and the cards (F12).
- [x] Task: Implement the step cards 7f9114c
  - [x] Card component with text from one step table (STE wording).
  - [x] Wire steps to the queue, the popup, the resume, and the skip path.
  - [x] Sync the step chip and the "How 3LO works" tab (F9).
  - [x] Accessibility: roles, labels, focus on the new card, reduce motion (N1).
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4: Deploy and real test [checkpoint: e25f21e]

- [x] Task: Deploy and verify e25f21e
  - [x] Coverage of more than 60 percent for the `script.js` changes (93.6 percent of changed code lines).
  - [x] Redeploy with `04_deploy_client.sh`. Check IAP, no allUsers, healthy logs. (revision agent-auth-client-00008-wj4)
  - [x] Update `client/README.md` (change list, Step mode section). dd0e229
  - [x] Secret scan and hygiene script. Commit and push on the track branch.
- [x] Task: Real browser test with GitHub and IAP, by the user (A5)
  - Passed for the consent path on 08 Nov 20:07 SGT (revision agent-auth-client-00008-wj4): 12 cards in order, then the Markdown answer after card 12.
  - The user did not report the stored-token path or Step mode off separately. The browser tests cover both paths.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)
