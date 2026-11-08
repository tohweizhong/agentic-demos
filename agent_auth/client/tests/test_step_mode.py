"""Browser tests for Step mode (track step_mode_3lo_20261108).

Phase 2: the Step mode switch and the event queue.
"""

STEP_SWITCH = "#step-mode-switch"


def send(page, text: str) -> None:
  """Types a message in the chat and sends it."""
  page.fill("#user-input", text)
  page.press("#user-input", "Enter")


def turn_on_step_mode(page) -> None:
  """Turns the Step mode switch on."""
  if not page.is_checked(STEP_SWITCH):
    page.click(STEP_SWITCH)
  assert page.is_checked(STEP_SWITCH)


def test_switch_is_off_by_default_and_persists(new_page):
  """F1: the switch is off by default, and the browser remembers it."""
  page = new_page()
  switch = page.locator(STEP_SWITCH)
  assert switch.count() == 1
  assert switch.get_attribute("role") == "switch"
  assert not page.is_checked(STEP_SWITCH)
  page.click(STEP_SWITCH)
  assert page.is_checked(STEP_SWITCH)
  page.reload()
  page.wait_for_timeout(800)
  assert page.is_checked(STEP_SWITCH)
  page.click(STEP_SWITCH)
  page.reload()
  page.wait_for_timeout(800)
  assert not page.is_checked(STEP_SWITCH)


def test_step_mode_queues_events_and_hides_answer(new_page, stats):
  """F4: with Step mode on, events go to a queue and no answer shows."""
  page = new_page()
  turn_on_step_mode(page)
  send(page, "md")
  page.wait_for_timeout(5500)
  assert stats.get()["chat"] == 1
  # The server sent the whole answer, but the page does not show it.
  assert page.locator("#messages-container .answer-text").count() == 0
  assert page.locator("#messages-container .agent-message").count() == 0
  queued = int(page.get_attribute("body", "data-step-queue") or "0")
  assert queued >= 3


def test_step_mode_off_still_shows_answer(new_page):
  """A1: with Step mode off, the answer shows as before."""
  page = new_page()
  assert not page.is_checked(STEP_SWITCH)
  send(page, "md")
  page.wait_for_selector(".answer-text.markdown", timeout=15000)
