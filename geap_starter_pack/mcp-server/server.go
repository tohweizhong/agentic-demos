package main

import (
	"context"
	"fmt"
	"net/http"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// GetStatusInput is the input of the get_status tool.
type GetStatusInput struct {
	ItemID string `json:"item_id" jsonschema:"The ID of the work item, for example ITEM-001"`
}

// UpdateStatusInput is the input of the update_status tool.
type UpdateStatusInput struct {
	ItemID string `json:"item_id" jsonschema:"The ID of the work item, for example ITEM-001"`
	Status string `json:"status" jsonschema:"The new status: open, in_progress, or closed"`
}

// The tool descriptions must be the same as in tool_spec.json. A test checks this.
const (
	getStatusDescription    = "Read the status of one work item. This tool does not change data."
	updateStatusDescription = "Change the status of one work item. This tool writes data."
)

// NewServer returns an MCP server with the two sample tools.
func NewServer(store *Store) *mcp.Server {
	server := mcp.NewServer(&mcp.Implementation{Name: "work-items", Version: "v0.1.0"}, nil)

	notDestructive := false
	mcp.AddTool(server, &mcp.Tool{
		Name:        "get_status",
		Description: getStatusDescription,
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: true, IdempotentHint: true},
	}, func(_ context.Context, _ *mcp.CallToolRequest, in GetStatusInput) (*mcp.CallToolResult, Item, error) {
		it, err := store.Get(in.ItemID)
		if err != nil {
			return toolError(err), Item{}, nil
		}
		return toolText(it), it, nil
	})

	mcp.AddTool(server, &mcp.Tool{
		Name:        "update_status",
		Description: updateStatusDescription,
		Annotations: &mcp.ToolAnnotations{ReadOnlyHint: false, DestructiveHint: &notDestructive},
	}, func(_ context.Context, _ *mcp.CallToolRequest, in UpdateStatusInput) (*mcp.CallToolResult, Item, error) {
		it, err := store.Update(in.ItemID, in.Status)
		if err != nil {
			return toolError(err), Item{}, nil
		}
		return toolText(it), it, nil
	})
	return server
}

func toolText(it Item) *mcp.CallToolResult {
	return &mcp.CallToolResult{Content: []mcp.Content{
		&mcp.TextContent{Text: fmt.Sprintf("%s (%s): %s", it.ID, it.Title, it.Status)},
	}}
}

func toolError(err error) *mcp.CallToolResult {
	return &mcp.CallToolResult{IsError: true, Content: []mcp.Content{&mcp.TextContent{Text: err.Error()}}}
}

// NewMux returns the HTTP routes: /mcp for MCP (streamable HTTP) and /healthz.
func NewMux(server *mcp.Server) *http.ServeMux {
	mux := http.NewServeMux()
	// Stateless mode: Cloud Run can send each request to a different instance.
	opts := &mcp.StreamableHTTPOptions{Stateless: true}
	mux.Handle("/mcp", mcp.NewStreamableHTTPHandler(func(*http.Request) *mcp.Server { return server }, opts))
	mux.HandleFunc("/healthz", func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusOK)
		_, _ = w.Write([]byte("ok\n"))
	})
	return mux
}
