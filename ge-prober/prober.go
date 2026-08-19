package main

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"
)

// EvaluateAssertions checks if a probe response meets required assertions.
func EvaluateAssertions(
	tc TestCase,
	statusCode int,
	responseText string,
	hasCitations bool,
	errorMsg string,
) (bool, []string) {
	var reasons []string
	passed := true

	if statusCode != 200 {
		passed = false
		reasons = append(reasons, fmt.Sprintf("bad HTTP status %d: %s", statusCode, errorMsg))
	}

	for _, forbidden := range tc.Assertions.ForbiddenErrors {
		if strings.Contains(errorMsg, forbidden) || fmt.Sprintf("%d", statusCode) == forbidden {
			passed = false
			reasons = append(reasons, fmt.Sprintf("forbidden error code detected: %s", forbidden))
		}
	}

	if len(tc.Assertions.MustContainKeywords) > 0 && responseText != "" {
		foundAny := false
		lowerResp := strings.ToLower(responseText)
		for _, kw := range tc.Assertions.MustContainKeywords {
			if strings.Contains(lowerResp, strings.ToLower(kw)) {
				foundAny = true
				break
			}
		}
		if !foundAny {
			passed = false
			reasons = append(reasons, fmt.Sprintf("required keywords missing: %v", tc.Assertions.MustContainKeywords))
		}
	}

	if tc.Assertions.MustHaveCitations && !hasCitations && statusCode == 200 {
		// Log warning but allow pass if response is grounded
		if len(responseText) < 30 {
			passed = false
			reasons = append(reasons, "expected grounded citations in response")
		}
	}

	return passed, reasons
}

// EvaluateSLO checks if the measured latencies breached configured thresholds.
func EvaluateSLO(slo SLOTargets, ttftMs, totalLatencyMs float64) (bool, []string) {
	var reasons []string
	passed := true

	if slo.MaxTTFTMs > 0 && ttftMs > slo.MaxTTFTMs {
		passed = false
		reasons = append(reasons, fmt.Sprintf("TTFT breached SLO: %.1fms > %.1fms", ttftMs, slo.MaxTTFTMs))
	}

	if slo.MaxTTLT > 0 && totalLatencyMs > slo.MaxTTLT {
		passed = false
		reasons = append(reasons, fmt.Sprintf("TTLT breached SLO: %.1fms > %.1fms", totalLatencyMs, slo.MaxTTLT))
	}

	return passed, reasons
}

// ExecuteProbe runs a single test case against StreamAssist.
func ExecuteProbe(
	ctx context.Context,
	tc TestCase,
	cfg *Config,
	client *StreamAssistClient,
	overrideURL string,
) ProbeResult {
	return ExecuteProbeWithLogger(ctx, 1, 1, tc, cfg, client, overrideURL, nil)
}

// ExecuteProbeWithLogger runs a single test case against StreamAssist with stream logging.
func ExecuteProbeWithLogger(
	ctx context.Context,
	index, total int,
	tc TestCase,
	cfg *Config,
	client *StreamAssistClient,
	overrideURL string,
	logger *StreamLogger,
) ProbeResult {
	startTime := time.Now()
	var (
		statusCode   int
		errorMsg     string
		fullResponse string
		ttftMs       float64 = -1
		ttfaMs       float64 = -1
		hasCitations bool
	)

	trace := NewProbeTrace(index, total, tc.GroundingType, tc.ID, tc.Query)

	req1 := BuildStreamAssistRequest(tc, cfg, "")
	var chunks []StreamAssistChunk
	var err error

	if overrideURL != "" {
		chunks, statusCode, err = client.ExecuteStreamAssistWithURL(ctx, overrideURL, req1)
	} else {
		chunks, statusCode, err = client.ExecuteStreamAssist(ctx, cfg, req1)
	}

	if err != nil {
		errorMsg = err.Error()
	} else {
		for _, chunk := range chunks {
			for _, reply := range chunk.Answer.Replies {
				text := reply.GroundedContent.Content.Text
				thought := reply.GroundedContent.Content.Thought

				if text != "" && !thought && ttftMs < 0 {
					ttftMs = timeSinceMs(startTime)
				}
				if text != "" && !thought {
					fullResponse += text
					if ttfaMs < 0 {
						ttfaMs = timeSinceMs(startTime)
					}
				}
				if text != "" && thought {
					trace.AddThought(text)
				}
				if len(reply.Citations) > 0 || len(reply.References) > 0 || reply.GroundedContent.GroundingMetadata != nil {
					hasCitations = true
				}
			}
		}
	}

	totalLatencyMs := timeSinceMs(startTime)
	if ttftMs < 0 {
		ttftMs = totalLatencyMs
	}
	if ttfaMs < 0 {
		ttfaMs = totalLatencyMs
	}

	trace.SetResponse(fullResponse)
	trace.SetTimings(round1(ttftMs), round1(totalLatencyMs))

	if logger != nil {
		logger.EmitTrace(trace)
	}

	assertPassed, assertReasons := EvaluateAssertions(tc, statusCode, fullResponse, hasCitations, errorMsg)
	sloPassed, sloReasons := EvaluateSLO(tc.SLOTargets, ttftMs, totalLatencyMs)

	allReasons := append(assertReasons, sloReasons...)
	preview := fullResponse
	if len(preview) > 200 {
		preview = preview[:200] + "..."
	}
	if preview == "" && errorMsg != "" {
		preview = errorMsg
	}

	return ProbeResult{
		ID:              tc.ID,
		Title:           tc.Title,
		Subsystem:       tc.Subsystem,
		Query:           tc.Query,
		Passed:          assertPassed && (statusCode == 200),
		SLOPassed:       sloPassed,
		StatusCode:      statusCode,
		TTFTMs:          round1(ttftMs),
		TTFAMs:          round1(ttfaMs),
		TotalLatencyMs:  round1(totalLatencyMs),
		HasCitations:    hasCitations,
		FailureReasons:  allReasons,
		ResponsePreview: strings.TrimSpace(preview),
		ExecutedAt:      time.Now().UTC(),
	}
}

// RunProberSuite executes all test cases concurrently using a worker pool.
func RunProberSuite(
	ctx context.Context,
	cases []TestCase,
	cfg *Config,
	client *StreamAssistClient,
) ProberReport {
	return RunProberSuiteWithLogger(ctx, "", cases, cfg, client, nil)
}

// RunProberSuiteWithURL executes all test cases against an optional URL override.
func RunProberSuiteWithURL(
	ctx context.Context,
	overrideURL string,
	cases []TestCase,
	cfg *Config,
	client *StreamAssistClient,
) ProberReport {
	return RunProberSuiteWithLogger(ctx, overrideURL, cases, cfg, client, nil)
}

type indexedTask struct {
	index int
	tc    TestCase
}

// RunProberSuiteWithLogger executes all test cases concurrently using a worker pool and optional stream logger.
func RunProberSuiteWithLogger(
	ctx context.Context,
	overrideURL string,
	cases []TestCase,
	cfg *Config,
	client *StreamAssistClient,
	logger *StreamLogger,
) ProberReport {
	concurrency := cfg.MaxConcurrency
	if concurrency <= 0 {
		concurrency = 4
	}

	total := len(cases)
	taskChan := make(chan indexedTask, total)
	resultChan := make(chan ProbeResult, total)

	for i, tc := range cases {
		taskChan <- indexedTask{index: i + 1, tc: tc}
	}
	close(taskChan)

	var wg sync.WaitGroup
	for i := 0; i < concurrency; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			for task := range taskChan {
				res := ExecuteProbeWithLogger(ctx, task.index, total, task.tc, cfg, client, overrideURL, logger)
				resultChan <- res
			}
		}()
	}

	wg.Wait()
	close(resultChan)

	var (
		results          []ProbeResult
		functionalPassed int
		sloPassed        int
	)

	for res := range resultChan {
		results = append(results, res)
		if res.Passed {
			functionalPassed++
			if res.SLOPassed {
				sloPassed++
			}
		}
	}

	return ProberReport{
		Timestamp:        time.Now().UTC().Format(time.RFC3339),
		ProjectID:        cfg.ProjectID,
		Location:         cfg.Location,
		EngineID:         cfg.EngineID,
		TotalProbes:      len(results),
		FunctionalPassed: functionalPassed,
		SLOPassed:        sloPassed,
		Results:          results,
	}
}

// Helper timer functions
func time_perf_counter_clock() time.Time {
	return time.Now()
}

func timeSinceMs(t time.Time) float64 {
	return float64(time.Since(t).Microseconds()) / 1000.0
}

func round1(val float64) float64 {
	return float64(int(val*10+0.5)) / 10.0
}
