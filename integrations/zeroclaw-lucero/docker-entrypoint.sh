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

rm -f "${SESSION_DB}" "${SESSION_DB}-wal" "${SESSION_DB}-shm" 2>/dev/null || true

export HOME="${DATA_HOME}"
export ZEROCLAW_CONFIG_DIR="${CFG_DIR}"
export ZEROCLAW_WORKSPACE="${DATA_HOME}/workspace"
export ZEROCLAW_gateway__allow_public_bind=true
export TERM=xterm-256color
export RUST_LOG=info
export PYTHONUNBUFFERED=1

echo "Lucero WhatsApp: starting channels (verbose)"
cat "${CFG}"
echo "---"

# Background: pipe a copy of later logs is hard; start relay that polls
# gateway pairing is NOT WhatsApp. We need channel start output.
# Run channel start with verbose so WhatsApp Web QR is printed.
exec zeroclaw -v channel start
