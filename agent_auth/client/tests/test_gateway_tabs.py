"""Browser tests for the Ingress and Egress gateway tabs (track gateway_tabs_20261108)."""

INGRESS_PROMPTS = [
    "what are the names of our west customers?",
    "what are ssn's for bob johnson and alice brown?",
    "what are bob johnson's and alice brown's email addresses?",
]

EGRESS_PROMPTS = [
    (
        "I am reviewing the Sterling family's current application. Can you"
        " summarize their 2024 and 2025 tax returns and verify if their total"
        " household income meets our 2026 debt-to-income requirements?"
    ),
    "Can you send a summary of this to my email jane@example.com?",
    "Can you read my latest emails from the corporate inbox?",
]


def test_ingress_tab_prompts_chat_banner_and_logs(new_page, stats):
  """G1, G5, G8: Ingress tab sample prompts, chat, block banner, and logs."""
  page = new_page(1280, 800)
  page.click("#tab-ingress")
  panel = page.locator("#ingress-panel")
  assert panel.is_visible()
  assert "ingress-engine-test" in panel.locator("#ingress-agent-id").inner_text()

  # Check the 3 exact sample prompts.
  prompts = panel.locator(".sample-prompt").all_inner_texts()
  assert prompts == INGRESS_PROMPTS

  # Inline SVG diagram is visible in the right column.
  svg = panel.locator("#ingress-diagram svg")
  assert svg.is_visible()
  assert "Model Armor" in svg.text_content()

  # Click allowed sample prompt 1.
  panel.locator(".sample-prompt").nth(0).click()
  page.wait_for_selector(
      "#ingress-messages .answer-text.markdown", timeout=10000
  )
  assert "Bob Johnson" in panel.locator("#ingress-messages").inner_text()
  assert stats.get()["last_agent_id"] == "ingress-engine-test"
  assert panel.locator(".gateway-block-banner").count() == 0

  # Polling status shows after sending a prompt.
  assert (
      "Waiting for the log..."
      in panel.locator("#ingress-log-status").inner_text()
  )

  # Click blocked sample prompt 2 (SSN).
  panel.locator(".sample-prompt").nth(1).click()
  page.wait_for_selector(
      "#ingress-messages .gateway-block-banner", timeout=10000
  )
  banner = panel.locator(".gateway-block-banner").last
  assert banner.is_visible()
  assert "state-blocked" in (banner.get_attribute("class") or "")
  assert "Model Armor" in banner.inner_text()

  # Refresh logs and verify decision badges and gcloud command.
  panel.locator("#ingress-refresh-logs").click()
  page.wait_for_selector("#ingress-log-table .state-blocked", timeout=5000)
  assert (
      panel.locator("#ingress-log-table .state-blocked").first.inner_text()
      == "Blocked"
  )
  assert (
      panel.locator("#ingress-log-table .state-allowed").first.inner_text()
      == "Allowed"
  )
  assert "SDP (SSN)" in panel.locator("#ingress-log-table").inner_text()
  assert (
      "gcloud logging read" in panel.locator("#ingress-gcloud-cmd").inner_text()
  )

  # New conversation clears the tab chat and resets its session ID.
  panel.locator("#ingress-new-conversation").click()
  assert panel.locator("#ingress-messages .answer-text").count() == 0


def test_egress_tab_prompts_chat_banner_and_logs(new_page, stats):
  """G2, G5, G8: Egress tab sample prompts, chat, MCP block banner, and logs."""
  page = new_page(1280, 800)
  page.click("#tab-egress")
  panel = page.locator("#egress-panel")
  assert panel.is_visible()
  assert "egress-engine-test" in panel.locator("#egress-agent-id").inner_text()

  # Check the 3 exact sample prompts.
  prompts = panel.locator(".sample-prompt").all_inner_texts()
  assert prompts == EGRESS_PROMPTS

  # Inline SVG diagram is visible in the right column.
  svg = panel.locator("#egress-diagram svg")
  assert svg.is_visible()
  assert "IAP" in svg.text_content()

  # Click allowed sample prompt 1.
  panel.locator(".sample-prompt").nth(0).click()
  page.wait_for_selector(
      "#egress-messages .answer-text.markdown", timeout=10000
  )
  assert "Sterling family" in panel.locator("#egress-messages").inner_text()
  assert stats.get()["last_agent_id"] == "egress-engine-test"
  assert panel.locator(".gateway-block-banner").count() == 0

  # Click blocked sample prompt 2 (send_email -> MCP session connection lost).
  panel.locator(".sample-prompt").nth(1).click()
  page.wait_for_selector(
      "#egress-messages .gateway-block-banner", timeout=10000
  )
  banner = panel.locator(".gateway-block-banner").last
  assert banner.is_visible()
  assert "state-blocked" in (banner.get_attribute("class") or "")
  assert "IAP" in banner.inner_text()

  # Refresh logs and verify decision badges and gcloud command.
  panel.locator("#egress-refresh-logs").click()
  page.wait_for_selector("#egress-log-table .state-blocked", timeout=5000)
  assert (
      panel.locator("#egress-log-table .state-blocked").first.inner_text()
      == "Blocked"
  )
  assert (
      panel.locator("#egress-log-table .state-allowed").first.inner_text()
      == "Allowed"
  )
  assert "send_email" in panel.locator("#egress-log-table").inner_text()
  assert (
      "gcloud logging read" in panel.locator("#egress-gcloud-cmd").inner_text()
  )

  # Manual input and Enter in Egress tab also works, and New conversation resets.
  panel.locator("#egress-new-conversation").click()
  assert panel.locator("#egress-messages .answer-text").count() == 0
  panel.locator("#egress-input").fill("Can you read my latest emails?")
  panel.locator("#egress-input").press("Enter")
  page.wait_for_selector(
      "#egress-messages .answer-text.markdown", timeout=10000
  )
