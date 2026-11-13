// Tests for the server-sent event parser. Run after tsc: node --test test/
import { test } from "node:test";
import assert from "node:assert/strict";
import { parseEvents } from "../dist/sse.js";

test("parses complete events and keeps the rest", () => {
  const buffer =
    'event: interaction.created\ndata: {"interaction":{"id":"i1"}}\n\n' +
    'event: step.delta\ndata: {"delta":{"type":"text","text":"Hi"},"event_id":"e1"}\n\n' +
    "event: step.del";
  const { events, rest } = parseEvents(buffer);
  assert.equal(events.length, 2);
  assert.equal(events[0].event, "interaction.created");
  assert.equal(events[0].data.interaction.id, "i1");
  assert.equal(events[1].data.delta.text, "Hi");
  assert.equal(rest, "event: step.del");
});

test("skips the [DONE] marker and other non-JSON data", () => {
  const { events, rest } = parseEvents("data: [DONE]\n\n");
  assert.equal(events.length, 0);
  assert.equal(rest, "");
});

test("uses message as the default event name", () => {
  const { events } = parseEvents('data: {"a":1}\n\n');
  assert.equal(events[0].event, "message");
});
