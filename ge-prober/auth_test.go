package main

import (
	"os"
	"testing"
)

func TestGetToken_EnvOverride(t *testing.T) {
	expectedToken := "test-token-ya29-xyz"
	os.Setenv("GCP_ACCESS_TOKEN", expectedToken)
	defer os.Unsetenv("GCP_ACCESS_TOKEN")

	token, err := GetAccessToken()
	if err != nil {
		t.Fatalf("expected token from env, got error: %v", err)
	}

	if token != expectedToken {
		t.Errorf("expected '%s', got '%s'", expectedToken, token)
	}
}
