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
