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

## Acceptance criteria

- All existing browser tests pass.
- New browser tests: folded cards, presentation mode, the split view at
  1280x800, the strip at 1024x700, and the marked arrow follows each card.
- A real browser test by the user on the deployed client.

## Out of scope

- Larger text option.
- Lazy loading for faster cold starts.
