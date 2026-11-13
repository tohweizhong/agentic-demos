// Frontend for the Managed Agents API demo.
//
// The page talks only to the local Go server. The server holds the Google credentials.

import { parseEvents, type StreamEvent } from "./sse.js";

interface Agent {
  id: string;
  description: string;
}

interface OutputFile {
  name: string;
  size: number;
  contentType: string;
  updated: string;
}

interface Session {
  agent: string;
  interactionId: string;
  environmentId: string;
}

const $ = <T extends HTMLElement>(id: string): T => {
  const element = document.getElementById(id);
  if (!element) {
    throw new Error(`Missing element #${id}`);
  }
  return element as T;
};

let lastSession: Session | null = null;

async function getJSON<T>(url: string): Promise<T> {
  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`${url}: HTTP ${response.status}: ${await response.text()}`);
  }
  return (await response.json()) as T;
}

function showError(target: HTMLElement, message: string): void {
  const line = document.createElement("p");
  line.className = "error";
  line.textContent = message;
  target.append(line);
}

async function loadConfig(): Promise<void> {
  const config = await getJSON<{ project: string; bucket: string }>("/api/config");
  $("project").textContent = config.project;
  $("bucket").textContent = config.bucket;
}

async function loadAgents(): Promise<void> {
  const select = $<HTMLSelectElement>("agent");
  const agents = await getJSON<Agent[]>("/api/agents");
  select.replaceChildren(
    ...agents.map((agent) => {
      const option = document.createElement("option");
      option.value = agent.id;
      option.textContent = agent.description ? `${agent.id}: ${agent.description}` : agent.id;
      return option;
    }),
  );
  if (agents.length === 0) {
    showError($("task-form"), "No agents. Run scripts/01_lifecycle.py first.");
  }
}

function addStep(text: string): void {
  const item = document.createElement("li");
  item.textContent = text;
  $("steps").append(item);
}

function showUsage(interaction: Record<string, unknown>): void {
  const usage = (interaction.usage ?? {}) as Record<string, unknown>;
  const rows: Array<[string, unknown]> = [
    ["Status", interaction.status],
    ["Interaction ID", interaction.id],
    ["Environment ID", interaction.environment_id],
    ["Input tokens", usage.total_input_tokens],
    ["Output tokens", usage.total_output_tokens],
    ["Total tokens", usage.total_tokens],
  ];
  $("usage").replaceChildren(
    ...rows.flatMap(([name, value]) => {
      const dt = document.createElement("dt");
      dt.textContent = name;
      const dd = document.createElement("dd");
      dd.textContent = value === undefined ? "-" : String(value);
      return [dt, dd];
    }),
  );
}

// handleEvent shows one stream event. Text chunks have an event_id. The API can repeat the
// full text of a step without an event_id, so the page skips that repeat.
function handleEvent(item: StreamEvent, agent: string): void {
  const data = item.data;
  const type = (data.event_type as string) ?? item.event;
  if (type === "step.start") {
    const step = (data.step ?? {}) as Record<string, unknown>;
    const stepType = String(step.type ?? "");
    if (stepType === "model_output" && $("text").textContent) {
      // Each text step is a new paragraph.
      $("text").textContent += "\n\n";
    } else if (stepType === "function_call") {
      addStep(`tool call: ${String(step.name)}`);
    } else if (stepType.endsWith("_call")) {
      addStep(`tool call: ${stepType.replace(/_call$/, "")}`);
    }
  } else if (type === "step.delta") {
    const delta = (data.delta ?? {}) as Record<string, unknown>;
    if (delta.type === "text" && "event_id" in data) {
      $("text").textContent += String(delta.text ?? "");
    } else if (delta.type === "text_annotation_delta") {
      const notes = (delta.annotations ?? []) as Array<Record<string, unknown>>;
      for (const note of notes) {
        addStep(`citation: ${String(note.title ?? note.url)}`);
      }
    }
  } else if (type === "interaction.completed") {
    const interaction = (data.interaction ?? {}) as Record<string, unknown>;
    showUsage(interaction);
    if (interaction.id && interaction.environment_id) {
      lastSession = {
        agent,
        interactionId: String(interaction.id),
        environmentId: String(interaction.environment_id),
      };
      $<HTMLInputElement>("follow-up").disabled = false;
    }
  } else if (type === "error") {
    showError($("steps"), JSON.stringify(data.error ?? data));
  }
}

async function sendTask(event: SubmitEvent): Promise<void> {
  event.preventDefault();
  const agent = $<HTMLSelectElement>("agent").value;
  const input = $<HTMLTextAreaElement>("input").value.trim();
  const followUp = $<HTMLInputElement>("follow-up").checked && lastSession?.agent === agent;
  const body: Record<string, string> = { agent, input };
  if (followUp && lastSession) {
    body.previousInteractionId = lastSession.interactionId;
    body.environmentId = lastSession.environmentId;
  }

  const button = $<HTMLButtonElement>("send");
  button.disabled = true;
  $("steps").replaceChildren();
  $("text").textContent = "";
  $("usage").replaceChildren();
  addStep(followUp ? "follow-up in the same session" : "new interaction");

  try {
    const response = await fetch("/api/interactions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!response.ok || !response.body) {
      throw new Error(`HTTP ${response.status}: ${await response.text()}`);
    }
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const parsed = parseEvents(buffer);
      buffer = parsed.rest;
      parsed.events.forEach((item) => handleEvent(item, agent));
    }
    await loadOutputs();
  } catch (error) {
    showError($("steps"), String(error));
  } finally {
    button.disabled = false;
  }
}

async function loadOutputs(): Promise<void> {
  const list = $("outputs");
  try {
    const files = await getJSON<OutputFile[]>("/api/outputs");
    list.replaceChildren(
      ...files.map((file) => {
        const item = document.createElement("li");
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = `${file.name.replace("agent/output/", "")} (${file.size} bytes)`;
        button.addEventListener("click", () => void preview(file));
        item.append(button);
        return item;
      }),
    );
    if (files.length === 0) {
      list.textContent = "No files yet.";
    }
  } catch (error) {
    list.replaceChildren();
    showError(list, String(error));
  }
}

async function preview(file: OutputFile): Promise<void> {
  const target = $("preview");
  const url = `/api/outputs/file?name=${encodeURIComponent(file.name)}`;
  if (file.name.endsWith(".png")) {
    const image = document.createElement("img");
    image.src = url;
    image.alt = file.name;
    target.replaceChildren(image);
    return;
  }
  const response = await fetch(url);
  const pre = document.createElement("pre");
  pre.textContent = await response.text();
  target.replaceChildren(pre);
}

async function start(): Promise<void> {
  $<HTMLFormElement>("task-form").addEventListener("submit", (event) => void sendTask(event));
  $("refresh").addEventListener("click", () => void loadOutputs());
  try {
    await loadConfig();
    await loadAgents();
  } catch (error) {
    showError($("task-form"), String(error));
  }
  await loadOutputs();
}

void start();
