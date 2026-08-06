#!/bin/sh
set -eu

DATA_HOME="${ZEROCLAW_HOME:-/zeroclaw-data}"
CFG_DIR="${DATA_HOME}/.zeroclaw"
CFG="${CFG_DIR}/config.toml"
TEMPLATE="/opt/lucero/config.lucero.toml"
SESSION_DB="${CFG_DIR}/state/whatsapp-web/session.db"

mkdir -p "${CFG_DIR}/state/whatsapp-web" "${DATA_HOME}/workspace"

if [ ! -f "${CFG}" ] || [ "${FORCE_LUCERO_CONFIG:-0}" = "1" ]; then
  cp "${TEMPLATE}" "${CFG}"
fi

if [ -n "${LUCERO_API_BASE:-}" ]; then
  esc=$(printf '%s' "${LUCERO_API_BASE}" | sed 's/[|&\\]/\\&/g')
  sed -i "s|uri = \".*/v1\"|uri = \"${esc}/v1\"|" "${CFG}" || true
fi

sed -i '/^pair_phone\s*=/d' "${CFG}" || true

if [ "${FORCE_NEW_QR:-0}" = "1" ]; then
  echo "FORCE_NEW_QR=1 — removing old WhatsApp session.db"
  rm -f "${SESSION_DB}" "${SESSION_DB}-wal" "${SESSION_DB}-shm" 2>/dev/null || true
fi

export HOME="${DATA_HOME}"
export ZEROCLAW_CONFIG_DIR="${CFG_DIR}"
export ZEROCLAW_WORKSPACE="${DATA_HOME}/workspace"
export ZEROCLAW_gateway__allow_public_bind="${ZEROCLAW_gateway__allow_public_bind:-true}"
export TERM="${TERM:-xterm-256color}"
export RUST_LOG="${RUST_LOG:-info}"

echo "Lucero WhatsApp sidecar starting (direct ZeroClaw for QR)"
echo "Config: ${CFG}"
echo "==== config.toml ===="
sed -n '1,80p' "${CFG}" || true
echo "==== end config ===="
echo "Session db exists: $([ -f "${SESSION_DB}" ] && echo yes || echo no)"
zeroclaw --help 2>&1 | head -n 40 || true

# Direct start — this previously produced QR in Railway logs.
# Dashboard PNG relay is temporarily secondary until QR is stable again.
exec zeroclaw channel start
