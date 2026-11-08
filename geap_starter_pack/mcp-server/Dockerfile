# Build the sample MCP server as a static binary.
FROM golang:1.26 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /out/mcp-server .

# Run it on distroless static, as a non-root user.
FROM gcr.io/distroless/static:nonroot
COPY --from=build /out/mcp-server /mcp-server
USER nonroot:nonroot
ENTRYPOINT ["/mcp-server"]
