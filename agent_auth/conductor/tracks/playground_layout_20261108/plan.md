# Plan: Playground layout for Step mode (3LO)

## Phase 1: Header and presentation mode

- [x] Task: Write failing tests for the header and presentation mode c0c3fc9
  - [x] The tabs are under the title (L3).
  - [x] "Step mode" is a switch control next to "New conversation", and it
        keeps its role, label, and saved state (L3).
  - [x] The presentation mode button folds the configuration panel to a thin
        bar and unfolds it. The state persists after reload (L2).
  - [x] With Step mode off, the chat area is unchanged (L6).
- [x] Task: Implement the header and presentation mode 4878e5d
  - [x] Move the tabs under the title. Style the Step mode switch as a real
        switch (track and thumb), with keyboard focus and "reduce motion".
  - [x] Add the presentation mode button with `aria-expanded` and
        `aria-controls`, and store the state in localStorage.
  - [x] Run all browser tests. All must pass.
- [x] Task: Write failing tests for the "Auth Manager" tab (L7, added on 08 Nov 20:18 SGT) b184749
  - [x] The tab exists after "How 3LO works", has role=tab, and opens with
        the keyboard.
  - [x] The panel shows all sections, with headings and the two tables, and
        the footer.
  - [x] Opening the tab makes no network request.
- [~] Task: Implement the "Auth Manager" tab
  - [ ] Add the third tab and a static panel with the approved text.
  - [ ] Make the tab code work for three tabs (click and arrow keys).
  - [ ] Add an in-page link to Demo controls.
  - [ ] Run all browser tests. All must pass.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Folded cards

- [ ] Task: Write failing tests for folded cards
  - [ ] Only the current card is open. Each past card is one line
        "✓ Step N: <title>" (L1).
  - [ ] A click on a folded line opens that card again. The keyboard opens it
        too (Enter or Space).
  - [ ] "Next step", the keyboard shortcuts, the skip path, and New
        conversation still work with folded cards.
- [ ] Task: Implement folded cards
  - [ ] Fold the previous card when a new card shows. Use a button with
        `aria-expanded` for the folded line.
  - [ ] Keep the card text and Details in the page, so that reopen is
        instant.
  - [ ] Run all browser tests. All must pass.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Split view and compact diagram

- [ ] Task: Write failing tests for the split view and the strip
  - [ ] At 1280x800 with Step mode on: the chat is on the left, and the
        compact diagram is on the right (L4).
  - [ ] At 1024x700 with Step mode on: the compact diagram is a strip above
        the chat (L5).
  - [ ] The compact arrows show short labels such as "4 Consent request" (L4).
  - [ ] The marked arrow follows each card, in the compact diagram and in the
        "How 3LO works" tab (L4).
  - [ ] With Step mode off: no compact diagram (L6).
- [ ] Task: Implement the split view and the compact diagram
  - [ ] Draw the compact diagram with the same SVG builder as the tab, with
        short labels, and a text marker for the current arrow.
  - [ ] Add the split layout and the strip layout with CSS (a width
        breakpoint). Keep the chat input usable in both layouts.
  - [ ] Connect the compact diagram to the step cards.
  - [ ] Run all browser tests. All must pass.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4: Deploy and real test

- [ ] Task: Deploy and verify
  - [ ] Coverage of more than 60 percent for the `script.js` changes.
  - [ ] Update `client/README.md` (change list, layout notes).
  - [ ] Secret scan and hygiene script. Commit and push on the track branch.
  - [ ] Tell the parent agent before the deploy, and wait for the go-ahead.
  - [ ] Redeploy with `04_deploy_client.sh`. Check IAP, no allUsers, healthy
        logs.
- [ ] Task: Real browser test on the deployed client, by the user
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
