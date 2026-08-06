#!/bin/sh
set -eu

DATA_HOME="${ZEROCLAW_HOME:-/zeroclaw-data}"
CFG_DIR="${DATA_HOME}/.zeroclaw"
CFG="${CFG_DIR}/config.toml"
TEMPLATE="/opt/lucero/config.lucero.toml"

mkdir -p "${CFG_DIR}/state/whatsapp-web" "${DATA_HOME}/workspace"

# Seed Lucero overlay on first boot; keep existing session config on restarts
# unless FORCE_LUCERO_CONFIG=1 is set.
if [ ! -f "${CFG}" ] || [ "${FORCE_LUCERO_CONFIG:-0}" = "1" ]; then
  cp "${TEMPLATE}" "${CFG}"
fi

if [ -n "${LUCERO_API_BASE:-}" ]; then
  esc=$(printf '%s' "${LUCERO_API_BASE}" | sed 's/[|&\\]/\\&/g')
  sed -i "s|uri = \".*/v1\"|uri = \"${esc}/v1\"|" "${CFG}" || true
fi

# Optional pair-code mode (digits only). Empty/unset => QR for Lucero dashboard.
PAIR_PHONE_RAW="${ZEROCLAW_PAIR_PHONE:-}"
PAIR_PHONE=$(printf '%s' "${PAIR_PHONE_RAW}" | tr -cd '0-9')
if [ -n "${PAIR_PHONE}" ]; then
  esc_phone=$(printf '%s' "${PAIR_PHONE}" | sed 's/[|&\\]/\\&/g')
  if grep -q 'pair_phone' "${CFG}"; then
    sed -i "s|pair_phone = \".*\"|pair_phone = \"${esc_phone}\"|g" "${CFG}"
  else
    printf '\npair_phone = "%s"\n' "${PAIR_PHONE}" >> "${CFG}"
  fi
  echo "Pair-code mode enabled for phone digits ${PAIR_PHONE}"
else
  # Ensure QR mode: strip any stale pair_phone from a previous deploy.
  sed -i '/^pair_phone\s*=/d' "${CFG}" || true
  echo "QR mode: client scans QR on Lucero Dashboard → Channels"
fi

export HOME="${DATA_HOME}"
export ZEROCLAW_CONFIG_DIR="${CFG_DIR}"
export ZEROCLAW_WORKSPACE="${DATA_HOME}/workspace"
export ZEROCLAW_gateway__allow_public_bind="${ZEROCLAW_gateway__allow_public_bind:-true}"

echo "Lucero WhatsApp sidecar starting"
echo "Config: ${CFG}"
echo "Pairing publishes to ${LUCERO_API_BASE:-}/api/v1/channels/pairing"

CMD="zeroclaw daemon"
if zeroclaw channel start --help >/dev/null 2>&1; then
  CMD="zeroclaw channel start"
elif zeroclaw channels start --help >/dev/null 2>&1; then
  CMD="zeroclaw channels start"
fi

# Relay QR/pair-code into Lucero dashboard (scannable PNG for the client).
exec python3 /opt/lucero/pair_relay.py $CMD
