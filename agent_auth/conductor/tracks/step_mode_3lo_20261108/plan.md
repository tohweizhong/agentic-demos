# Plan: Step mode in the Playground (3LO)

## Phase 1: Test setup

- [ ] Task: Add the browser test harness to the repository
  - [ ] Add `client/tests/` with a fake agent server that emits the 3LO events
        (prompt, adk_request_credential, completion signal, answer).
  - [ ] Add a headless Chrome runner (Playwright) and a README for the tests.
  - [ ] Port the existing checks (resume once, no empty bubble, Markdown,
        New conversation, diagram height).
  - [ ] Run them with Step mode off. All must pass (acceptance A1 baseline).
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Event queue and switch

- [ ] Task: Write failing tests for the switch and the queue
  - [ ] Switch is off by default, and its state persists after reload (F1).
  - [ ] With Step mode on, events are queued and no answer text shows (F4).
- [ ] Task: Implement the switch and the event queue
  - [ ] Add the "Step mode" switch to the chat header, with localStorage.
  - [ ] Route agent events through a queue when Step mode is on.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Step cards

- [ ] Task: Write failing tests for the cards
  - [ ] 12 cards in order, only the newest has "Next step" (F2, A2).
  - [ ] Short card and "Details" content, no secrets (F3).
  - [ ] Popup opens on the step 5 click (F5). Resume runs in the background (F6).
  - [ ] Stored token: steps 4 to 10 show "Skipped" (F7, A3).
  - [ ] Keyboard: right arrow and Enter (F10). Expired consent message (F11).
  - [ ] New conversation clears the queue and the cards (F12).
- [ ] Task: Implement the step cards
  - [ ] Card component with text from one step table (STE wording).
  - [ ] Wire steps to the queue, the popup, the resume, and the skip path.
  - [ ] Sync the step chip and the "How 3LO works" tab (F9).
  - [ ] Accessibility: roles, labels, focus on the new card, reduce motion (N1).
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4: Deploy and real test

- [ ] Task: Deploy and verify
  - [ ] Coverage of more than 60 percent for the `script.js` changes.
  - [ ] Redeploy with `04_deploy_client.sh`. Check IAP, no allUsers, healthy logs.
  - [ ] Update `client/README.md` (change list, Step mode section).
  - [ ] Secret scan and hygiene script. Commit and push on the track branch.
- [ ] Task: Real browser test with GitHub and IAP, by the user (A5)
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
