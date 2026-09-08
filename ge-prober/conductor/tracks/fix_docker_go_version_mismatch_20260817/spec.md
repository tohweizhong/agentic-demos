# Specification: Fix Docker Go Version Mismatch

## Problem Statement
When running `bash deploy_job.sh`, Google Cloud Build failed during step 0 (`docker build`):
```
Step 4/13 : RUN go mod download
go: go.mod requires go >= 1.26.5 (running go 1.22.12; GOTOOLCHAIN=local)
The command '/bin/sh -c go mod download' returned a non-zero code: 1
```

## Root Cause
- `go.mod` was created with directive `go 1.26.5`.
- `Dockerfile` used the builder image `FROM golang:1.22-alpine AS builder`.
- Go 1.22's toolchain rejects `go.mod` files requiring a newer minimum version when `GOTOOLCHAIN=local`.

## Remediation Plan
1. Update `go.mod` to specify `go 1.22` (fully compatible with standard library and `golang.org/x/oauth2`).
2. Update `Dockerfile` to use `golang:alpine` for the builder image.
3. Validate local build and re-trigger Cloud Build deployment.

## Acceptance Criteria
- [ ] `go.mod` specifies `go 1.22`.
- [ ] `Dockerfile` builder image compiles cleanly without version mismatch errors.
- [ ] `bash deploy_job.sh` successfully builds container image in Google Cloud Build and deploys Cloud Run Job `ge-prober-daily`.
