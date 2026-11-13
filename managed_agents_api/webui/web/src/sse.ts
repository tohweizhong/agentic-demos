// Server-sent event parsing for the Interactions API stream.

export interface StreamEvent {
  event: string;
  data: Record<string, unknown>;
}

// parseEvents splits a server-sent event buffer into complete events. It returns the events
// and the rest of the buffer, which is the start of the next event.
export function parseEvents(buffer: string): { events: StreamEvent[]; rest: string } {
  const events: StreamEvent[] = [];
  const blocks = buffer.split("\n\n");
  const rest = blocks.pop() ?? "";
  for (const block of blocks) {
    let event = "message";
    const dataLines: string[] = [];
    for (const line of block.split("\n")) {
      if (line.startsWith("event:")) {
        event = line.slice(6).trim();
      } else if (line.startsWith("data:")) {
        dataLines.push(line.slice(5).trim());
      }
    }
    if (dataLines.length > 0) {
      try {
        events.push({ event, data: JSON.parse(dataLines.join("\n")) as Record<string, unknown> });
      } catch {
        // Skip a block that is not JSON. The stream ends with "data: [DONE]".
      }
    }
  }
  return { events, rest };
}
