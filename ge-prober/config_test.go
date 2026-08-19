package main

import (
	"os"
	"path/filepath"
	"testing"
)

func TestParseDataStoreIDs(t *testing.T) {
	// Comma separated
	ds1 := ParseDataStoreIDs("ds-file, ds-attach, ds-event")
	if len(ds1) != 3 || ds1[0] != "ds-file" || ds1[1] != "ds-attach" || ds1[2] != "ds-event" {
		t.Errorf("unexpected comma parsing: %v", ds1)
	}

	// JSON array
	ds2 := ParseDataStoreIDs(`["ds-a", "ds-b"]`)
	if len(ds2) != 2 || ds2[0] != "ds-a" || ds2[1] != "ds-b" {
		t.Errorf("unexpected JSON parsing: %v", ds2)
	}

	// Empty
	ds3 := ParseDataStoreIDs("")
	if len(ds3) != 0 {
		t.Errorf("expected empty slice, got: %v", ds3)
	}
}

func TestLoadDotEnv(t *testing.T) {
	tmpDir := t.TempDir()
	envPath := filepath.Join(tmpDir, ".env")

	content := `
# Comment line
TEST_DOTENV_KEY="test_value_123"
TEST_DOTENV_SINGLE='single_quoted'
`
	if err := os.WriteFile(envPath, []byte(content), 0644); err != nil {
		t.Fatalf("failed to write .env: %v", err)
	}

	LoadDotEnv(envPath)

	if os.Getenv("TEST_DOTENV_KEY") != "test_value_123" {
		t.Errorf("expected 'test_value_123', got '%s'", os.Getenv("TEST_DOTENV_KEY"))
	}
	if os.Getenv("TEST_DOTENV_SINGLE") != "single_quoted" {
		t.Errorf("expected 'single_quoted', got '%s'", os.Getenv("TEST_DOTENV_SINGLE"))
	}
}

func TestResolveConfig_Precedence(t *testing.T) {
	tmpDir := t.TempDir()
	configPath := filepath.Join(tmpDir, "config.json")

	fileContent := `{
		"project_id": "file-project",
		"location": "global",
		"engine_id": "file-engine",
		"max_concurrency": 2
	}`
	if err := os.WriteFile(configPath, []byte(fileContent), 0644); err != nil {
		t.Fatalf("failed to write test config: %v", err)
	}

	// Set Env Vars
	os.Setenv("GE_PROJECT_ID", "env-project")
	os.Setenv("GE_LOCATION", "asia-southeast1")
	defer os.Unsetenv("GE_PROJECT_ID")
	defer os.Unsetenv("GE_LOCATION")

	// 1. Env overrides File
	cfg1, err := ResolveConfig(configPath, CLIFlagOverrides{})
	if err != nil {
		t.Fatalf("ResolveConfig failed: %v", err)
	}
	if cfg1.ProjectID != "env-project" {
		t.Errorf("expected Env project 'env-project', got '%s'", cfg1.ProjectID)
	}
	if cfg1.Location != "asia-southeast1" {
		t.Errorf("expected Env location 'asia-southeast1', got '%s'", cfg1.Location)
	}
	if cfg1.EngineID != "file-engine" {
		t.Errorf("expected File engine 'file-engine', got '%s'", cfg1.EngineID)
	}

	// 2. CLI Flags override Env and File
	cfg2, err := ResolveConfig(configPath, CLIFlagOverrides{
		ProjectID: "flag-project",
		EngineID:  "flag-engine",
	})
	if err != nil {
		t.Fatalf("ResolveConfig with flags failed: %v", err)
	}
	if cfg2.ProjectID != "flag-project" {
		t.Errorf("expected Flag project 'flag-project', got '%s'", cfg2.ProjectID)
	}
	if cfg2.EngineID != "flag-engine" {
		t.Errorf("expected Flag engine 'flag-engine', got '%s'", cfg2.EngineID)
	}
}

func TestValidateConfig(t *testing.T) {
	// Missing mandatory parameters
	invalidCfg := &Config{
		ProjectID: "",
		EngineID:  "",
	}
	if err := ValidateConfig(invalidCfg); err == nil {
		t.Errorf("expected validation error for missing parameters, got nil")
	}

	// Valid config
	validCfg := &Config{
		ProjectID: "my-project",
		EngineID:  "my-engine",
		Location:  "global",
	}
	if err := ValidateConfig(validCfg); err != nil {
		t.Errorf("expected valid config to pass, got: %v", err)
	}
}

func TestLoadTestCases_Valid(t *testing.T) {
	tmpDir := t.TempDir()
	tcPath := filepath.Join(tmpDir, "cases.json")

	content := `[
		{
			"id": "smoke_01",
			"subsystem": "sharepoint",
			"title": "SharePoint Test",
			"query": "Find policy",
			"grounding_type": "vertex_ai_search",
			"slo_targets": {
				"max_ttft_ms": 3000.0,
				"max_ttlt_ms": 12000.0
			},
			"assertions": {
				"must_contain_keywords": ["policy"],
				"forbidden_errors": ["401", "403"]
			}
		}
	]`

	if err := os.WriteFile(tcPath, []byte(content), 0644); err != nil {
		t.Fatalf("failed to write test cases: %v", err)
	}

	cases, err := LoadTestCases(tcPath)
	if err != nil {
		t.Fatalf("failed to load test cases: %v", err)
	}

	if len(cases) != 1 {
		t.Fatalf("expected 1 test case, got %d", len(cases))
	}
	if cases[0].ID != "smoke_01" {
		t.Errorf("expected ID 'smoke_01', got '%s'", cases[0].ID)
	}
}

func TestLoadSmokeTestCases_DefaultSuite(t *testing.T) {
	cases, err := LoadTestCases("test_cases/smoke_test_cases.json")
	if err != nil {
		t.Fatalf("failed to load default smoke test cases: %v", err)
	}
	if len(cases) != 3 {
		t.Fatalf("expected 3 smoke test cases, got %d", len(cases))
	}

	expectedIDs := []string{"smoke_gdrive_01", "smoke_deep_research_02", "smoke_web_grounding_03"}
	for i, expID := range expectedIDs {
		if cases[i].ID != expID {
			t.Errorf("expected test case %d ID '%s', got '%s'", i, expID, cases[i].ID)
		}
		if cases[i].SemanticContract == "" {
			t.Errorf("expected non-empty semantic contract for '%s'", expID)
		}
	}
}

func TestResolveConfig_Verbose(t *testing.T) {
	// 1. Default is true
	cfg, err := ResolveConfig("", CLIFlagOverrides{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !cfg.Verbose {
		t.Errorf("expected default verbose to be true, got false")
	}

	// 2. Env override
	os.Setenv("GE_VERBOSE", "false")
	defer os.Unsetenv("GE_VERBOSE")
	cfgEnv, err := ResolveConfig("", CLIFlagOverrides{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfgEnv.Verbose {
		t.Errorf("expected env GE_VERBOSE=false to set verbose=false")
	}

	// 3. CLI flag override
	vTrue := true
	cfgFlag, err := ResolveConfig("", CLIFlagOverrides{Verbose: &vTrue})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !cfgFlag.Verbose {
		t.Errorf("expected CLI flag override to set verbose=true")
	}
}

func TestResolveConfig_JudgeSettings(t *testing.T) {
	// 1. Defaults
	cfg, err := ResolveConfig("", CLIFlagOverrides{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !cfg.EnableJudge {
		t.Errorf("expected default EnableJudge true, got false")
	}
	if cfg.JudgeModel != "gemini-2.5-flash" {
		t.Errorf("expected default JudgeModel gemini-2.5-flash, got %s", cfg.JudgeModel)
	}

	// 2. Env override
	os.Setenv("GE_ENABLE_JUDGE", "false")
	os.Setenv("GE_JUDGE_MODEL", "gemini-2.0-flash")
	defer func() {
		os.Unsetenv("GE_ENABLE_JUDGE")
		os.Unsetenv("GE_JUDGE_MODEL")
	}()

	cfgEnv, err := ResolveConfig("", CLIFlagOverrides{})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if cfgEnv.EnableJudge {
		t.Errorf("expected env GE_ENABLE_JUDGE=false to disable judge")
	}
	if cfgEnv.JudgeModel != "gemini-2.0-flash" {
		t.Errorf("expected env GE_JUDGE_MODEL=gemini-2.0-flash, got %s", cfgEnv.JudgeModel)
	}

	// 3. CLI overrides
	jTrue := true
	cfgFlag, err := ResolveConfig("", CLIFlagOverrides{
		EnableJudge: &jTrue,
		JudgeModel:  "gemini-2.5-pro",
	})
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !cfgFlag.EnableJudge {
		t.Errorf("expected CLI flag override to enable judge")
	}
	if cfgFlag.JudgeModel != "gemini-2.5-pro" {
		t.Errorf("expected CLI flag model gemini-2.5-pro, got %s", cfgFlag.JudgeModel)
	}
}
