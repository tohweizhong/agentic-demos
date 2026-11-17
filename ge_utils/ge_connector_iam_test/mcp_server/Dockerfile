# Stage 1: build a static binary.
FROM golang:1.25 AS build
WORKDIR /src
COPY go.mod go.sum ./
RUN go mod download
COPY *.go ./
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /iamtest-mcp .

# Stage 2: run the binary on a distroless image.
FROM gcr.io/distroless/static
COPY --from=build /iamtest-mcp /iamtest-mcp
ENV PORT=8080
EXPOSE 8080
USER nonroot:nonroot
ENTRYPOINT ["/iamtest-mcp"]
