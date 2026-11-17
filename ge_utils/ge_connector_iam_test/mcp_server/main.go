// Command iamtest-mcp is a small MCP server for the connector-level IAM test.
//
// The server has one tool, get_marker. The tool returns a fixed marker text.
// When the marker text is in a Gemini Enterprise answer, the test knows that
// Gemini Enterprise called the server. Each tool call writes one log line, so
// the Cloud Run logs show every call.
//
// The server uses the Streamable HTTP transport at the path /mcp. It reads the
// port from the PORT environment variable. The default port is 8080.
package main

import (
	"context"
	"log"
	"net/http"
	"os"

	"github.com/modelcontextprotocol/go-sdk/mcp"
)

// marker is the text that the get_marker tool returns.
const marker = "MCP-MARKER-A"

// markerInput is the input of get_marker. The tool takes no arguments.
type markerInput struct{}

// getMarker returns the marker text and writes one log line.
func getMarker(ctx context.Context, req *mcp.CallToolRequest, in markerInput) (*mcp.CallToolResult, any, error) {
	log.Print("TOOL_CALL get_marker")
	return &mcp.CallToolResult{
		Content: []mcp.Content{&mcp.TextContent{Text: marker}},
	}, nil, nil
}

func main() {
	server := mcp.NewServer(&mcp.Implementation{Name: "iamtest-mcp-a", Version: "1.0.0"}, nil)
	mcp.AddTool(server, &mcp.Tool{
		Name: "get_marker",
		Description: "Returns the marker text for the IAM test connector A. " +
			"Call this tool when the user asks for the connector A marker or the MCP marker.",
	}, getMarker)

	handler := mcp.NewStreamableHTTPHandler(
		func(*http.Request) *mcp.Server { return server },
		&mcp.StreamableHTTPOptions{Stateless: true},
	)

	mux := http.NewServeMux()
	mux.Handle("/mcp", handler)

	port := os.Getenv("PORT")
	if port == "" {
		port = "8080"
	}
	addr := ":" + port
	log.Printf("iamtest-mcp listens on %s, path /mcp", addr)
	log.Fatal(http.ListenAndServe(addr, mux))
}
