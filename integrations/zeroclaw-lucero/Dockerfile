# Lucero WhatsApp sidecar — ZeroClaw transport → hosted Lucero /v1 brain.
# Build from repo root:
#   docker build -f integrations/zeroclaw-lucero/Dockerfile -t lucero-whatsapp .
#
# Official image includes whatsapp-web in current default feature set.

FROM ghcr.io/zeroclaw-labs/zeroclaw:debian

USER root

RUN mkdir -p /opt/lucero /zeroclaw-data/.zeroclaw/state/whatsapp-web /zeroclaw-data/workspace \
    && chmod -R 777 /zeroclaw-data

COPY integrations/zeroclaw-lucero/config.lucero.toml /opt/lucero/config.lucero.toml
COPY integrations/zeroclaw-lucero/docker-entrypoint.sh /opt/lucero/docker-entrypoint.sh
RUN chmod +x /opt/lucero/docker-entrypoint.sh

ENV HOME=/zeroclaw-data \
    ZEROCLAW_HOME=/zeroclaw-data \
    ZEROCLAW_CONFIG_DIR=/zeroclaw-data/.zeroclaw \
    ZEROCLAW_WORKSPACE=/zeroclaw-data/workspace \
    LUCERO_API_BASE=https://lucero-api-production.up.railway.app \
    ZEROCLAW_gateway__allow_public_bind=true \
    PORT=42617

# Persist WhatsApp session via Railway Volume mounted at /zeroclaw-data (not Docker VOLUME).
EXPOSE 42617

WORKDIR /zeroclaw-data
ENTRYPOINT ["/opt/lucero/docker-entrypoint.sh"]
