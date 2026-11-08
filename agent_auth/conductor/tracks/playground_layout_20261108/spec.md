# Spec: Playground layout for Step mode (3LO)

## Functional requirements

- L1 Folded cards: in Step mode, only the current card stays open. Each past
  card becomes one line: "✓ Step 3: The agent asks Auth Manager for a token".
  A click on the line opens the card again.
- L2 Presentation mode: a button folds the left configuration panel to a thin
  bar, and unfolds it again. The browser remembers the choice.
- L3 Tidier header: the tabs move under the title. "Step mode" becomes a real
  switch, next to "New conversation".
- L4 Split view in Step mode: the chat with the cards on the left, and a
  compact 3LO diagram on the right. The current arrow is marked, as in the tab.
  The arrows show short labels, for example "4 Consent request". The full text
  stays in the step card.
- L5 If the screen is too narrow for the split view, the compact diagram moves
  above the chat as a strip.
- L6 With Step mode off, the Playground looks the same as today, except for the
  new header layout and presentation mode.
- L7 "Auth Manager" tab: a third tab after "How 3LO works". Information only:
  no API calls, and no buttons except an in-page link to Demo controls. Static
  HTML text in Simplified Technical English, with accessible headings and
  tables. (Added on 08 Nov 2026 at 20:18 SGT, approved by the user.)

- L8 Wider, resizable compact panel in the Step mode split view: the default
  width is 40 percent of the Playground area, minimum 380 px, maximum 560 px.
  A drag handle sits between the chat and the diagram. It works with the mouse
  and the keyboard: a focusable separator with role="separator",
  aria-orientation="vertical", and aria-valuenow. The left and right arrow keys
  change the width by 20 px. The browser remembers the width (localStorage).
  The compact diagram text scales with the panel width, so that the labels
  stay readable. The strip below 1100 px does not change. Step mode off does
  not change. (Added on 08 Nov 2026 at 20:57 SGT after the user test, approved
  by the user.)

- L9 One colour scheme, with CSS variables for the palette. (Added on 08 Nov
  2026 at 21:02 SGT, approved by the user.)
  - One main colour, Google blue, for all buttons (also "Save & Apply
    Settings" and "Load Remote Agents"), the tabs, the Step mode switch, the
    step chip, and the links.
  - Red only for warnings: the "Demo only" label and border, errors, and
    blocked decisions.
  - Green only for "allowed". The token is defined now, for the later gateway
    tabs.
  - Each state also has a text label, not colour only.
  - All text meets WCAG AA contrast: 4.5:1 for normal text, 3:1 for large text
    and UI parts.

## Acceptance criteria

- All existing browser tests pass.
- New browser tests: folded cards, presentation mode, the split view at
  1280x800, the strip at 1024x700, and the marked arrow follows each card.
- New browser test for L7: the tab exists, has role=tab, opens with the
  keyboard, shows the sections, and makes no network request when it opens.
- New browser tests for L8: the default width is in range at 1280x800, the
  drag and keyboard resize stay between the minimum and the maximum, the width
  persists after reload, and the strip does not change at 1024x700.
- New browser test for L9: an automated contrast check for the main buttons,
  the tabs, the step chip, the links, and the "Demo only" label, and no purple
  main buttons.
- A real browser test by the user on the deployed client.

## Out of scope

- Larger text option.
- Lazy loading for faster cold starts.
