package main

import (
	"context"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"
)

func TestBuildJudgePrompt(t *testing.T) {
	tc := TestCase{
		ID:               "test_sharepoint_01",
		Subsystem:        "sharepoint",
		Query:            "Find the workplace policy document in our SharePoint site.",
		ExpectedBehavior: "Must locate relevant policy document",
		SemanticContract: "Must present actual workplace policy documents, not a setup guide.",
	}
	resp := "Here is the AI Workplace Policy: https://sharepoint.com/doc.docx"

	prompt := BuildJudgePrompt(tc, resp)
	if !strings.Contains(prompt, tc.Query) {
		t.Errorf("prompt missing query: %s", prompt)
	}
	if !strings.Contains(prompt, tc.SemanticContract) {
		t.Errorf("prompt missing semantic contract: %s", prompt)
	}
	if !strings.Contains(prompt, resp) {
		t.Errorf("prompt missing response text: %s", prompt)
	}
}

func TestVertexAIJudgeClient_Success(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.Header.Get("Authorization") != "Bearer test-token" {
			http.Error(w, "Unauthorized", http.StatusUnauthorized)
			return
		}

		respJSON := `{
			"candidates": [
				{
					"content": {
						"parts": [
							{
								"text": "{\"fulfilled\": true, \"score\": 5, \"reasoning\": \"Successfully retrieved SharePoint policy document with direct link.\", \"detected_refusal_or_unconnected\": false}"
							}
						]
					}
				}
			]
		}`
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, respJSON)
	}))
	defer server.Close()

	client := &VertexAIJudgeClient{
		ProjectID:  "test-project",
		Location:   "us-central1",
		ModelName:  "gemini-2.5-flash",
		Token:      "test-token",
		HTTPClient: server.Client(),
		Endpoint:   server.URL,
	}

	tc := TestCase{
		ID:               "smoke_01",
		Query:            "Find policy",
		SemanticContract: "Must return policy document",
	}

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	eval, err := client.EvaluateResponse(ctx, tc, "Found policy document: https://sharepoint/doc.pdf")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !eval.Fulfilled {
		t.Errorf("expected fulfilled true, got false")
	}
	if eval.Score != 5 {
		t.Errorf("expected score 5, got %d", eval.Score)
	}
	if eval.DetectedRefusalOrUnconnected {
		t.Errorf("expected refusal false, got true")
	}
	if eval.JudgeModel != "gemini-2.5-flash" {
		t.Errorf("expected model gemini-2.5-flash, got %s", eval.JudgeModel)
	}
}

func TestVertexAIJudgeClient_RefusalDetected(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		respJSON := `{
			"candidates": [
				{
					"content": {
						"parts": [
							{
								"text": "{\"fulfilled\": false, \"score\": 1, \"reasoning\": \"Response is a refusal message explaining how to connect SharePoint in Entra ID rather than retrieving document.\", \"detected_refusal_or_unconnected\": true}"
							}
						]
					}
				}
			]
		}`
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, respJSON)
	}))
	defer server.Close()

	client := &VertexAIJudgeClient{
		ProjectID:  "test-project",
		Location:   "us-central1",
		ModelName:  "gemini-2.5-flash",
		Token:      "test-token",
		HTTPClient: server.Client(),
		Endpoint:   server.URL,
	}

	tc := TestCase{
		ID:               "smoke_sharepoint",
		Query:            "Find policy document",
		SemanticContract: "Must return policy document, not setup instructions",
	}

	eval, err := client.EvaluateResponse(context.Background(), tc, "I do not have access. Please register SharePoint in Entra ID.")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if eval.Fulfilled {
		t.Errorf("expected fulfilled false, got true")
	}
	if eval.Score != 1 {
		t.Errorf("expected score 1, got %d", eval.Score)
	}
	if !eval.DetectedRefusalOrUnconnected {
		t.Errorf("expected detected refusal true, got false")
	}
}

func TestVertexAIJudgeClient_MarkdownJSONCleaned(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		respJSON := "{\"candidates\": [{\"content\": {\"parts\": [{\"text\": \"```json\\n{\\n  \\\"fulfilled\\\": true,\\n  \\\"score\\\": 4,\\n  \\\"reasoning\\\": \\\"Good synthesis\\\",\\n  \\\"detected_refusal_or_unconnected\\\": false\\n}\\n```\"}]}}]}"
		w.Header().Set("Content-Type", "application/json")
		fmt.Fprint(w, respJSON)
	}))
	defer server.Close()

	client := &VertexAIJudgeClient{
		ProjectID:  "test-project",
		Location:   "us-central1",
		ModelName:  "gemini-2.5-flash",
		Token:      "test-token",
		HTTPClient: server.Client(),
		Endpoint:   server.URL,
	}

	eval, err := client.EvaluateResponse(context.Background(), TestCase{}, "Sample response")
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	if !eval.Fulfilled || eval.Score != 4 {
		t.Errorf("failed to parse markdown-fenced JSON: %+v", eval)
	}
}
