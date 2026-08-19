#!/usr/bin/env bash
# Runner for local Go E2E tests against Gemini Enterprise live backend
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="${SCRIPT_DIR}/.."

cd "${ROOT_DIR}"

echo "================================================================================"
echo "🧪 RUNNING LOCAL GO E2E TEST SUITE (//go:build e2e)"
echo "================================================================================"
echo "Running: go test -v -tags=e2e -run TestLiveE2E ./..."
echo

go test -v -tags=e2e -run TestLiveE2E ./...
