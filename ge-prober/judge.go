package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"strings"
	"time"
)

// JudgeClient defines the interface for evaluating model responses semantically.
type JudgeClient interface {
	EvaluateResponse(ctx context.Context, testCase TestCase, responseText string) (*SemanticEvaluation, error)
}

// VertexAIJudgeClient evaluates responses using Vertex AI generateContent REST API.
type VertexAIJudgeClient struct {
	ProjectID  string
	Location   string
	ModelName  string
	Token      string
	HTTPClient *http.Client
	Endpoint   string // Optional override for testing
}

// NewVertexAIJudgeClient creates a new Vertex AI judge client.
func NewVertexAIJudgeClient(projectID, location, modelName, token string, timeout time.Duration) *VertexAIJudgeClient {
	if location == "" || location == "global" {
		location = "us-central1" // Vertex AI standard region for Generative AI endpoints
	}
	if modelName == "" {
		modelName = "gemini-2.5-flash"
	}
	if timeout <= 0 {
		timeout = 45 * time.Second
	}
	return &VertexAIJudgeClient{
		ProjectID:  projectID,
		Location:   location,
		ModelName:  modelName,
		Token:      token,
		HTTPClient: &http.Client{Timeout: timeout},
	}
}

// BuildJudgePrompt constructs the evaluation prompt for Vertex AI.
func BuildJudgePrompt(testCase TestCase, responseText string) string {
	contract := testCase.SemanticContract
	if contract == "" {
		contract = testCase.ExpectedBehavior
	}

	return fmt.Sprintf(`You are an expert AI evaluator and quality judge for enterprise AI applications.
Evaluate whether the following AI system response satisfies the required semantic contract and fulfills the user's objective.

[EVALUATION CONTRACT]
Test Case ID: %s
Subsystem: %s
User Query: "%s"
Expected Behavior: %s
Semantic Contract: %s

[ACTUAL RESPONSE UNDER EVALUATION]
%s

[INSTRUCTIONS]
1. Assess whether the response fulfills the user's objective and satisfies the Semantic Contract.
2. If the response is a refusal, an error explanation, a setup/installation guide instead of data retrieval, or missing required knowledge, mark "fulfilled": false and "detected_refusal_or_unconnected": true.
3. Assign a score from 1 to 5:
   - 5: Perfectly fulfilled, accurate, grounded, and meets all criteria.
   - 4: Substantially fulfilled with minor formatting or minor omissions.
   - 3: Partially fulfilled or incomplete.
   - 2: Poorly fulfilled or partially ungrounded.
   - 1: Unfulfilled, refusal, error, or completely ungrounded.
4. Output STRICT JSON adhering to this exact schema (no surrounding markdown code fences, only valid JSON):
{
  "fulfilled": true,
  "score": 5,
  "reasoning": "Concise 1-2 sentence explanation of the score and verdict",
  "detected_refusal_or_unconnected": false
}`,
		testCase.ID,
		testCase.Subsystem,
		testCase.Query,
		testCase.ExpectedBehavior,
		contract,
		responseText,
	)
}

// EvaluateResponse calls Vertex AI generateContent and extracts the SemanticEvaluation.
func (c *VertexAIJudgeClient) EvaluateResponse(ctx context.Context, testCase TestCase, responseText string) (*SemanticEvaluation, error) {
	startTime := time.Now()

	prompt := BuildJudgePrompt(testCase, responseText)

	reqPayload := map[string]interface{}{
		"contents": []map[string]interface{}{
			{
				"role": "user",
				"parts": []map[string]interface{}{
					{"text": prompt},
				},
			},
		},
		"generationConfig": map[string]interface{}{
			"temperature":     0.0,
			"responseMimeType": "application/json",
		},
	}

	bodyBytes, err := json.Marshal(reqPayload)
	if err != nil {
		return nil, fmt.Errorf("failed to marshal judge request: %w", err)
	}

	url := c.Endpoint
	if url == "" {
		url = fmt.Sprintf("https://%s-aiplatform.googleapis.com/v1/projects/%s/locations/%s/publishers/google/models/%s:generateContent",
			c.Location, c.ProjectID, c.Location, c.ModelName)
	}

	req, err := http.NewRequestWithContext(ctx, "POST", url, bytes.NewReader(bodyBytes))
	if err != nil {
		return nil, fmt.Errorf("failed to create judge request: %w", err)
	}

	req.Header.Set("Authorization", "Bearer "+c.Token)
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.HTTPClient.Do(req)
	if err != nil {
		return nil, fmt.Errorf("judge HTTP request failed: %w", err)
	}
	defer resp.Body.Close()

	respBytes, err := io.ReadAll(resp.Body)
	if err != nil {
		return nil, fmt.Errorf("failed to read judge response: %w", err)
	}

	if resp.StatusCode != http.StatusOK {
		return nil, fmt.Errorf("judge API returned HTTP %d: %s", resp.StatusCode, string(respBytes))
	}

	// Parse Vertex AI generateContent response
	var vertexResp struct {
		Candidates []struct {
			Content struct {
				Parts []struct {
					Text string `json:"text"`
				} `json:"parts"`
			} `json:"content"`
		} `json:"candidates"`
	}

	if err := json.Unmarshal(respBytes, &vertexResp); err != nil {
		return nil, fmt.Errorf("failed to unmarshal Vertex AI response envelope: %w", err)
	}

	if len(vertexResp.Candidates) == 0 || len(vertexResp.Candidates[0].Content.Parts) == 0 {
		return nil, fmt.Errorf("no candidate content returned from judge model")
	}

	rawJudgeText := vertexResp.Candidates[0].Content.Parts[0].Text

	// Clean any markdown code blocks
	cleanJSON := cleanJSONResponse(rawJudgeText)

	var evalResult struct {
		Fulfilled                    bool   `json:"fulfilled"`
		Score                        int    `json:"score"`
		Reasoning                    string `json:"reasoning"`
		DetectedRefusalOrUnconnected bool   `json:"detected_refusal_or_unconnected"`
	}

	if err := json.Unmarshal([]byte(cleanJSON), &evalResult); err != nil {
		return nil, fmt.Errorf("failed to parse judge evaluation JSON (%s): %w", cleanJSON, err)
	}

	latencyMs := float64(time.Since(startTime).Microseconds()) / 1000.0

	return &SemanticEvaluation{
		JudgeModel:                   c.ModelName,
		Fulfilled:                    evalResult.Fulfilled,
		Score:                        evalResult.Score,
		Reasoning:                    evalResult.Reasoning,
		DetectedRefusalOrUnconnected: evalResult.DetectedRefusalOrUnconnected,
		EvaluationLatencyMs:          latencyMs,
	}, nil
}

// cleanJSONResponse strips markdown code fences if present.
func cleanJSONResponse(s string) string {
	trimmed := strings.TrimSpace(s)
	if strings.HasPrefix(trimmed, "```json") {
		trimmed = strings.TrimPrefix(trimmed, "```json")
		trimmed = strings.TrimSuffix(trimmed, "```")
	} else if strings.HasPrefix(trimmed, "```") {
		trimmed = strings.TrimPrefix(trimmed, "```")
		trimmed = strings.TrimSuffix(trimmed, "```")
	}
	return strings.TrimSpace(trimmed)
}
