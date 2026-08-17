package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"os"
	"strconv"
	"strings"
)

// CLIFlagOverrides captures explicit command-line flag inputs.
type CLIFlagOverrides struct {
	ProjectID      string
	Location       string
	EngineID       string
	AssistantID    string
	DataStoreIDs   string
	MaxConcurrency int
	TimeoutSeconds int
	TestCasesPath  string
	OutputFile     string
	Token          string
}

// LoadDotEnv parses a local .env file if it exists, without external dependencies.
// Existing environment variables are never overwritten.
func LoadDotEnv(path string) {
	if path == "" {
		path = ".env"
	}
	file, err := os.Open(path)
	if err != nil {
		return // File optional
	}
	defer file.Close()

	scanner := bufio.NewScanner(file)
	for scanner.Scan() {
		line := strings.TrimSpace(scanner.Text())
		if line == "" || strings.HasPrefix(line, "#") {
			continue
		}
		parts := strings.SplitN(line, "=", 2)
		if len(parts) != 2 {
			continue
		}
		key := strings.TrimSpace(parts[0])
		val := strings.TrimSpace(parts[1])
		// Strip outer quotes if present
		if len(val) >= 2 && ((val[0] == '"' && val[len(val)-1] == '"') || (val[0] == '\'' && val[len(val)-1] == '\'')) {
			val = val[1 : len(val)-1]
		}
		if _, exists := os.LookupEnv(key); !exists {
			_ = os.Setenv(key, val)
		}
	}
}

// DefaultConfig returns safe fallback configuration parameters.
func DefaultConfig() *Config {
	return &Config{
		ProjectID:      "",
		Location:       "global",
		EngineID:       "",
		AssistantID:    "default_assistant",
		TimeoutSeconds: 180,
		MaxConcurrency: 4,
		DataStoreIDs:   []string{},
	}
}

// ParseDataStoreIDs converts a comma-separated or JSON list of data stores into a slice of strings.
func ParseDataStoreIDs(input string) []string {
	input = strings.TrimSpace(input)
	if input == "" {
		return []string{}
	}
	// Try parsing as JSON array
	if strings.HasPrefix(input, "[") && strings.HasSuffix(input, "]") {
		var list []string
		if err := json.Unmarshal([]byte(input), &list); err == nil {
			return list
		}
	}
	// Split by comma
	raw := strings.Split(input, ",")
	var result []string
	for _, item := range raw {
		trimmed := strings.TrimSpace(item)
		if trimmed != "" {
			result = append(result, trimmed)
		}
	}
	return result
}

// getFirstEnv returns the first non-empty value among the given environment variable keys.
func getFirstEnv(keys ...string) string {
	for _, key := range keys {
		if val := strings.TrimSpace(os.Getenv(key)); val != "" {
			return val
		}
	}
	return ""
}

// ResolveConfig implements 12-factor configuration resolution:
// Flags > OS Environment Variables > .env > config.json > Defaults.
func ResolveConfig(configFilePath string, flags CLIFlagOverrides) (*Config, error) {
	// 1. Auto-load .env if present
	LoadDotEnv(".env")

	// 2. Start from defaults
	cfg := DefaultConfig()

	// 3. Load from JSON config file if present
	if configFilePath == "" {
		configFilePath = "config.json"
	}
	if data, err := os.ReadFile(configFilePath); err == nil {
		_ = json.Unmarshal(data, cfg)
	}

	// 4. Environment variable overrides (Priority 2)
	if envProj := getFirstEnv("GE_PROJECT_ID", "GCP_PROJECT_ID", "PROJECT_ID"); envProj != "" {
		cfg.ProjectID = envProj
	}
	if envLoc := getFirstEnv("GE_LOCATION", "GCP_LOCATION", "LOCATION", "REGION"); envLoc != "" {
		cfg.Location = envLoc
	}
	if envEng := getFirstEnv("GE_ENGINE_ID", "GCP_ENGINE_ID", "ENGINE_ID", "APP_ID"); envEng != "" {
		cfg.EngineID = envEng
	}
	if envAss := getFirstEnv("GE_ASSISTANT_ID", "ASSISTANT_ID"); envAss != "" {
		cfg.AssistantID = envAss
	}
	if envDS := getFirstEnv("GE_DATA_STORE_IDS", "DATA_STORE_IDS", "DATASTORES"); envDS != "" {
		cfg.DataStoreIDs = ParseDataStoreIDs(envDS)
	}
	if envConc := getFirstEnv("GE_MAX_CONCURRENCY", "CONCURRENCY"); envConc != "" {
		if n, err := strconv.Atoi(envConc); err == nil && n > 0 {
			cfg.MaxConcurrency = n
		}
	}
	if envTimeout := getFirstEnv("GE_TIMEOUT_SECONDS", "TIMEOUT_SECONDS"); envTimeout != "" {
		if n, err := strconv.Atoi(envTimeout); err == nil && n > 0 {
			cfg.TimeoutSeconds = n
		}
	}

	// 5. CLI flag overrides (Priority 1 - highest)
	if flags.ProjectID != "" {
		cfg.ProjectID = flags.ProjectID
	}
	if flags.Location != "" {
		cfg.Location = flags.Location
	}
	if flags.EngineID != "" {
		cfg.EngineID = flags.EngineID
	}
	if flags.AssistantID != "" {
		cfg.AssistantID = flags.AssistantID
	}
	if flags.DataStoreIDs != "" {
		cfg.DataStoreIDs = ParseDataStoreIDs(flags.DataStoreIDs)
	}
	if flags.MaxConcurrency > 0 {
		cfg.MaxConcurrency = flags.MaxConcurrency
	}
	if flags.TimeoutSeconds > 0 {
		cfg.TimeoutSeconds = flags.TimeoutSeconds
	}

	return cfg, nil
}

// ValidateConfig verifies that all mandatory connection parameters are present.
func ValidateConfig(cfg *Config) error {
	var missing []string
	if cfg.ProjectID == "" {
		missing = append(missing, "Project ID (-project or GCP_PROJECT_ID)")
	}
	if cfg.EngineID == "" {
		missing = append(missing, "Engine ID (-engine or GE_ENGINE_ID)")
	}
	if cfg.Location == "" {
		cfg.Location = "global"
	}
	if len(missing) > 0 {
		return fmt.Errorf("missing required configuration parameters: %s", strings.Join(missing, ", "))
	}
	return nil
}

// LoadConfig is backward-compatible loader.
func LoadConfig(path string) (*Config, error) {
	return ResolveConfig(path, CLIFlagOverrides{})
}

// LoadTestCases loads smoke test cases from the specified JSON file.
func LoadTestCases(path string) ([]TestCase, error) {
	if path == "" {
		path = "test_cases/smoke_test_cases.json"
	}

	data, err := os.ReadFile(path)
	if err != nil {
		return nil, fmt.Errorf("failed to read test cases at %s: %w", path, err)
	}

	var cases []TestCase
	if err := json.Unmarshal(data, &cases); err != nil {
		return nil, fmt.Errorf("failed to parse test cases JSON: %w", err)
	}

	if len(cases) == 0 {
		return nil, fmt.Errorf("no test cases found in %s", path)
	}

	return cases, nil
}
