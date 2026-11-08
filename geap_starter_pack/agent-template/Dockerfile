# Container for the reference agent on Agent Runtime (image_spec deploy).
# It follows the ADK deploy template. It runs `adk api_server`.
FROM python:3.13-slim
WORKDIR /app

RUN adduser --disabled-password --gecos "" appuser

# The egress Agent Gateway inspects TLS with its own root CA. Terraform passes
# the CA from the gateway as a build argument. Python HTTP clients, OpenSSL, and
# gRPC must all trust it, so the three variables point to the system bundle.
ARG AGENT_GATEWAY_ROOT_CERTIFICATES
RUN if [ -n "$AGENT_GATEWAY_ROOT_CERTIFICATES" ]; then \
      mkdir -p /usr/local/share/ca-certificates && \
      printf '%b\n' "$AGENT_GATEWAY_ROOT_CERTIFICATES" | awk 'BEGIN {c=0} /BEGIN CERTIFICATE/ {c++} {print > ("/usr/local/share/ca-certificates/agw-ca-" c ".crt")}' && \
      update-ca-certificates; \
    fi
ENV REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
ENV GRPC_DEFAULT_SSL_ROOTS_FILE_PATH=/etc/ssl/certs/ca-certificates.crt

USER appuser
ENV PATH="/home/appuser/.local/bin:$PATH"

COPY --chown=appuser:appuser requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --user -r /app/requirements.txt

COPY --chown=appuser:appuser work_items/ /app/agents/work_items/

EXPOSE 8080
# On Agent Runtime, GOOGLE_CLOUD_AGENT_ENGINE_ID is set, so `adk api_server`
# uses Agent Runtime Sessions.
CMD ["adk", "api_server", "--host=0.0.0.0", "--port=8080", "--trace_to_cloud", "/app/agents"]
