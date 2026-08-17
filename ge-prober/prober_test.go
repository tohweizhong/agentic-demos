package main

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"sync/atomic"
	"testing"
	"time"
)

func TestEvaluateAssertions(t *testing.T) {
	tc := TestCase{
		Assertions: Assertions{
			MustContainKeywords: []string{"policy", "SharePoint"},
			ForbiddenErrors:     []string{"401", "403", "500", "503"},
			MustHaveCitations:   true,
		},
	}

	// 1. Success case
	passed, reasons := EvaluateAssertions(tc, 200, "Here is the SharePoint workplace policy document.", true, "")
	if !passed {
		t.Errorf("expected assertions to pass, failed with: %v", reasons)
	}

	// 2. Missing keyword
	passed, reasons = EvaluateAssertions(tc, 200, "Here is a general document.", true, "")
	if passed {
		t.Errorf("expected failure due to missing keywords, but passed")
	}

	// 3. Forbidden error code in error message
	passed, reasons = EvaluateAssertions(tc, 503, "", false, "HTTP 503: Service Unavailable")
	if passed {
		t.Errorf("expected failure due to HTTP 503, but passed")
	}
}

func TestEvaluateSLO(t *testing.T) {
	slo := SLOTargets{
		MaxTTFTMs: 3000.0,
		MaxTTLT:   12000.0,
	}

	// Within SLO
	passed, reasons := EvaluateSLO(slo, 1500.0, 8000.0)
	if !passed {
		t.Errorf("expected SLO pass, failed with: %v", reasons)
	}

	// TTFT breach
	passed, reasons = EvaluateSLO(slo, 4500.0, 8000.0)
	if passed {
		t.Errorf("expected TTFT breach, but passed")
	}

	// TTLT breach
	passed, reasons = EvaluateSLO(slo, 1500.0, 15000.0)
	if passed {
		t.Errorf("expected TTLT breach, but passed")
	}
}

func TestRunProberSuite_Concurrent(t *testing.T) {
	var requestCount int32

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		atomic.AddInt32(&requestCount, 1)
		time.Sleep(10 * time.Millisecond)

		chunks := []StreamAssistChunk{
			{
				Answer: AssistAnswer{
					State: "SUCCEEDED",
					Replies: []ReplyPart{
						{
							GroundedContent: GroundedContent{
								Content: ContentPart{
									Text: "Document found with policy.",
								},
							},
							Citations: []interface{}{"cite-1"},
						},
					},
				},
			},
		}

		w.Header().Set("Content-Type", "application/json")
		_ = json.NewEncoder(w).Encode(chunks)
	}))
	defer server.Close()

	cases := []TestCase{
		{
			ID:            "case-1",
			Title:         "Test 1",
			Subsystem:     "sharepoint",
			Query:         "Find policy",
			GroundingType: "vertex_ai_search",
			SLOTargets:    SLOTargets{MaxTTFTMs: 5000, MaxTTLT: 10000},
			Assertions:    Assertions{MustContainKeywords: []string{"policy"}},
		},
		{
			ID:            "case-2",
			Title:         "Test 2",
			Subsystem:     "web",
			Query:         "Find policy",
			GroundingType: "web_search",
			SLOTargets:    SLOTargets{MaxTTFTMs: 5000, MaxTTLT: 10000},
			Assertions:    Assertions{MustContainKeywords: []string{"policy"}},
		},
	}

	cfg := &Config{
		ProjectID:      "test-proj",
		Location:       "sg",
		EngineID:       "test-engine",
		MaxConcurrency: 2,
		TimeoutSeconds: 5,
	}

	client := NewStreamAssistClient("test-token", 5*time.Second)
	ctx := context.Background()

	report := RunProberSuiteWithURL(ctx, server.URL, cases, cfg, client)
	if report.TotalProbes != 2 {
		t.Errorf("expected 2 total probes, got %d", report.TotalProbes)
	}
	if report.FunctionalPassed != 2 {
		t.Errorf("expected 2 functional passes, got %d", report.FunctionalPassed)
	}
	if atomic.LoadInt32(&requestCount) != 2 {
		t.Errorf("expected 2 HTTP requests dispatched, got %d", requestCount)
	}
}
