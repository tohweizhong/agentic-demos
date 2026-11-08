"""Pytest fixtures for the client browser tests.

The fixtures start the fake agent server (fake_agent_server.py) and a headless
Chrome browser. They also collect JavaScript coverage for static/script.js
through the Chrome DevTools Protocol.

Set JS_COVERAGE_OUT=<file> to write the per-line coverage of script.js as JSON.
"""

import contextlib
import json
import os
import socket
import subprocess
import sys
import time
import urllib.request

from playwright.sync_api import sync_playwright
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_URL_SUFFIX = "/static/script.js"


def _free_port() -> int:
  with socket.socket() as s:
    s.bind(("127.0.0.1", 0))
    return s.getsockname()[1]


@pytest.fixture(scope="session")
def base_url():
  """Starts the fake agent server and returns its base URL."""
  port = _free_port()
  env = dict(os.environ)
  env.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
  env.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
  env.setdefault("INGRESS_AGENT_ID", "ingress-engine-test")
  env.setdefault("EGRESS_AGENT_ID", "egress-engine-test")
  proc = subprocess.Popen(
      [sys.executable, os.path.join(TESTS_DIR, "fake_agent_server.py"),
       "--port", str(port)],
      env=env, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
  url = f"http://localhost:{port}"
  deadline = time.time() + 60
  while time.time() < deadline:
    try:
      urllib.request.urlopen(url + "/test/stats", timeout=1)
      break
    except OSError:
      time.sleep(0.3)
  else:
    proc.kill()
    raise RuntimeError("The fake agent server did not start.")
  yield url
  proc.terminate()
  proc.wait(timeout=10)


@pytest.fixture(scope="session")
def browser():
  """Starts headless Chrome. Uses the installed Google Chrome if present."""
  with sync_playwright() as p:
    try:
      b = p.chromium.launch(channel="chrome", headless=True)
    except Exception:  # pylint: disable=broad-except
      b = p.chromium.launch(headless=True)
    yield b
    b.close()


class Stats:
  """Reads and resets the request counters of the fake agent server."""

  def __init__(self, url: str):
    self._url = url

  def reset(self) -> None:
    req = urllib.request.Request(self._url + "/test/stats/reset",
                                 method="POST")
    urllib.request.urlopen(req)

  def get(self) -> dict:
    return json.loads(urllib.request.urlopen(self._url + "/test/stats").read())


@pytest.fixture
def stats(base_url):
  s = Stats(base_url)
  s.reset()
  return s


# ---- JavaScript coverage of static/script.js ----
_COVERAGE = {"source": None, "covered": None}


def _merge_coverage(result: dict, source: str) -> None:
  """Merges one CDP precise coverage result into the byte map."""
  if _COVERAGE["source"] is None:
    _COVERAGE["source"] = source
    _COVERAGE["covered"] = bytearray(len(source))
  counts = [None] * len(source)
  for func in result["functions"]:
    for rng in func["ranges"]:
      for i in range(rng["startOffset"], min(rng["endOffset"], len(source))):
        counts[i] = rng["count"]
  for i, c in enumerate(counts):
    if c:
      _COVERAGE["covered"][i] = 1


@pytest.fixture
def new_page(browser, base_url):
  """Returns a function that opens a new page with JS coverage on."""
  opened = []

  def _open(width=1280, height=800):
    ctx = browser.new_context(viewport={"width": width, "height": height})
    page = ctx.new_page()
    cdp = ctx.new_cdp_session(page)
    cdp.send("Profiler.enable")
    cdp.send("Profiler.startPreciseCoverage",
             {"callCount": True, "detailed": True})
    opened.append((ctx, page, cdp))
    page.goto(base_url + "/")
    page.wait_for_timeout(1200)
    return page

  yield _open

  for ctx, page, cdp in opened:
    with contextlib.suppress(Exception):
      result = cdp.send("Profiler.takePreciseCoverage")
      for script in result["result"]:
        if script["url"].endswith(SCRIPT_URL_SUFFIX):
          source = urllib.request.urlopen(script["url"]).read().decode()
          _merge_coverage(script, source)
    ctx.close()


def line_coverage() -> dict:
  """Returns {line_number: covered} for lines with code in script.js."""
  source = _COVERAGE["source"]
  if source is None:
    return {}
  result = {}
  offset = 0
  for number, line in enumerate(source.split("\n"), start=1):
    stripped = line.strip()
    if stripped and not stripped.startswith("//") and stripped not in (
        "}", "});", "};", ")", "});", "]", "],", "},"):
      start = offset + (len(line) - len(line.lstrip()))
      end = offset + len(line)
      result[number] = any(_COVERAGE["covered"][start:end])
    offset += len(line) + 1
  return result


def pytest_sessionfinish(session, exitstatus):  # pylint: disable=unused-argument
  """Prints the script.js coverage, and writes it to JS_COVERAGE_OUT if set."""
  lines = line_coverage()
  if not lines:
    return
  covered = sum(1 for v in lines.values() if v)
  print(f"\nscript.js line coverage: {covered}/{len(lines)} "
        f"({100.0 * covered / len(lines):.1f} percent)")
  out = os.environ.get("JS_COVERAGE_OUT")
  if out:
    with open(out, "w") as f:
      json.dump({str(k): v for k, v in lines.items()}, f)
