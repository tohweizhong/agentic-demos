"""Browser tests for the Playground layout (track playground_layout_20261108).

Phase 1: the header and presentation mode.
"""

PRESENT = "#presentation-toggle"


def test_tabs_are_under_the_title(new_page):
  """L3: the tabs show under the title."""
  page = new_page()
  title = page.locator(".chat-header h1").bounding_box()
  tabs = page.locator(".chat-header .tabs").bounding_box()
  assert tabs["y"] >= title["y"] + title["height"] - 1
  # The tabs stay on the left side, under the title.
  assert tabs["x"] < title["x"] + title["width"]


def test_step_switch_is_a_switch_next_to_new_conversation(new_page):
  """L3: Step mode is a real switch, next to New conversation."""
  page = new_page()
  same_group = page.evaluate(
      """() => document.querySelector('#step-mode-switch')
          .closest('.header-actions') ===
        document.querySelector('#new-conversation')
          .closest('.header-actions')""")
  assert same_group
  switch = page.locator("#step-mode-switch")
  assert switch.get_attribute("role") == "switch"
  assert page.locator(".step-switch .switch-track .switch-thumb").count() == 1
  # The switch still works and the browser remembers it.
  page.click(".step-switch")
  assert page.is_checked("#step-mode-switch")
  page.reload()
  page.wait_for_timeout(800)
  assert page.is_checked("#step-mode-switch")
  page.click(".step-switch")
  assert not page.is_checked("#step-mode-switch")


def test_presentation_mode_folds_the_panel(new_page):
  """L2: the button folds the panel to a thin bar, and the browser remembers."""
  page = new_page()
  button = page.locator(PRESENT)
  assert button.get_attribute("aria-expanded") == "true"
  assert button.get_attribute("aria-controls")
  wide = page.locator("#settings-sidebar").bounding_box()["width"]
  assert wide > 250
  button.click()
  page.wait_for_timeout(400)
  assert button.get_attribute("aria-expanded") == "false"
  assert page.locator("#settings-sidebar").bounding_box()["width"] < 60
  assert not page.locator(".settings-form").is_visible()
  page.reload()
  page.wait_for_timeout(800)
  assert page.locator(PRESENT).get_attribute("aria-expanded") == "false"
  assert page.locator("#settings-sidebar").bounding_box()["width"] < 60
  page.locator(PRESENT).click()
  page.wait_for_timeout(400)
  assert page.locator("#settings-sidebar").bounding_box()["width"] > 250
  assert page.locator(".settings-form").is_visible()


def test_step_mode_off_chat_area_unchanged(new_page):
  """L6: 3LO GitHub shows three columns below a full-width header at x=0."""
  page = new_page()
  assert not page.is_checked("#step-mode-switch")
  for tab_id in ("#tab-play", "#tab-egress", "#tab-ingress", "#tab-how", "#tab-auth-manager"):
    page.click(tab_id)
    assert page.locator(".chat-header").bounding_box()["x"] == 0
  page.click("#tab-play")
  sidebar = page.locator("#playground-panel > #settings-sidebar").bounding_box()
  chat_col = page.locator("#playground-panel > .chat-column").bounding_box()
  compact = page.locator("#playground-panel > #compact-flow").bounding_box()
  assert sidebar["x"] == 0
  assert chat_col["x"] >= sidebar["x"] + sidebar["width"] - 1
  assert compact["x"] >= chat_col["x"] + chat_col["width"] - 1
  assert page.locator("#user-input").is_visible()
  assert page.locator("#play-sample-prompts .play-sample-prompt").count() == 2


AM_SECTIONS = [
    "What Auth Manager is",
    "Auth providers",
    "Who may use a provider",
    "The vault",
    "The 3LO consent, in short",
    'What "Reset Auth Manager consent" deletes',
    "What the reset does not delete",
    "Revoke in two places",
    "Audit",
    "Console view",
]


def test_auth_manager_tab(new_page):
  """L7: the Auth Manager tab shows static text and makes no request."""
  page = new_page()
  tabs = page.locator(".tabs [role=tab]")
  assert tabs.count() == 5
  assert tabs.nth(4).inner_text() == "Auth Manager"
  assert tabs.nth(4).get_attribute("role") == "tab"
  # Open it with the keyboard: ArrowLeft from #tab-play wraps to #tab-auth-manager.
  page.focus("#tab-play")
  requests = []
  page.on("request", lambda r: requests.append(r.url))
  page.keyboard.press("ArrowLeft")
  page.wait_for_timeout(500)
  tab = page.locator("#tab-auth-manager")
  assert tab.get_attribute("aria-selected") == "true"
  panel = page.locator("#auth-manager-panel")
  assert panel.is_visible()
  assert panel.get_attribute("role") == "tabpanel"
  assert not page.locator("#playground-panel").is_visible()
  headings = panel.locator("h3").all_inner_texts()
  for section in AM_SECTIONS:
    assert section in headings
  assert panel.locator("table").count() == 2
  assert panel.locator("table th[scope=col]").count() == 4
  assert "Facts tested in a demo project in November 2026" in panel.inner_text()
  # Information only: no buttons, and one link to Demo controls.
  assert panel.locator("button, md-outlined-button, md-filled-button").count() == 0
  links = panel.locator("a").evaluate_all("els => els.map(a => a.getAttribute('href'))")
  assert links == ["#demo-controls"]
  assert requests == []


# ---- Phase 2: folded cards (L1) ----
CARD = "#messages-container .step-card"


def _step_on_and_send(page, text):
  if not page.is_checked("#step-mode-switch"):
    page.click(".step-switch")
  page.fill("#user-input", text)
  page.press("#user-input", "Enter")
  page.wait_for_selector(CARD, timeout=5000)


def _click_next(page):
  page.wait_for_function(
      """() => { const b = [...document.querySelectorAll(
          '#messages-container .step-card .step-next')].pop();
        return b && !b.disabled; }""", timeout=20000)
  count = page.locator(CARD).count()
  page.locator("#messages-container .step-card .step-next").last.click()
  page.wait_for_function(
      f"() => document.querySelectorAll('{CARD}').length > {count}",
      timeout=5000)


def test_past_cards_fold_to_one_line(new_page, stats):  # pylint: disable=unused-argument
  """L1: only the current card is open. Past cards are one line."""
  page = new_page()
  _step_on_and_send(page, "token")
  for _ in range(3):
    _click_next(page)
  cards = page.locator(CARD)
  assert cards.count() == 4
  expected = [
      "✓ Step 1: You send the prompt",
      "✓ Step 2: The client calls the agent",
      "✓ Step 3: The agent asks Auth Manager for a token",
  ]
  for i, line in enumerate(expected):
    fold = cards.nth(i).locator(".step-fold")
    assert fold.is_visible()
    assert fold.inner_text().strip() == line
    assert fold.get_attribute("aria-expanded") == "false"
    assert not cards.nth(i).locator(".step-body").is_visible()
  current = cards.nth(3)
  assert not current.locator(".step-fold").is_visible()
  assert current.locator(".step-body").is_visible()
  assert page.locator(f"{CARD} .step-body:visible").count() == 1


def test_folded_card_opens_again(new_page, stats):  # pylint: disable=unused-argument
  """L1: a click, Enter, or Space opens a folded card again."""
  page = new_page()
  _step_on_and_send(page, "token")
  for _ in range(3):
    _click_next(page)
  cards = page.locator(CARD)
  card2 = cards.nth(1)
  card2.locator(".step-fold").click()
  assert card2.locator(".step-fold").get_attribute("aria-expanded") == "true"
  assert card2.locator(".step-body").is_visible()
  assert "Step 2 of 12" in card2.inner_text()
  card2.locator(".step-fold").click()
  assert not card2.locator(".step-body").is_visible()
  # Keyboard: Enter opens, Space closes.
  card1 = cards.nth(0)
  card1.locator(".step-fold").focus()
  page.keyboard.press("Enter")
  assert card1.locator(".step-body").is_visible()
  page.keyboard.press("Space")
  assert not card1.locator(".step-body").is_visible()
  # Next step still works, and the old current card folds.
  _click_next(page)
  assert cards.count() == 5
  assert cards.nth(3).locator(".step-fold").is_visible()
  assert "✓ Step 4:" in cards.nth(3).locator(".step-fold").inner_text()


# ---- Phase 3: split view, strip, and compact diagram (L4, L5, L6) ----
COMPACT = "#compact-flow"


def _step_on(page):
  if not page.is_checked("#step-mode-switch"):
    page.click(".step-switch")
  page.wait_for_timeout(300)


def test_split_view_at_1280(new_page):
  """L4: chat on the left, compact diagram on the right, short labels."""
  page = new_page(1280, 800)
  _step_on(page)
  compact = page.locator(COMPACT)
  assert compact.is_visible()
  chat = page.locator("#messages-container").bounding_box()
  box = compact.bounding_box()
  assert box["x"] >= chat["x"] + chat["width"] - 1
  svg = page.locator(f"{COMPACT} svg.compact-svg")
  assert svg.is_visible()
  svg_box = svg.bounding_box()
  assert svg_box["y"] + svg_box["height"] <= box["y"] + box["height"] + 1
  assert svg.locator(".flow-step").count() == 12
  labels = svg.locator(".step-label").all_text_contents()
  assert "4 Consent request" in labels
  assert page.locator("#user-input").is_visible()


def test_strip_at_1024(new_page):
  """L5: on a narrow screen, the compact diagram is a strip above the chat."""
  page = new_page(1024, 700)
  _step_on(page)
  strip = page.locator(f"{COMPACT} .compact-strip")
  assert strip.is_visible()
  assert not page.locator(f"{COMPACT} svg.compact-svg").is_visible()
  chat = page.locator("#messages-container").bounding_box()
  box = strip.bounding_box()
  assert box["y"] + box["height"] <= chat["y"] + 1
  assert strip.locator("li").count() == 12
  assert "4 Consent request" in strip.locator("li").all_inner_texts()
  assert page.locator("#user-input").is_visible()


def test_marked_arrow_follows_each_card(new_page, stats):  # pylint: disable=unused-argument
  """L4: the marked arrow follows each card, in the compact view and the tab."""
  page = new_page(1280, 800)
  _step_on(page)
  page.fill("#user-input", "token")
  page.press("#user-input", "Enter")
  page.wait_for_selector(CARD, timeout=5000)
  for n in range(1, 13):
    if n > 1:
      _click_next(page)
    marked = page.locator(f"{COMPACT} .flow-step.active")
    assert marked.count() == 1
    assert marked.get_attribute("data-flow-step") == str(n)
    assert page.locator(f"#flow-step-{n}.active").count() == 1
    strip_marked = page.locator(f"{COMPACT} .compact-strip li.active")
    assert strip_marked.get_attribute("aria-current") == "step"
    assert strip_marked.get_attribute("data-flow-step") == str(n)


def test_no_compact_diagram_with_step_mode_off(new_page):
  """L6: the compact diagram and left controls stay visible in 3LO GitHub."""
  page = new_page(1280, 800)
  assert not page.is_checked("#step-mode-switch")
  assert page.locator(COMPACT).is_visible()
  assert page.locator("#playground-panel > #settings-sidebar").is_visible()
  _step_on(page)
  assert page.locator(COMPACT).is_visible()
  page.click(".step-switch")
  page.wait_for_timeout(300)
  assert page.locator(COMPACT).is_visible()


# ---- Phase 5 review fix: resizable compact panel (L8) ----
RESIZER = "#compact-resizer"
MIN_W, MAX_W = 380, 560


def _compact_width(page):
  return page.locator(COMPACT).bounding_box()["width"]


def test_compact_default_width(new_page):
  """L8: the default width is 40 percent of the Playground area, in range."""
  page = new_page(1280, 800)
  _step_on(page)
  panel = page.locator("#playground-panel").bounding_box()["width"]
  width = _compact_width(page)
  assert MIN_W - 1 <= width <= MAX_W + 1
  expected = min(MAX_W, max(MIN_W, 0.4 * panel))
  assert abs(width - expected) < 3
  sep = page.locator(RESIZER)
  assert sep.is_visible()
  assert sep.get_attribute("role") == "separator"
  assert sep.get_attribute("aria-orientation") == "vertical"
  assert sep.get_attribute("tabindex") == "0"
  assert abs(int(sep.get_attribute("aria-valuenow")) - width) < 3


def test_compact_resize_with_drag_and_keys(new_page):
  """L8: a drag and the arrow keys change the width, within min and max."""
  page = new_page(1280, 800)
  _step_on(page)
  start = _compact_width(page)
  box = page.locator(RESIZER).bounding_box()
  cx, cy = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
  page.mouse.move(cx, cy)
  page.mouse.down()
  page.mouse.move(cx - 100, cy, steps=5)
  page.mouse.up()
  assert abs(_compact_width(page) - min(MAX_W, start + 100)) < 4
  # Far left: the width stops at the maximum.
  box = page.locator(RESIZER).bounding_box()
  page.mouse.move(box["x"] + 2, cy)
  page.mouse.down()
  page.mouse.move(box["x"] - 600, cy, steps=5)
  page.mouse.up()
  assert abs(_compact_width(page) - MAX_W) < 2
  # Keyboard: the right arrow key makes the panel narrower by 20 px.
  page.focus(RESIZER)
  page.keyboard.press("ArrowRight")
  assert abs(_compact_width(page) - (MAX_W - 20)) < 2
  assert page.get_attribute(RESIZER, "aria-valuenow") == str(MAX_W - 20)
  page.keyboard.press("ArrowLeft")
  assert abs(_compact_width(page) - MAX_W) < 2
  for _ in range(20):
    page.keyboard.press("ArrowRight")
  assert abs(_compact_width(page) - MIN_W) < 2


def test_compact_width_persists(new_page):
  """L8: the browser remembers the width."""
  page = new_page(1280, 800)
  _step_on(page)
  page.focus(RESIZER)
  for _ in range(3):
    page.keyboard.press("ArrowLeft")
  width = _compact_width(page)
  page.reload()
  page.wait_for_timeout(800)
  assert abs(_compact_width(page) - width) < 2


def test_strip_has_no_resizer_at_1024(new_page):
  """L8: the strip below 1100 px does not change, and no separator shows."""
  page = new_page(1024, 700)
  _step_on(page)
  assert not page.locator(RESIZER).is_visible()
  strip = page.locator(f"{COMPACT} .compact-strip")
  assert strip.is_visible()
  chat = page.locator("#messages-container").bounding_box()
  box = strip.bounding_box()
  assert box["y"] + box["height"] <= chat["y"] + 1
  assert abs(box["width"] - page.locator("#playground-panel").bounding_box()["width"]) < 30


# ---- Phase 5 review fix: one colour scheme (L9) ----
CONTRAST_JS = """(el) => {
  const parse = (c) => (c.match(/[\\d.]+/g) || []).map(Number);
  const lum = (rgb) => {
    const f = (v) => { v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(rgb[0]) + 0.7152 * f(rgb[1]) + 0.0722 * f(rgb[2]);
  };
  const bgOf = (e) => {
    while (e && e.nodeType === 1) {
      const p = parse(getComputedStyle(e).backgroundColor);
      if (p.length === 3 || (p.length === 4 && p[3] > 0)) { return p.slice(0, 3); }
      e = e.parentElement;
    }
    return [255, 255, 255];
  };
  const ratio = (a, b) => { const x = lum(a), y = lum(b);
    return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const fg = parse(getComputedStyle(el).color).slice(0, 3);
  return ratio(fg, bgOf(el));
}"""

UI_CONTRAST_JS = """([el, prop]) => {
  const parse = (c) => (c.match(/[\\d.]+/g) || []).map(Number);
  const lum = (rgb) => {
    const f = (v) => { v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(rgb[0]) + 0.7152 * f(rgb[1]) + 0.0722 * f(rgb[2]);
  };
  const part = parse(getComputedStyle(el)[prop]).slice(0, 3);
  let e = el.parentElement, bg = [255, 255, 255];
  while (e) { const p = parse(getComputedStyle(e).backgroundColor);
    if (p.length === 3 || (p.length === 4 && p[3] > 0)) { bg = p.slice(0, 3); break; }
    e = e.parentElement; }
  const x = lum(part), y = lum(bg);
  return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05);
}"""

MAIN = "#1a73e8"
WARNING = "#c5221f"


def _var(page, name, selector=":root"):
  return page.evaluate(
      "([s, n]) => getComputedStyle(document.querySelector(s))"
      ".getPropertyValue(n).trim().toLowerCase()", [selector, name])


def _text_ratio(page, selector):
  return page.locator(selector).first.evaluate(CONTRAST_JS)


def test_palette_tokens_and_main_buttons(new_page):
  """L9: one main colour from CSS variables, red for warnings, green token."""
  page = new_page()
  assert _var(page, "--color-main") == MAIN
  assert _var(page, "--color-warning") == WARNING
  assert _var(page, "--color-allowed") != ""
  # The Material buttons (Save & Apply Settings, Load Remote Agents) use the
  # main colour, not the default purple.
  for button in ("#save-settings", "#load-agents-btn"):
    assert _var(page, "--md-sys-color-primary", button) == MAIN
    assert _var(page, "--md-sys-color-on-primary", button) == "#ffffff"
  # Red only for warnings: the Demo only label and the panel border.
  badge_bg = page.locator(".demo-badge").evaluate(
      "e => getComputedStyle(e).backgroundColor")
  assert badge_bg == "rgb(197, 34, 31)"
  border = page.locator(".demo-controls").evaluate(
      "e => getComputedStyle(e).borderTopColor")
  assert border == "rgb(197, 34, 31)"
  # The selected tab, the switch when on, and the links use the main colour.
  tab_bg = page.locator(".tab[aria-selected=true]").evaluate(
      "e => getComputedStyle(e).backgroundColor")
  assert tab_bg == "rgb(26, 115, 232)"
  link = page.locator("#demo-github-link").evaluate(
      "e => getComputedStyle(e).color")
  assert link == "rgb(26, 115, 232)"


def test_text_contrast_meets_wcag_aa(new_page):
  """L9: text contrast is at least 4.5:1, UI parts at least 3:1."""
  page = new_page()
  for selector in (".tab[aria-selected=true]", ".tab[aria-selected=false]",
                   "#step-chip", ".demo-badge", "#demo-github-link",
                   ".step-switch", "#am-open-demo-controls"):
    ratio = _text_ratio(page, selector)
    assert ratio >= 4.5, f"{selector}: {ratio:.2f}"
  # UI part: the switch track when on, against its background.
  page.add_style_tag(content="* { transition: none !important; }")
  page.click(".step-switch")
  ratio = page.evaluate(
      UI_CONTRAST_JS, [page.locator(".switch-track").element_handle(),
                       "backgroundColor"])
  assert ratio >= 3.0, f"switch track: {ratio:.2f}"


def test_switch_state_has_a_text_label(new_page):
  """L9: the switch state shows as text, not only as colour."""
  page = new_page()
  state = page.locator(".step-switch .switch-state")
  assert state.inner_text() == "Off"
  page.click(".step-switch")
  assert state.inner_text() == "On"
  page.click(".step-switch")
  assert state.inner_text() == "Off"
