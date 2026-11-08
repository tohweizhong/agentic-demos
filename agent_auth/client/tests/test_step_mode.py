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


# ---- Phase 3: step cards ----
CARD = "#messages-container .step-card"
NEXT = "#messages-container .step-card .step-next"


def cards(page):
  return page.locator(CARD)


def click_next(page, timeout=20000):
  """Waits until the Next step button is enabled, then clicks it."""
  button = page.locator(NEXT).last
  page.wait_for_function(
      """() => { const b = [...document.querySelectorAll(
          '#messages-container .step-card .step-next')].pop();
        return b && !b.disabled; }""", timeout=timeout)
  count = cards(page).count()
  button.click()
  page.wait_for_function(
      f"() => document.querySelectorAll('{CARD}').length > {count}",
      timeout=5000)


def check_newest_only_has_next(page):
  """F2: only the newest card has a Next step button."""
  total = cards(page).count()
  nexts = page.locator(NEXT).count()
  if total < 12:
    assert nexts == 1
    assert cards(page).last.locator(".step-next").count() == 1
  else:
    assert nexts == 0


def test_cards_consent_path(new_page, stats):
  """A2, F2, F3, F5, F6, F8, F9: 12 cards in order with the consent flow."""
  page = new_page()
  turn_on_step_mode(page)
  send(page, "fast")
  page.wait_for_selector(CARD, timeout=5000)
  assert "Step 1 of 12" in cards(page).first.inner_text()
  check_newest_only_has_next(page)
  for _ in range(3):  # cards 2, 3, 4
    click_next(page)
    check_newest_only_has_next(page)
  assert "Step 4 of 12" in cards(page).last.inner_text()
  # F9: the step chip and the diagram follow the card.
  assert "3LO step 4" in page.inner_text("#step-chip")
  assert page.locator("#flow-step-4.active").count() == 1
  # F3: Details shows a masked nonce, never the full nonce.
  card4 = cards(page).last
  card4.locator("summary").click()
  details = card4.inner_text()
  assert "nonc" in details
  assert "nonce-1234567890" not in details
  assert page.locator("#messages-container .answer-text").count() == 0
  # F5: the click that shows card 5 opens the GitHub window.
  with page.context.expect_page() as popup_info:
    click_next(page)
  assert popup_info.value is not None
  assert "Step 5 of 12" in cards(page).last.inner_text()
  click_next(page)  # card 6
  # F6: the resume runs in the background, while the cards wait.
  page.wait_for_function("() => true")
  click_next(page, timeout=20000)  # card 7, after the consent signal
  page.wait_for_timeout(4500)
  assert stats.get()["resume"] == 1
  assert page.locator("#messages-container .answer-text").count() == 0
  # F8: server steps say so in Details.
  card7 = cards(page).last
  card7.locator("summary").click()
  assert "Runs on the server" in card7.inner_text()
  for _ in range(5):  # cards 8 to 12
    assert page.locator("#messages-container .answer-text").count() == 0
    click_next(page)
    check_newest_only_has_next(page)
  assert cards(page).count() == 12
  # Past cards are folded (layout track L1). Read their full text from the
  # page, not only the visible text.
  titles = [cards(page).nth(i).text_content() for i in range(12)]
  for i, title in enumerate(titles, start=1):
    assert f"Step {i} of 12" in title
  # A2: the answer shows only at step 12.
  page.wait_for_selector(".answer-text.markdown", timeout=5000)
  assert stats.get()["resume"] == 1


def test_cards_stored_token(new_page, stats):
  """A3, F7: with a stored token, steps 4 to 10 say Skipped."""
  page = new_page()
  turn_on_step_mode(page)
  opened = []
  page.context.on("page", lambda p: opened.append(p))
  send(page, "token")
  page.wait_for_selector(CARD, timeout=5000)
  for _ in range(11):
    click_next(page)
  assert cards(page).count() == 12
  for i in range(4, 11):
    assert "Skipped: token already stored" in (
        cards(page).nth(i - 1).text_content())
  for i in (1, 2, 3, 11, 12):
    assert "Skipped" not in cards(page).nth(i - 1).text_content()
  assert not opened
  page.wait_for_selector(".answer-text.markdown", timeout=5000)
  assert stats.get()["resume"] == 0


def test_keyboard_moves_to_next_step(new_page, stats):  # pylint: disable=unused-argument
  """F10: the right arrow key and Enter click Next step."""
  page = new_page()
  turn_on_step_mode(page)
  send(page, "token")
  page.wait_for_selector(CARD, timeout=5000)
  page.locator("body").click(position={"x": 5, "y": 5})
  page.keyboard.press("ArrowRight")
  page.wait_for_function(f"() => document.querySelectorAll('{CARD}').length == 2")
  # Step 3 waits for the agent. Enter works when the button is enabled.
  page.wait_for_function(
      """() => { const b = [...document.querySelectorAll(
          '#messages-container .step-card .step-next')].pop();
        return b && !b.disabled; }""", timeout=10000)
  page.keyboard.press("Enter")
  page.wait_for_function(f"() => document.querySelectorAll('{CARD}').length == 3")
  # The new card gets the focus.
  focused = page.evaluate(
      "() => document.activeElement.closest('.step-card') !== null")
  assert focused


def test_expired_consent(new_page, stats):  # pylint: disable=unused-argument
  """F11: a consent request that expires during a pause shows a message."""
  page = new_page()
  turn_on_step_mode(page)
  page.evaluate("() => { window.STEP_MODE_CONSENT_EXPIRY_MS = 1; }")
  opened = []
  page.context.on("page", lambda p: opened.append(p))
  send(page, "fast")
  page.wait_for_selector(CARD, timeout=5000)
  for _ in range(3):
    click_next(page)
  page.wait_for_timeout(200)
  click_next(page)
  text = cards(page).last.inner_text()
  assert "expired" in text
  assert "send the prompt again" in text.lower()
  assert page.locator(NEXT).count() == 0
  assert not opened


def test_new_conversation_clears_cards(new_page, stats):  # pylint: disable=unused-argument
  """F12: New conversation clears the queue and the step cards."""
  page = new_page()
  turn_on_step_mode(page)
  send(page, "token")
  page.wait_for_selector(CARD, timeout=5000)
  click_next(page)
  page.click("#new-conversation")
  page.wait_for_timeout(300)
  assert cards(page).count() == 0
  assert page.get_attribute("body", "data-step-queue") == "0"
  assert page.inner_text("#step-chip") == "3LO step: none"
