package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"sort"
	"strings"
	"testing"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// connect starts the server on an in-memory transport and returns a client session.
func connect(t *testing.T) *mcp.ClientSession {
	t.Helper()
	ctx := context.Background()
	server := NewServer(NewStore())
	st, ct := mcp.NewInMemoryTransports()
	if _, err := server.Connect(ctx, st, nil); err != nil {
		t.Fatalf("server.Connect: %v", err)
	}
	client := mcp.NewClient(&mcp.Implementation{Name: "test-client", Version: "v0.0.1"}, nil)
	cs, err := client.Connect(ctx, ct, nil)
	if err != nil {
		t.Fatalf("client.Connect: %v", err)
	}
	t.Cleanup(func() { cs.Close() })
	return cs
}

func callText(t *testing.T, cs *mcp.ClientSession, name string, args map[string]any) (string, bool) {
	t.Helper()
	res, err := cs.CallTool(context.Background(), &mcp.CallToolParams{Name: name, Arguments: args})
	if err != nil {
		t.Fatalf("CallTool(%s): %v", name, err)
	}
	var b strings.Builder
	for _, c := range res.Content {
		if tc, ok := c.(*mcp.TextContent); ok {
			b.WriteString(tc.Text)
		}
	}
	return b.String(), res.IsError
}

func TestListToolsHasReadOnlyAndWriteTool(t *testing.T) {
	cs := connect(t)
	res, err := cs.ListTools(context.Background(), nil)
	if err != nil {
		t.Fatalf("ListTools: %v", err)
	}
	hints := map[string]bool{}
	for _, tool := range res.Tools {
		hints[tool.Name] = tool.Annotations != nil && tool.Annotations.ReadOnlyHint
	}
	if ro, ok := hints["get_status"]; !ok || !ro {
		t.Errorf("get_status: present=%v readOnly=%v, want present and read-only", ok, ro)
	}
	if ro, ok := hints["update_status"]; !ok || ro {
		t.Errorf("update_status: present=%v readOnly=%v, want present and not read-only", ok, ro)
	}
}

func TestGetStatusTool(t *testing.T) {
	cs := connect(t)
	text, isErr := callText(t, cs, "get_status", map[string]any{"item_id": "ITEM-001"})
	if isErr {
		t.Fatalf("get_status returned a tool error: %s", text)
	}
	if !strings.Contains(text, "ITEM-001") || !strings.Contains(text, "open") {
		t.Errorf("get_status text = %q, want the item ID and the status", text)
	}
}

func TestGetStatusUnknownItemIsToolError(t *testing.T) {
	cs := connect(t)
	_, isErr := callText(t, cs, "get_status", map[string]any{"item_id": "ITEM-999"})
	if !isErr {
		t.Errorf("get_status(ITEM-999): IsError = false, want true")
	}
}

func TestUpdateStatusTool(t *testing.T) {
	cs := connect(t)
	text, isErr := callText(t, cs, "update_status", map[string]any{"item_id": "ITEM-003", "status": "closed"})
	if isErr {
		t.Fatalf("update_status returned a tool error: %s", text)
	}
	text, _ = callText(t, cs, "get_status", map[string]any{"item_id": "ITEM-003"})
	if !strings.Contains(text, "closed") {
		t.Errorf("after update_status, get_status text = %q, want status closed", text)
	}
}

func TestUpdateStatusBadValueIsToolError(t *testing.T) {
	cs := connect(t)
	_, isErr := callText(t, cs, "update_status", map[string]any{"item_id": "ITEM-001", "status": "deleted"})
	if !isErr {
		t.Errorf("update_status with bad status: IsError = false, want true")
	}
}

// TestToolSpecMatchesServer checks that tool_spec.json, which Terraform sends to
// Agent Registry, has the same tools and read-only hints as the server.
func TestToolSpecMatchesServer(t *testing.T) {
	raw, err := os.ReadFile("tool_spec.json")
	if err != nil {
		t.Fatalf("read tool_spec.json: %v", err)
	}
	var spec struct {
		Tools []struct {
			Name        string         `json:"name"`
			Description string         `json:"description"`
			InputSchema map[string]any `json:"inputSchema"`
			Annotations struct {
				ReadOnlyHint bool `json:"readOnlyHint"`
			} `json:"annotations"`
		} `json:"tools"`
	}
	if err := json.Unmarshal(raw, &spec); err != nil {
		t.Fatalf("parse tool_spec.json: %v", err)
	}
	cs := connect(t)
	res, err := cs.ListTools(context.Background(), nil)
	if err != nil {
		t.Fatalf("ListTools: %v", err)
	}
	var fromServer, fromSpec []string
	for _, tool := range res.Tools {
		ro := tool.Annotations != nil && tool.Annotations.ReadOnlyHint
		fromServer = append(fromServer, tool.Name+":"+boolText(ro)+":"+tool.Description)
	}
	for _, tool := range spec.Tools {
		if tool.InputSchema == nil {
			t.Errorf("tool_spec.json: tool %q has no inputSchema", tool.Name)
		}
		fromSpec = append(fromSpec, tool.Name+":"+boolText(tool.Annotations.ReadOnlyHint)+":"+tool.Description)
	}
	sort.Strings(fromServer)
	sort.Strings(fromSpec)
	if strings.Join(fromServer, "|") != strings.Join(fromSpec, "|") {
		t.Errorf("tool_spec.json does not match the server.\nserver: %v\nspec:   %v", fromServer, fromSpec)
	}
}

func boolText(b bool) string {
	if b {
		return "true"
	}
	return "false"
}

func TestHealthHandler(t *testing.T) {
	mux := NewMux(NewServer(NewStore()))
	rec := httptest.NewRecorder()
	mux.ServeHTTP(rec, httptest.NewRequest(http.MethodGet, "/healthz", nil))
	if rec.Code != http.StatusOK {
		t.Errorf("GET /healthz status = %d, want %d", rec.Code, http.StatusOK)
	}
}

func TestListenAddrUsesPort(t *testing.T) {
	t.Setenv("PORT", "9090")
	if got := listenAddr(); got != ":9090" {
		t.Errorf("listenAddr() = %q, want %q", got, ":9090")
	}
	t.Setenv("PORT", "")
	if got := listenAddr(); got != ":8080" {
		t.Errorf("listenAddr() with no PORT = %q, want %q", got, ":8080")
	}
}

// TestStreamableHTTPEndToEnd calls the tools over HTTP, as the agent does through the gateway.
func TestStreamableHTTPEndToEnd(t *testing.T) {
	ts := httptest.NewServer(NewMux(NewServer(NewStore())))
	defer ts.Close()
	client := mcp.NewClient(&mcp.Implementation{Name: "http-client", Version: "v0.0.1"}, nil)
	cs, err := client.Connect(context.Background(), &mcp.StreamableClientTransport{Endpoint: ts.URL + "/mcp"}, nil)
	if err != nil {
		t.Fatalf("Connect over HTTP: %v", err)
	}
	defer cs.Close()
	text, isErr := callText(t, cs, "get_status", map[string]any{"item_id": "ITEM-002"})
	if isErr || !strings.Contains(text, "in_progress") {
		t.Errorf("get_status over HTTP = %q (IsError=%v), want status in_progress", text, isErr)
	}
}
