#!/bin/sh
set -eu

DATA_HOME="${ZEROCLAW_HOME:-/zeroclaw-data}"
CFG_DIR="${DATA_HOME}/.zeroclaw"
CFG="${CFG_DIR}/config.toml"
TEMPLATE="/opt/lucero/config.lucero.toml"
SESSION_DB="${CFG_DIR}/state/whatsapp-web/session.db"

mkdir -p "${CFG_DIR}/state/whatsapp-web" "${DATA_HOME}/workspace"

cp "${TEMPLATE}" "${CFG}"

if [ -n "${LUCERO_API_BASE:-}" ]; then
  esc=$(printf '%s' "${LUCERO_API_BASE}" | sed 's/[|&\\]/\\&/g')
  sed -i "s|uri = \".*/v1\"|uri = \"${esc}/v1\"|" "${CFG}" || true
fi

sed -i '/^pair_phone\s*=/d' "${CFG}" || true

if [ "${FORCE_NEW_QR:-1}" = "1" ]; then
  echo "Removing WhatsApp session.db for fresh QR"
  rm -f "${SESSION_DB}" "${SESSION_DB}-wal" "${SESSION_DB}-shm" 2>/dev/null || true
fi

export HOME="${DATA_HOME}"
export ZEROCLAW_CONFIG_DIR="${CFG_DIR}"
export ZEROCLAW_WORKSPACE="${DATA_HOME}/workspace"
export ZEROCLAW_gateway__allow_public_bind="${ZEROCLAW_gateway__allow_public_bind:-true}"
export TERM="${TERM:-xterm-256color}"
export RUST_LOG="${RUST_LOG:-info,whatsapp=debug,zeroclaw_channels=debug}"

echo "Lucero WhatsApp sidecar"
echo "Config ${CFG}:"
cat "${CFG}"
echo "---"
echo "channel start help:"
zeroclaw channel start --help 2>&1 || true
echo "---"
echo "Starting zeroclaw daemon (WhatsApp Web QR should follow)..."

# Daemon is the long-running path used by ZeroClaw Docker docs.
# Channel start alone was exiting without QR in this image/config.
exec zeroclaw daemon
