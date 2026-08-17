package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// StreamAssistClient handles HTTP communication with Discovery Engine StreamAssist.
type StreamAssistClient struct {
	Token      string
	HTTPClient *http.Client
}

// NewStreamAssistClient initializes a new StreamAssist client.
func NewStreamAssistClient(token string, timeout time.Duration) *StreamAssistClient {
	return &StreamAssistClient{
		Token: token,
		HTTPClient: &http.Client{
			Timeout: timeout,
		},
	}
}

// BuildStreamAssistURL constructs the regional REST endpoint for StreamAssist.
func BuildStreamAssistURL(location, projectID, engineID, assistantID string) string {
	if assistantID == "" {
		assistantID = "default_assistant"
	}
	host := "discoveryengine.googleapis.com"
	if location != "global" && location != "" {
		host = fmt.Sprintf("%s-discoveryengine.googleapis.com", location)
	}
	return fmt.Sprintf(
		"https://%s/v1alpha/projects/%s/locations/%s/collections/default_collection/engines/%s/assistants/%s:streamAssist",
		host, projectID, location, engineID, assistantID,
	)
}

// BuildStreamAssistRequest constructs the appropriate JSON payload for a test case.
func BuildStreamAssistRequest(tc TestCase, cfg *Config, sessionID string) StreamAssistRequest {
	req := StreamAssistRequest{
		Query: QueryText{Text: tc.Query},
	}

	if sessionID != "" {
		req.SessionInfo = &SessionInfo{Session: sessionID}
	}

	switch tc.GroundingType {
	case "vertex_ai_search":
		if len(cfg.DataStoreIDs) > 0 {
			var dsSpecs []DataStoreSpec
			for _, dsID := range cfg.DataStoreIDs {
				dsPath := fmt.Sprintf(
					"projects/%s/locations/%s/collections/default_collection/dataStores/%s",
					cfg.ProjectID, cfg.Location, dsID,
				)
				dsSpecs = append(dsSpecs, DataStoreSpec{DataStore: dsPath})
			}
			req.ToolsSpec = &ToolsSpec{
				VertexAISearchSpec: &VertexAISearchSpec{
					DataStoreSpecs: dsSpecs,
				},
			}
		}
	case "web_search":
		req.ToolsSpec = &ToolsSpec{
			WebGroundingSpec: map[string]interface{}{},
		}
	case "deep_research_agent":
		req.AgentsSpec = &AgentsSpec{
			AgentSpecs: []AgentSpec{
				{AgentID: "deep_research"},
			},
		}
		req.ToolsSpec = &ToolsSpec{
			WebGroundingSpec: map[string]interface{}{},
		}
	case "gemini_notebook", "notebooklm":
		// Direct query against notebook knowledge base without injecting external data stores
	}

	return req
}

// ExecuteStreamAssist dispatches the StreamAssist request to Discovery Engine.
func (c *StreamAssistClient) ExecuteStreamAssist(
	ctx context.Context,
	cfg *Config,
	req StreamAssistRequest,
) ([]StreamAssistChunk, int, error) {
	url := BuildStreamAssistURL(cfg.Location, cfg.ProjectID, cfg.EngineID, cfg.AssistantID)
	return c.ExecuteStreamAssistWithURL(ctx, url, req)
}

// ExecuteStreamAssistWithURL sends HTTP POST to a specific URL (useful for testing).
func (c *StreamAssistClient) ExecuteStreamAssistWithURL(
	ctx context.Context,
	url string,
	req StreamAssistRequest,
) ([]StreamAssistChunk, int, error) {
	bodyBytes, err := json.Marshal(req)
	if err != nil {
		return nil, 0, fmt.Errorf("failed to marshal request body: %w", err)
	}

	httpReq, err := http.NewRequestWithContext(ctx, http.MethodPost, url, bytes.NewReader(bodyBytes))
	if err != nil {
		return nil, 0, fmt.Errorf("failed to create http request: %w", err)
	}

	httpReq.Header.Set("Content-Type", "application/json")
	if c.Token != "" {
		httpReq.Header.Set("Authorization", "Bearer "+c.Token)
	}

	res, err := c.HTTPClient.Do(httpReq)
	if err != nil {
		return nil, 0, fmt.Errorf("streamAssist request failed: %w", err)
	}
	defer res.Body.Close()

	respBytes, err := io.ReadAll(res.Body)
	if err != nil {
		return nil, res.StatusCode, fmt.Errorf("failed to read response body: %w", err)
	}

	if res.StatusCode != http.StatusOK {
		return nil, res.StatusCode, fmt.Errorf("HTTP %d: %s", res.StatusCode, string(respBytes[:min(len(respBytes), 300)]))
	}

	var chunks []StreamAssistChunk
	if err := json.Unmarshal(respBytes, &chunks); err != nil {
		return nil, res.StatusCode, fmt.Errorf("failed to decode stream response: %w", err)
	}

	return chunks, res.StatusCode, nil
}

func min(a, b int) int {
	if a < b {
		return a
	}
	return b
}
