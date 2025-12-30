# Dockerfile
FROM alpine/curl

# Copy toolbox binary and tools.yaml
RUN curl -O https://storage.googleapis.com/genai-toolbox/v0.9.0/linux/amd64/toolbox
RUN chmod +x toolbox

COPY tools.yaml .

# Expose port (if running locally)
EXPOSE 8080

# Entrypoint
ENTRYPOINT ["./toolbox", "--tools-file=tools.yaml", "--address=0.0.0.0", "--port=8080"]
