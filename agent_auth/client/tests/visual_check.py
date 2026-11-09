"""Visual check of the demo client. Run it before you ask a person to review UI.

The script starts the fake agent server (fake_agent_server.py), opens headless
Chrome, and clicks through the views that a presenter uses:
- Egress gateway: an allowed long answer, then the blocked send_email prompt.
- Ingress gateway: the three sample prompts.
- 3LO GitHub with Step mode off: the arrow step-through and the answer table.

It prints PASS or FAIL for each check and saves one PNG file for each view.
Open the PNG files and look at them. A PASS does not replace a visual look.

Usage (from agent_auth/client):
  .venv/bin/python tests/visual_check.py /tmp/visual_check
  VW=1024 VH=560 .venv/bin/python tests/visual_check.py /tmp/visual_check_narrow

VW and VH set the viewport. The default 1440 x 790 shows the three-column
layout. Below 1100 px wide, the page uses the narrow layout.
The script exits with code 1 if a check fails.
"""

import os
import socket
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright

CLIENT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)


def free_port():
  with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    return s.getsockname()[1]


port = free_port()
env = dict(os.environ, GOOGLE_CLOUD_PROJECT="test-project",
           GOOGLE_CLOUD_LOCATION="us-central1",
           INGRESS_AGENT_ID="ingress-engine-test",
           EGRESS_AGENT_ID="egress-engine-test")
proc = subprocess.Popen(
    [sys.executable, os.path.join(CLIENT, "tests", "fake_agent_server.py"),
     "--port", str(port)], cwd=CLIENT, env=env,
    stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
url = f"http://localhost:{port}"
for _ in range(200):
  try:
    urllib.request.urlopen(url + "/test/stats", timeout=1)
    break
  except OSError:
    time.sleep(0.3)

results = []


def check(name, ok, detail=""):
  results.append((name, ok, detail))


def inner_scrollers(page, sel):
  """Returns messages that have their own vertical scroll bar."""
  return page.evaluate(
      """sel => [...document.querySelectorAll(sel + ' > *')]
        .filter(el => el.scrollHeight > el.clientHeight + 1 &&
                ['auto','scroll'].includes(getComputedStyle(el).overflowY))
        .map(el => el.className)""", sel)


try:
  with sync_playwright() as p:
    try:
      b = p.chromium.launch(channel="chrome", headless=True)
    except Exception:  # pylint: disable=broad-except
      b = p.chromium.launch(headless=True)
    ctx = b.new_context(viewport={
        "width": int(os.environ.get("VW", 1440)),
        "height": int(os.environ.get("VH", 790)),
    })
    page = ctx.new_page()
    page.goto(url)
    page.wait_for_timeout(800)

    # Egress: allowed long answer, then blocked send_email.
    page.click("#tab-egress")
    pan = page.locator("#egress-panel")
    pan.locator(".sample-prompt").nth(0).click()
    page.wait_for_selector("#egress-messages .answer-text.markdown")
    page.wait_for_timeout(300)
    check("egress allowed: no banner",
          pan.locator(".gateway-block-banner").count() == 0)
    check("egress: no inner scroll bars",
          not inner_scrollers(page, "#egress-messages"),
          str(inner_scrollers(page, "#egress-messages")))
    page.screenshot(path=f"{OUT}/01_egress_allowed.png")
    pan.locator(".sample-prompt").nth(1).click()
    page.wait_for_selector("#egress-messages .gateway-block-banner")
    page.wait_for_timeout(300)
    m = page.locator("#egress-messages")
    m.evaluate("el => el.scrollTop = el.scrollHeight")
    check("egress list scrolls", m.evaluate(
        "el => el.scrollHeight > el.clientHeight && el.scrollTop > 0"))
    page.screenshot(path=f"{OUT}/02_egress_blocked_scrolled.png")
    m.evaluate("el => el.scrollTop = 0")
    page.screenshot(path=f"{OUT}/03_egress_top.png")

    # Ingress: all three prompts.
    page.click("#tab-ingress")
    pan = page.locator("#ingress-panel")
    for i in range(3):
      pan.locator(".sample-prompt").nth(i).click()
      page.wait_for_function(
          f"document.querySelectorAll('#ingress-messages .agent-message "
          f".answer-text.markdown').length >= {i + 1}", timeout=10000)
    page.wait_for_timeout(300)
    check("ingress: one banner (SSN prompt only)",
          pan.locator(".gateway-block-banner").count() == 1,
          str(pan.locator(".gateway-block-banner").count()))
    check("ingress: no inner scroll bars",
          not inner_scrollers(page, "#ingress-messages"),
          str(inner_scrollers(page, "#ingress-messages")))
    page.screenshot(path=f"{OUT}/04_ingress.png")

    # 3LO GitHub, Step mode off: arrow step-through and the answer table.
    page.click("#tab-play")
    page.evaluate("localStorage.setItem('agentAuthStepMode','0')")
    page.reload()
    page.wait_for_timeout(800)
    page.fill("#user-input", "token list my recent PRs")
    page.press("#user-input", "Enter")
    seen = []
    for _ in range(60):
      chip = page.locator("#step-chip").inner_text()
      if not seen or seen[-1] != chip:
        seen.append(chip)
        if len(seen) <= 4:
          page.screenshot(path=f"{OUT}/05_play_step_{len(seen)}.png")
      if "12" in chip.split(":")[0]:
        break
      page.wait_for_timeout(100)
    check("non-step mode shows several single steps", len(seen) >= 4,
          " | ".join(seen))
    page.wait_for_selector("#messages-container .answer-text.markdown",
                           timeout=15000)
    page.wait_for_timeout(500)
    check("play: no inner scroll bars",
          not inner_scrollers(page, "#messages-container"),
          str(inner_scrollers(page, "#messages-container")))
    over = page.evaluate("""() => [...document.querySelectorAll(
        '#messages-container .agent-message table')].map(t => {
          const b = t.closest('.agent-message').getBoundingClientRect();
          const r = t.getBoundingClientRect();
          return r.right <= b.right + 1; })""")
    check("play: table inside bubble", all(over), str(over))
    page.screenshot(path=f"{OUT}/06_play_answer.png")
    b.close()
finally:
  proc.terminate()

bad = [r for r in results if not r[1]]
for name, ok, detail in results:
  print(("PASS " if ok else "FAIL ") + name + (f"  [{detail}]" if detail else ""))
sys.exit(1 if bad else 0)
