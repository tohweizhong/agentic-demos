# Local or Cloud Run image for the demo web UI.
# Build from the managed_agents_api/webui folder:
#   docker build -t managed-agents-ui .
#   docker run -p 8080:8080 -e GOOGLE_CLOUD_PROJECT=your-project-id \
#     -v "$HOME/.config/gcloud:/home/nonroot/.config/gcloud:ro" managed-agents-ui

FROM node:24-slim AS web
WORKDIR /web
COPY web/ ./
RUN npx -y -p typescript@5.9.3 tsc -p .

FROM golang:1.24 AS server
WORKDIR /src
COPY server/go.mod server/go.sum ./
RUN go mod download
COPY server/ ./
RUN CGO_ENABLED=0 go build -o /server .

FROM gcr.io/distroless/static:nonroot
COPY --from=server /server /server
COPY --from=web /web/index.html /web/style.css /web/
COPY --from=web /web/dist /web/dist
ENV STATIC_DIR=/web PORT=8080
EXPOSE 8080
ENTRYPOINT ["/server"]
