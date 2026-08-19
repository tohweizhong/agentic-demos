package main

import (
	"context"
	"encoding/json"
	"flag"
	"fmt"
	"os"
	"time"
)

func main() {
	configPath := flag.String("config", "config.json", "Path to JSON config file")
	projectID := flag.String("project", "", "Target GCP Project ID (overrides config/env)")
	location := flag.String("location", "", "Target Discovery Engine location (e.g. 'global', 'us', 'eu')")
	regionAlias := flag.String("region", "", "Alias for -location")
	engineID := flag.String("engine", "", "Target Engine / App ID (overrides config/env)")
	assistantID := flag.String("assistant", "", "Target Assistant ID (default: 'default_assistant')")
	dataStores := flag.String("datastores", "", "Comma-separated list of Data Store IDs")
	concurrency := flag.Int("concurrency", 0, "Number of concurrent probe workers")
	timeoutSec := flag.Int("timeout", 0, "Overall timeout in seconds per probe")
	testCasesPath := flag.String("test-cases", "test_cases/smoke_test_cases.json", "Path to smoke_test_cases.json")
	outputJSON := flag.String("output", "smoke_prober_results.json", "Path to export results JSON report")
	outputJSONAlias := flag.String("output-json", "", "Alias for -output")
	tokenFlag := flag.String("token", "", "GCP Access Token override (fallback to ADC/WIF)")
	verboseFlag := flag.Bool("verbose", true, "Enable line-by-line verbose stream tracing")
	flag.Parse()

	// Resolve aliases
	loc := *location
	if loc == "" && *regionAlias != "" {
		loc = *regionAlias
	}
	outPath := *outputJSON
	if *outputJSONAlias != "" {
		outPath = *outputJSONAlias
	}

	var explicitVerbose *bool
	flag.Visit(func(f *flag.Flag) {
		if f.Name == "verbose" {
			explicitVerbose = verboseFlag
		}
	})

	flags := CLIFlagOverrides{
		ProjectID:      *projectID,
		Location:       loc,
		EngineID:       *engineID,
		AssistantID:    *assistantID,
		DataStoreIDs:   *dataStores,
		MaxConcurrency: *concurrency,
		TimeoutSeconds: *timeoutSec,
		TestCasesPath:  *testCasesPath,
		OutputFile:     outPath,
		Token:          *tokenFlag,
		Verbose:        explicitVerbose,
	}

	// 12-factor configuration resolution
	cfg, err := ResolveConfig(*configPath, flags)
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Configuration error: %v\n", err)
		os.Exit(1)
	}

	if err := ValidateConfig(cfg); err != nil {
		fmt.Fprintf(os.Stderr, "❌ Invalid configuration: %v\n\n", err)
		fmt.Fprintf(os.Stderr, "💡 Provide missing parameters via:\n")
		fmt.Fprintf(os.Stderr, "   - CLI flags: ./ge-prober -project=YOUR_PROJECT -engine=YOUR_ENGINE -region=global\n")
		fmt.Fprintf(os.Stderr, "   - Environment: export GCP_PROJECT_ID=YOUR_PROJECT GE_ENGINE_ID=YOUR_ENGINE\n")
		fmt.Fprintf(os.Stderr, "   - Local .env file or config.json\n\n")
		os.Exit(1)
	}

	cases, err := LoadTestCases(*testCasesPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "❌ Error loading test cases: %v\n", err)
		os.Exit(1)
	}

	var token string
	if *tokenFlag != "" {
		token = *tokenFlag
	} else {
		token, err = GetAccessToken()
		if err != nil {
			fmt.Fprintf(os.Stderr, "❌ Error resolving GCP access token: %v\n", err)
			os.Exit(1)
		}
	}

	timeout := time.Duration(cfg.TimeoutSeconds) * time.Second
	if timeout <= 0 {
		timeout = 180 * time.Second
	}
	client := NewStreamAssistClient(token, timeout)
	streamLogger := NewStreamLogger(os.Stdout, cfg.Verbose)

	fmt.Println()
	fmt.Println("================================================================================")
	fmt.Println("🚀 GEMINI ENTERPRISE SYNTHETIC SMOKE TEST PROBER (Go)")
	fmt.Println("================================================================================")
	fmt.Printf("🎯 Target Project : %s\n", cfg.ProjectID)
	fmt.Printf("📍 Location / Reg : %s\n", cfg.Location)
	fmt.Printf("⚙️ Target Engine  : %s\n", cfg.EngineID)
	fmt.Printf("📦 Smoke Probes   : %d test cases\n", len(cases))
	fmt.Printf("⚡ Concurrency    : %d parallel workers\n", cfg.MaxConcurrency)
	fmt.Printf("🔍 Verbose Stream : %t\n", cfg.Verbose)
	fmt.Println("================================================================================")
	fmt.Println()

	startTime := time.Now()
	ctx := context.Background()
	report := RunProberSuiteWithLogger(ctx, "", cases, cfg, client, streamLogger)
	totalDuration := time.Since(startTime).Seconds()

	// Print summary report
	fmt.Println()
	fmt.Println(FormatExecutionSummary(report, totalDuration, outPath))
	fmt.Println()

	// Export JSON report
	reportBytes, err := json.MarshalIndent(report, "", "  ")
	if err == nil {
		_ = os.WriteFile(outPath, reportBytes, 0644)
	}

	if report.FunctionalPassed < report.TotalProbes {
		os.Exit(1)
	}
}
