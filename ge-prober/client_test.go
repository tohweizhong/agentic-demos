package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestBuildStreamAssistRequest_SharePoint(t *testing.T) {
	tc := TestCase{
		Query:         "Find policy",
		GroundingType: "vertex_ai_search",
	}
	cfg := &Config{
		ProjectID: "proj-123",
		Location:  "sg",
		DataStoreIDs: []string{"ds-sp-file"},
	}

	req := BuildStreamAssistRequest(tc, cfg, "")
	if req.Query.Text != "Find policy" {
		t.Errorf("expected query 'Find policy', got '%s'", req.Query.Text)
	}
	if req.ToolsSpec == nil || req.ToolsSpec.VertexAISearchSpec == nil {
		t.Fatalf("expected vertexAiSearchSpec to be populated")
	}
	if len(req.ToolsSpec.VertexAISearchSpec.DataStoreSpecs) != 1 {
		t.Errorf("expected 1 data store, got %d", len(req.ToolsSpec.VertexAISearchSpec.DataStoreSpecs))
	}
}

func TestBuildStreamAssistRequest_WebGrounding(t *testing.T) {
	tc := TestCase{
		Query:         "What is new in Singapore?",
		GroundingType: "web_search",
	}
	cfg := &Config{}

	req := BuildStreamAssistRequest(tc, cfg, "")
	if req.ToolsSpec == nil || req.ToolsSpec.WebGroundingSpec == nil {
		t.Fatalf("expected webGroundingSpec to be populated")
	}
}

func TestBuildStreamAssistRequest_DeepResearch(t *testing.T) {
	tc := TestCase{
		Query:         "Research MCP protocol adoption",
		GroundingType: "deep_research_agent",
	}
	cfg := &Config{
		ProjectID: "proj-123",
		Location:  "sg",
	}

	req := BuildStreamAssistRequest(tc, cfg, "session-abc")
	if req.AgentsSpec == nil || len(req.AgentsSpec.AgentSpecs) == 0 {
		t.Fatalf("expected agentsSpec for deep research")
	}
	if req.AgentsSpec.AgentSpecs[0].AgentID != "deep_research" {
		t.Errorf("expected agentId 'deep_research', got '%s'", req.AgentsSpec.AgentSpecs[0].AgentID)
	}
	if req.ToolsSpec == nil || req.ToolsSpec.WebGroundingSpec == nil {
		t.Fatalf("expected webGroundingSpec in toolsSpec for deep research")
	}
	if req.SessionInfo == nil || req.SessionInfo.Session != "session-abc" {
		t.Errorf("expected session 'session-abc', got '%v'", req.SessionInfo)
	}
}

func TestExecuteStreamAssist_Success(t *testing.T) {
	mockResponse := []StreamAssistChunk{
		{
			Answer: AssistAnswer{
				State: "IN_PROGRESS",
				Replies: []ReplyPart{
					{
						GroundedContent: GroundedContent{
							Content: ContentPart{
								Text:    "Thinking...",
								Thought: true,
							},
						},
					},
				},
			},
		},
		{
			Answer: AssistAnswer{
				State: "SUCCEEDED",
				Replies: []ReplyPart{
					{
						GroundedContent: GroundedContent{
							Content: ContentPart{
								Text:    "Here is the SharePoint policy summary.",
								Thought: false,
							},
						},
						Citations: []interface{}{"doc1.pdf"},
					},
				},
			},
			SessionInfo: SessionInfo{Session: "projects/p/locations/l/sessions/sess-123"},
		},
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if auth := r.Header.Get("Authorization"); !strings.HasPrefix(auth, "Bearer ") {
			http.Error(w, "missing bearer token", http.StatusUnauthorized)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		_ = json.NewEncoder(w).Encode(mockResponse)
	}))
	defer server.Close()

	client := NewStreamAssistClient("dummy-token", 5*time.Second)
	req := StreamAssistRequest{Query: QueryText{Text: "Test"}}

	ctx := context.Background()
	chunks, statusCode, err := client.ExecuteStreamAssistWithURL(ctx, server.URL, req)
	if err != nil {
		t.Fatalf("expected no error, got: %v", err)
	}
	if statusCode != 200 {
		t.Errorf("expected 200, got %d", statusCode)
	}
	if len(chunks) != 2 {
		t.Fatalf("expected 2 chunks, got %d", len(chunks))
	}
	if chunks[1].SessionInfo.Session != "projects/p/locations/l/sessions/sess-123" {
		t.Errorf("expected session preserved, got '%s'", chunks[1].SessionInfo.Session)
	}
}
