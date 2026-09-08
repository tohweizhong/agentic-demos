//go:build e2e

package main

import (
	"bytes"
	"context"
	"encoding/json"
	"testing"
	"time"
)

func TestLiveE2E_FullProberSuite(t *testing.T) {
	// 1. Resolve configuration
	cfg, err := ResolveConfig("config.json", CLIFlagOverrides{})
	if err != nil {
		t.Skipf("skipping live E2E test: configuration cannot be loaded: %v", err)
	}

	if cfg.ProjectID == "" || cfg.EngineID == "" {
		t.Skip("skipping live E2E test: GCP_PROJECT_ID and GE_ENGINE_ID are not set")
	}

	// 2. Resolve Access Token
	token, err := GetAccessToken()
	if err != nil {
		t.Skipf("skipping live E2E test: GCP ADC credentials unavailable: %v", err)
	}

	// 3. Load smoke test cases
	cases, err := LoadTestCases("test_cases/smoke_test_cases.json")
	if err != nil {
		t.Fatalf("failed to load smoke test cases: %v", err)
	}
	if len(cases) == 0 {
		t.Fatal("no smoke test cases found")
	}

	// 4. Create client and logger
	timeout := time.Duration(cfg.TimeoutSeconds) * time.Second
	if timeout <= 0 {
		timeout = 180 * time.Second
	}
	client := NewStreamAssistClient(token, timeout)

	var logBuf bytes.Buffer
	logger := NewStreamLogger(&logBuf, true)

	// 5. Execute prober suite
	ctx, cancel := context.WithTimeout(context.Background(), 240*time.Second)
	defer cancel()

	report := RunProberSuiteWithLogger(ctx, "", cases, cfg, client, logger)

	// 6. Assertions
	if report.TotalProbes != len(cases) {
		t.Errorf("expected %d total probes, got %d", len(cases), report.TotalProbes)
	}

	if report.FunctionalPassed < report.TotalProbes {
		t.Errorf("E2E Prober failure: only %d/%d functional probes passed", report.FunctionalPassed, report.TotalProbes)
		for _, res := range report.Results {
			if !res.Passed {
				t.Errorf("  ❌ Failed Probe [%s] %s: %v", res.Subsystem, res.Title, res.FailureReasons)
			}
		}
	}

	// 7. Verify JSON report export & schema
	reportJSON, err := json.Marshal(report)
	if err != nil {
		t.Fatalf("failed to serialize report to JSON: %v", err)
	}

	var parsed ProberReport
	if err := json.Unmarshal(reportJSON, &parsed); err != nil {
		t.Fatalf("failed to deserialize report JSON: %v", err)
	}

	if parsed.FunctionalPassed != report.TotalProbes {
		t.Errorf("expected parsed report FunctionalPassed %d, got %d", report.TotalProbes, parsed.FunctionalPassed)
	}
}
