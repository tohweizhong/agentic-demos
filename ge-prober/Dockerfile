# Multi-stage Dockerfile for ge-prober (Minimal static distroless image < 20MB)
FROM golang:alpine AS builder

WORKDIR /app

# Cache dependencies
COPY go.mod go.sum ./
RUN go mod download

# Copy source code
COPY . .

# Build static binary without CGO
RUN CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -ldflags="-w -s" -o /ge-prober .

# Distroless runtime image for maximum security and minimal cold start
FROM gcr.io/distroless/static-debian12:nonroot

WORKDIR /app

COPY --from=builder /ge-prober /app/ge-prober
COPY config.json /app/config.json
COPY test_cases /app/test_cases

USER nonroot:nonroot

ENTRYPOINT ["/app/ge-prober"]
