# Lucero WhatsApp sidecar — ZeroClaw transport → hosted Lucero /v1 brain.
# Build from repo root:
#   docker build -f integrations/zeroclaw-lucero/Dockerfile -t lucero-whatsapp .

FROM ghcr.io/zeroclaw-labs/zeroclaw:debian

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pil python3-pip \
    && pip3 install --break-system-packages --no-cache-dir qrcode[pil] \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /opt/lucero /zeroclaw-data/.zeroclaw/state/whatsapp-web /zeroclaw-data/workspace \
    && chmod -R 777 /zeroclaw-data

COPY integrations/zeroclaw-lucero/config.lucero.toml /opt/lucero/config.lucero.toml
COPY integrations/zeroclaw-lucero/docker-entrypoint.sh /opt/lucero/docker-entrypoint.sh
COPY integrations/zeroclaw-lucero/pair_relay.py /opt/lucero/pair_relay.py
RUN chmod +x /opt/lucero/docker-entrypoint.sh /opt/lucero/pair_relay.py

ENV HOME=/zeroclaw-data \
    ZEROCLAW_HOME=/zeroclaw-data \
    ZEROCLAW_CONFIG_DIR=/zeroclaw-data/.zeroclaw \
    ZEROCLAW_WORKSPACE=/zeroclaw-data/workspace \
    LUCERO_API_BASE=https://lucero-api-production.up.railway.app \
    ZEROCLAW_gateway__allow_public_bind=true \
    PORT=42617

EXPOSE 42617

WORKDIR /zeroclaw-data
ENTRYPOINT ["/opt/lucero/docker-entrypoint.sh"]
