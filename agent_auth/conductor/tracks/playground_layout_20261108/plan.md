# Plan: Playground layout for Step mode (3LO)

## Phase 1: Header and presentation mode [checkpoint: bc4bae8]

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
- [x] Task: Implement the "Auth Manager" tab bc4bae8
  - [x] Add the third tab and a static panel with the approved text.
  - [x] Make the tab code work for three tabs (click and arrow keys).
  - [x] Add an in-page link to Demo controls.
  - [x] Run all browser tests. All must pass.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 2: Folded cards [checkpoint: 0110492]

- [x] Task: Write failing tests for folded cards bf4c6d6
  - [x] Only the current card is open. Each past card is one line
        "✓ Step N: <title>" (L1).
  - [x] A click on a folded line opens that card again. The keyboard opens it
        too (Enter or Space).
  - [x] "Next step", the keyboard shortcuts, the skip path, and New
        conversation still work with folded cards.
- [x] Task: Implement folded cards 0110492
  - [x] Fold the previous card when a new card shows. Use a button with
        `aria-expanded` for the folded line.
  - [x] Keep the card text and Details in the page, so that reopen is
        instant.
  - [x] Run all browser tests. All must pass.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 3: Split view and compact diagram [checkpoint: dd0a51c]

- [x] Task: Write failing tests for the split view and the strip 2fef294
  - [x] At 1280x800 with Step mode on: the chat is on the left, and the
        compact diagram is on the right (L4).
  - [x] At 1024x700 with Step mode on: the compact diagram is a strip above
        the chat (L5).
  - [x] The compact arrows show short labels such as "4 Consent request" (L4).
  - [x] The marked arrow follows each card, in the compact diagram and in the
        "How 3LO works" tab (L4).
  - [x] With Step mode off: no compact diagram (L6).
- [x] Task: Implement the split view and the compact diagram dd0a51c
  - [x] Draw the compact diagram with the same SVG builder as the tab, with
        short labels, and a text marker for the current arrow.
  - [x] Add the split layout and the strip layout with CSS (a width
        breakpoint). Keep the chat input usable in both layouts.
  - [x] Connect the compact diagram to the step cards.
  - [x] Run all browser tests. All must pass.
- [x] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 4: Deploy and real test

- [x] Task: Deploy and verify eeb1508
  - [x] Coverage of more than 60 percent for the `script.js` changes (95.3 percent of changed code lines).
  - [x] Update `client/README.md` (change list, layout notes). eeb1508
  - [x] Secret scan and hygiene script. Commit and push on the track branch.
  - [x] Tell the parent agent before the deploy, and wait for the go-ahead.
  - [x] Redeploy with `04_deploy_client.sh`. Check IAP, no allUsers, healthy
        logs. (revision agent-auth-client-00009-5v9, upload 74 KB)
- [~] Task: Real browser test on the deployed client, by the user
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)

## Phase 5: Review Fixes

User feedback after the Phase 4 user test (08 Nov 20:56 SGT): "looks good".
Amendment L8 approved at 20:57 SGT.

- [x] Task: Write failing tests for the resizable compact panel (L8) 748fa9d
  - [x] The default width is 40 percent of the Playground area, between
        380 px and 560 px, at 1280x800.
  - [x] The separator has role="separator", aria-orientation="vertical", and
        aria-valuenow, and it can get the focus.
  - [x] A mouse drag and the arrow keys (20 px for each key) change the width,
        and the width stays between 380 px and 560 px.
  - [x] The width persists after reload.
  - [x] At 1024x700 the strip does not change, and the separator does not show.
- [x] Task: Implement the resizable compact panel (L8) 5528dab
  - [x] Add the separator, the drag and keyboard handlers, and the localStorage
        key.
  - [x] Set the width with a CSS variable, so that the strip layout below
        1100 px does not change.
  - [x] Run all browser tests. All must pass.
- [x] Task: Write failing tests for the colour scheme (L9, added on 08 Nov 21:02 SGT) fb330c5
  - [x] The main buttons, the tabs, the switch, the step chip, and the links
        use the main colour. No purple.
  - [x] Red only for the "Demo only" label and border, and for errors.
  - [x] Contrast check: 4.5:1 for normal text, 3:1 for UI parts.
- [x] Task: Implement the colour scheme (L9) 3382b6b
  - [x] Add the palette as CSS variables (main, main dark, warning, allowed,
        and text colours), and the Material web colour variables.
  - [x] Use the variables in the header, the cards, the tabs, the strip, and
        the Demo controls.
  - [x] Run all browser tests. All must pass.
- [~] Task: Deploy and verify the review fix
  - [x] Coverage, README change list, secret scan, commit and push.
  - [x] Tell the parent agent before the deploy, and wait for the go-ahead.
  - [ ] Redeploy with `04_deploy_client.sh`. Check IAP, no allUsers, healthy
        logs.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
