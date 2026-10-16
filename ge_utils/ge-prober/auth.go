package main

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"strings"

	"golang.org/x/oauth2/google"
)

// GetAccessToken retrieves an OAuth2 bearer token for Google Cloud APIs.
// Priority:
// 1. GCP_ACCESS_TOKEN environment variable.
// 2. Application Default Credentials (ADC) / Cloud Run Service Account.
// 3. Fallback to `gcloud auth print-access-token` for local CLI execution.
func GetAccessToken() (string, error) {
	if envToken := strings.TrimSpace(os.Getenv("GCP_ACCESS_TOKEN")); envToken != "" {
		return envToken, nil
	}

	// Attempt Application Default Credentials (ADC)
	ctx := context.Background()
	creds, err := google.FindDefaultCredentials(ctx, "https://www.googleapis.com/auth/cloud-platform")
	if err == nil && creds != nil && creds.TokenSource != nil {
		token, err := creds.TokenSource.Token()
		if err == nil && token != nil && token.AccessToken != "" {
			return token.AccessToken, nil
		}
	}

	// Fallback to local gcloud CLI if running on developer workstation
	out, err := exec.Command("gcloud", "auth", "print-access-token").Output()
	if err == nil {
		token := strings.TrimSpace(string(out))
		if token != "" {
			return token, nil
		}
	}

	return "", fmt.Errorf("no valid Google Cloud credentials found. Set GCP_ACCESS_TOKEN or run 'gcloud auth application-default login'")
}
