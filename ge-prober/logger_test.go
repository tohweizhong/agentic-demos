package main

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"
)

func TestFormatProbeHeader(t *testing.T) {
	header := FormatProbeHeader(4, 4, "sharepoint", "sharepoint_01")
	expected := "[4/4] 🔎 [sharepoint] sharepoint_01"
	if header != expected {
		t.Fatalf("expected %q, got %q", expected, header)
	}
}

func TestFormatQuery(t *testing.T) {
	queryLine := FormatQuery("Search for files about FormSG in our SharePoint site.")
	expected := "📜 Query: \"Search for files about FormSG in our SharePoint site.\""
	if queryLine != expected {
		t.Fatalf("expected %q, got %q", expected, queryLine)
	}
}

func TestFormatStreamDone(t *testing.T) {
	banner := FormatStreamDone(14027.84, 20015.12)
	expected := "✅ Stream Done (TTFT: 14027.8 ms | Total: 20015.1 ms)"
	if banner != expected {
		t.Fatalf("expected %q, got %q", expected, banner)
	}
}

func TestFormatResponseLines(t *testing.T) {
	rawResponse := `I found several documents regarding **FormSG** on your SharePoint site. All of these...

### 📌 Primary Document
* **[FormSG.pdf](https://example.com/form.pdf)**
* **Description:** This is the main product page document for FormSG.`

	lines := FormatResponseLines(rawResponse)
	if len(lines) != 4 {
		t.Fatalf("expected 4 formatted lines, got %d: %v", len(lines), lines)
	}
	if lines[0] != "I found several documents regarding **FormSG** on your SharePoint site. All of these..." {
		t.Errorf("unexpected first line: %q", lines[0])
	}
	if lines[1] != "### 📌 Primary Document" {
		t.Errorf("unexpected second line: %q", lines[1])
	}
	if lines[2] != "* **[FormSG.pdf](https://example.com/form.pdf)**" {
		t.Errorf("unexpected third line: %q", lines[2])
	}
}

func TestProbeTraceBuffer_Emit(t *testing.T) {
	var buf bytes.Buffer
	trace := NewProbeTrace(1, 4, "web", "web_01", "What is Vertex AI?")
	trace.AddThought("Searching the web for Vertex AI overview...")
	trace.SetResponse("Vertex AI is a unified ML platform on Google Cloud.\n\n### Features\n* AutoML\n* Custom training")
	trace.SetTimings(1234.5, 4567.8)

	trace.EmitTo(&buf)
	output := buf.String()

	if !strings.Contains(output, "[1/4] 🔎 [web] web_01") {
		t.Errorf("missing probe header in output: %s", output)
	}
	if !strings.Contains(output, "📜 Query: \"What is Vertex AI?\"") {
		t.Errorf("missing query in output: %s", output)
	}
	if !strings.Contains(output, "💭 Thought:") || !strings.Contains(output, "Searching the web for Vertex AI overview...") {
		t.Errorf("missing thought block in output: %s", output)
	}
	if !strings.Contains(output, "💬 Response:") {
		t.Errorf("missing response header in output: %s", output)
	}
	if !strings.Contains(output, "Vertex AI is a unified ML platform on Google Cloud.") {
		t.Errorf("missing response text in output: %s", output)
	}
	if !strings.Contains(output, "✅ Stream Done (TTFT: 1234.5 ms | Total: 4567.8 ms)") {
		t.Errorf("missing stream done banner in output: %s", output)
	}
}

func TestRunProberSuiteWithLogger_VerboseOutput(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		chunks := []StreamAssistChunk{
			{
				Answer: AssistAnswer{
					State: "SUCCEEDED",
					Replies: []ReplyPart{
						{
							GroundedContent: GroundedContent{
								Content: ContentPart{
									Text:    "Thinking about Singapore FormSG...",
									Thought: true,
								},
							},
						},
						{
							GroundedContent: GroundedContent{
								Content: ContentPart{
									Text: "I found several documents regarding **FormSG**.\n\n### 📌 Primary Document\n* **[FormSG.pdf](https://example.com/forms.pdf)**",
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
			ID:            "sharepoint_01",
			Title:         "SharePoint Test",
			Subsystem:     "sharepoint",
			Query:         "Search for files about FormSG in our SharePoint site.",
			GroundingType: "sharepoint",
			SLOTargets:    SLOTargets{MaxTTFTMs: 5000, MaxTTLT: 10000},
			Assertions:    Assertions{MustContainKeywords: []string{"FormSG"}},
		},
	}

	cfg := &Config{
		ProjectID:      "test-proj",
		Location:       "global",
		EngineID:       "test-engine",
		MaxConcurrency: 1,
		TimeoutSeconds: 5,
	}

	client := NewStreamAssistClient("test-token", 5*time.Second)
	ctx := context.Background()

	var buf bytes.Buffer
	logger := NewStreamLogger(&buf, true)

	report := RunProberSuiteWithLogger(ctx, server.URL, cases, cfg, client, logger)
	if report.FunctionalPassed != 1 {
		t.Fatalf("expected 1 pass, got %d", report.FunctionalPassed)
	}

	out := buf.String()
	if !strings.Contains(out, "[1/1] 🔎 [sharepoint] sharepoint_01") {
		t.Errorf("missing probe header in verbose log: %s", out)
	}
	if !strings.Contains(out, "📜 Query: \"Search for files about FormSG in our SharePoint site.\"") {
		t.Errorf("missing query in verbose log: %s", out)
	}
	if !strings.Contains(out, "💭 Thought:\nThinking about Singapore FormSG...") {
		t.Errorf("missing thought in verbose log: %s", out)
	}
	if !strings.Contains(out, "💬 Response:") {
		t.Errorf("missing response header in verbose log: %s", out)
	}
	if !strings.Contains(out, "### 📌 Primary Document") {
		t.Errorf("missing formatted response markdown in verbose log: %s", out)
	}
	if !strings.Contains(out, "✅ Stream Done (TTFT:") {
		t.Errorf("missing stream done banner in verbose log: %s", out)
	}
}

func TestStreamLogger_ConcurrencySafety(t *testing.T) {
	var buf bytes.Buffer
	logger := NewStreamLogger(&buf, true)

	var wg sync.WaitGroup
	for i := 1; i <= 10; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			trace := NewProbeTrace(idx, 10, "subsystem", fmt.Sprintf("case_%d", idx), fmt.Sprintf("Query %d", idx))
			trace.SetResponse(fmt.Sprintf("Line 1 from %d\nLine 2 from %d", idx, idx))
			trace.SetTimings(float64(idx*100), float64(idx*200))
			logger.EmitTrace(trace)
		}(i)
	}
	wg.Wait()

	out := buf.String()
	for i := 1; i <= 10; i++ {
		expectedHeader := fmt.Sprintf("[%d/10] 🔎 [subsystem] case_%d", i, i)
		if !strings.Contains(out, expectedHeader) {
			t.Errorf("missing header for probe %d", i)
		}
	}
}

func TestFormatExecutionSummary(t *testing.T) {
	report := ProberReport{
		TotalProbes:      4,
		FunctionalPassed: 4,
		SLOPassed:        4,
	}
	summary := FormatExecutionSummary(report, 20.015, "smoke_prober_results.json")
	if !strings.Contains(summary, "TEST SUITE EXECUTION SUMMARY") {
		t.Errorf("missing summary banner: %s", summary)
	}
	if !strings.Contains(summary, "Total Test Cases") || !strings.Contains(summary, "4") {
		t.Errorf("missing total count in summary: %s", summary)
	}
	if !strings.Contains(summary, "100.0%") {
		t.Errorf("missing pass percentage: %s", summary)
	}
}
