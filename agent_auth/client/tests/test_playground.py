"""Browser tests for the Playground (Step mode off).

These tests check the client behaviour before the Step mode track. They are
the baseline for acceptance criterion A1.
"""

import pytest

EMPTY_BUBBLES_JS = """() => [...document.querySelectorAll('.agent-message')]
  .filter(b => !b.innerText.trim()).length"""


def send(page, text: str) -> None:
  """Types a message in the chat and sends it."""
  page.fill("#user-input", text)
  page.press("#user-input", "Enter")


def watch(page, seconds: float) -> tuple[int, list]:
  """Samples the chat every 0.2 s.

  Returns:
    The largest count of empty agent bubbles, and a list of
    (time, dots visible, last wait text) samples.
  """
  empty_max = 0
  samples = []
  for i in range(int(seconds * 5)):
    page.wait_for_timeout(200)
    empty_max = max(empty_max, page.evaluate(EMPTY_BUBBLES_JS))
    waits = page.locator(".wait-indicator .wait-text").all_inner_texts()
    dots = page.locator(".typing-dots")
    visible = dots.count() > 0 and dots.first.is_visible()
    samples.append((round((i + 1) * 0.2, 1), visible,
                    waits[-1] if waits else ""))
  return empty_max, samples


@pytest.mark.parametrize("mode,close_early,expect_finalize", [
    ("fast", False, 1),
    ("slow", False, 1),
    ("slow", True, 0),
])
def test_resume_once(new_page, stats, mode, close_early, expect_finalize):
  """The client resumes the agent exactly once after the consent."""
  page = new_page()
  with page.context.expect_page() as popup_info:
    send(page, mode)
  popup = popup_info.value
  page.wait_for_timeout(500)
  if mode != "fast":
    # In fast mode the consent is complete before this check.
    assert "Waiting for your approval" in " ".join(
        page.locator(".wait-indicator .wait-text").all_inner_texts())
  if close_early:
    popup.close()
  page.wait_for_selector("text=private-repo-c", timeout=20000)
  page.wait_for_timeout(1500)
  s = stats.get()
  assert s["resume"] == 1
  assert s["chat"] == 2
  assert s["finalize"] == expect_finalize
  assert page.locator(".wait-indicator").count() == 0
  assert "step 12" in page.inner_text("#step-chip")


def test_resume_once_without_opener(new_page, stats, base_url):
  """A validate page in a tab with no opener still resumes once."""
  page = new_page()
  with page.context.expect_page() as popup_info:
    send(page, "stay")
  popup = popup_info.value
  page.wait_for_timeout(800)
  other = page.context.new_page()
  other.goto(base_url + "/validateUserId?user_id_validation_state=YWJj"
             "&auth_provider_name=projects/p/locations/l/authProviders/a")
  page.wait_for_selector("text=private-repo-c", timeout=20000)
  page.wait_for_timeout(1500)
  assert stats.get()["resume"] == 1
  assert not popup.is_closed()


def test_no_empty_bubble_and_status_lines(new_page, stats):
  """Dots show at once, a tool call changes the status, no empty bubble."""
  page = new_page()
  send(page, "md")
  empty_max, samples = watch(page, 5)
  assert empty_max == 0
  assert samples[0][1] is True
  assert samples[0][2] == "The agent is working..."
  texts = {s[2] for s in samples}
  assert "The agent is calling a tool: search_repositories..." in texts
  assert page.locator(".wait-indicator").count() == 0
  assert stats.get()["chat"] == 1


def test_markdown_and_sanitizer(new_page, stats):  # pylint: disable=unused-argument
  """Answers render as Markdown, and unsafe HTML does not run."""
  page = new_page()
  send(page, "md")
  page.wait_for_selector(".answer-text.markdown", timeout=15000)
  ans = page.locator(".answer-text.markdown").last
  assert ans.locator("li").count() == 3
  assert ans.locator("strong").count() >= 1
  assert ans.locator("em").count() >= 1
  assert ans.locator("tr").count() == 3
  assert ans.locator("pre").count() == 1
  links = ans.locator("a").evaluate_all(
      "els => els.map(a => [a.getAttribute('href'), a.target, a.rel])")
  assert ["https://github.com/", "_blank", "noopener noreferrer"] in links
  assert all(href is None or not href.startswith("javascript:")
             for href, _, _ in links)
  assert page.locator("#messages-container script").count() == 0
  assert page.locator("#messages-container [onerror]").count() == 0
  assert page.locator("#messages-container img").count() == 0
  assert page.evaluate("() => window.__xss") is None


def test_new_conversation(new_page, stats):
  """New conversation clears the chat and starts a new session."""
  page = new_page()
  send(page, "md")
  page.wait_for_selector(".answer-text.markdown", timeout=15000)
  page.click("#new-conversation")
  page.wait_for_timeout(300)
  assert page.locator(".system-message").last.inner_text() == (
      "New conversation started.")
  assert page.inner_text("#step-chip") == "3LO step: none"
  assert page.locator(".answer-text").count() == 0
  send(page, "md")
  page.wait_for_selector(".answer-text.markdown", timeout=15000)
  assert stats.get()["no_session"] == 2


@pytest.mark.parametrize("width,height", [(1280, 800), (1024, 700)])
def test_diagram_height(new_page, width, height):
  """The 3LO diagram shows at full height, with 12 steps."""
  page = new_page(width, height)
  page.click("#tab-how")
  page.wait_for_timeout(300)
  box = page.locator("svg.flow-svg").bounding_box()
  assert box["height"] > 400
  assert page.locator("svg.flow-svg .flow-step").count() == 12
  assert page.locator("svg.flow-svg .party-name").count() == 6
