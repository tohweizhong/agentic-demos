"""Browser tests for the Ingress and Egress gateway tabs (track gateway_tabs_20261108)."""

INGRESS_PROMPTS = [
    "what are the names of our west customers?",
    (
        "what are the SSNs for bob johnson and alice brown? Format each line"
        " as Name - SSN: xxx-xx-xxxx"
    ),
    "what are bob johnson's and alice brown's email addresses?",
]

INGRESS_LABELS = [
    "Allow: List West region customers",
    "Block (Model Armor): Request customer SSNs",
    "Allow: List customer email addresses",
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

EGRESS_LABELS = [
    "Allow: Summarize Sterling tax returns",
    "Block (IAP): Email summary to jane@example.com",
    "Allow: Read latest corporate inbox emails",
]


def test_ingress_tab_prompts_chat_banner_and_logs(new_page, stats):
  """G1, G5, G8: Ingress tab sample prompts, chat, block banner, and logs."""
  page = new_page(1280, 800)
  # Check tab order (3 live interactive tabs first, 2 reference tabs on right).
  tab_labels = page.locator(".tabs [role=tab]").all_inner_texts()
  assert tab_labels == [
      "3LO GitHub",
      "Egress gateway",
      "Ingress gateway",
      "How 3LO works",
      "Auth Manager",
  ]
  # Check Configuration Settings sidebar on 3LO GitHub tab.
  assert page.locator("#settings-sidebar h2").inner_text() == "Configuration Settings"
  assert page.locator("#demo-controls").count() == 1

  page.click("#tab-ingress")
  panel = page.locator("#ingress-panel")
  assert panel.is_visible()
  # 3LO-only header actions, step chip, and left sidebar are hidden on Ingress tab.
  assert not page.locator(".header-right").is_visible()
  assert not page.locator("#step-chip").is_visible()
  assert not page.locator("#settings-sidebar").is_visible()
  assert "ingress-engine-test" in panel.locator("#ingress-agent-id").inner_text()

  # Check the 3 outcome-labeled buttons, data-prompt attributes, and usecase line.
  assert "CRM agent" in panel.locator(".gateway-usecase").inner_text()
  assert panel.locator(".sample-prompt").all_inner_texts() == INGRESS_LABELS
  prompts = panel.locator(".sample-prompt").evaluate_all(
      "els => els.map(b => b.getAttribute('data-prompt'))"
  )
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
  first_time_cell = panel.locator("#ingress-log-table tbody tr td").first
  assert "SGT" in first_time_cell.inner_text()
  assert "2026" not in first_time_cell.inner_text()
  assert "2026-11-08" in (first_time_cell.get_attribute("title") or "")
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

  # Check the 3 outcome-labeled buttons and data-prompt attributes.
  assert panel.locator(".sample-prompt").all_inner_texts() == EGRESS_LABELS
  prompts = panel.locator(".sample-prompt").evaluate_all(
      "els => els.map(b => b.getAttribute('data-prompt'))"
  )
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
  # An allowed answer with a redacted SSN is not an Egress block.
  assert panel.locator(".gateway-block-banner").count() == 0
  # The long answer bubble keeps its full height. Only the message list
  # scrolls, so the bubble has no inner scroll bar.
  bubble = panel.locator("#egress-messages .agent-message").last
  sizes = bubble.evaluate(
      "el => [el.scrollHeight, el.clientHeight, getComputedStyle(el).overflowY]"
  )
  assert sizes[0] <= sizes[1] + 1, sizes
  msgs = panel.locator("#egress-messages")
  assert msgs.evaluate("el => el.scrollHeight > el.clientHeight")

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
