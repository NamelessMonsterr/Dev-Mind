# Ollama with Phi-3 model pre-pulled
FROM ollama/ollama:latest

# Create model directory
RUN mkdir -p /root/.ollama/models

# Expose Ollama port
EXPOSE 11434

# Pre-pull Phi-3 model during build
RUN ollama serve & \
    sleep 10 && \
    ollama pull phi3 && \
    pkill ollama

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:11434/ || exit 1

CMD ["/bin/ollama", "serve"]
