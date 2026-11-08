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
  """L6: with Step mode off, the chat uses the full width of the panel."""
  page = new_page()
  assert not page.is_checked("#step-mode-switch")
  panel = page.locator("#playground-panel").bounding_box()
  messages = page.locator("#messages-container").bounding_box()
  assert abs(panel["width"] - messages["width"]) < 2
  assert page.locator("#user-input").is_visible()


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
  assert tabs.count() == 3
  assert tabs.nth(2).inner_text() == "Auth Manager"
  assert tabs.nth(2).get_attribute("role") == "tab"
  # Open it with the keyboard: arrow keys move along the tabs.
  page.focus("#tab-play")
  requests = []
  page.on("request", lambda r: requests.append(r.url))
  page.keyboard.press("ArrowRight")
  page.keyboard.press("ArrowRight")
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
