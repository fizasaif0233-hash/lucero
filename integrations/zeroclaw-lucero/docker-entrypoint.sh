#!/bin/sh
set -eu

DATA_HOME="${ZEROCLAW_HOME:-/zeroclaw-data}"
CFG_DIR="${DATA_HOME}/.zeroclaw"
CFG="${CFG_DIR}/config.toml"
TEMPLATE="/opt/lucero/config.lucero.toml"
PAIR_PHONE_RAW="${ZEROCLAW_PAIR_PHONE:-923203628978}"
# WhatsApp pair-code flow wants digits-only E.164 (no + / spaces).
PAIR_PHONE=$(printf '%s' "${PAIR_PHONE_RAW}" | tr -cd '0-9')
if [ -z "${PAIR_PHONE}" ]; then
  echo "ZEROCLAW_PAIR_PHONE must contain digits (e.g. 923203628978)" >&2
  exit 1
fi

mkdir -p "${CFG_DIR}/state/whatsapp-web" "${DATA_HOME}/workspace"

# Seed Lucero overlay on first boot; keep existing session config on restarts
# unless FORCE_LUCERO_CONFIG=1 is set.
if [ ! -f "${CFG}" ] || [ "${FORCE_LUCERO_CONFIG:-0}" = "1" ]; then
  cp "${TEMPLATE}" "${CFG}"
fi

# Always refresh brain URI + WhatsApp peer policy from the image template fields
# that matter for Lucero, without wiping session metadata ZeroClaw may add.
if [ -n "${LUCERO_API_BASE:-}" ]; then
  # Escape for sed replacement - use | delimiter
  esc=$(printf '%s' "${LUCERO_API_BASE}" | sed 's/[|&\\]/\\&/g')
  sed -i "s|uri = \".*/v1\"|uri = \"${esc}/v1\"|" "${CFG}" || true
fi

if [ -n "${PAIR_PHONE}" ]; then
  esc_phone=$(printf '%s' "${PAIR_PHONE}" | sed 's/[|&\\]/\\&/g')
  if grep -q 'pair_phone' "${CFG}"; then
    sed -i "s|pair_phone = \".*\"|pair_phone = \"${esc_phone}\"|" "${CFG}"
  else
    printf '\npair_phone = "%s"\n' "${PAIR_PHONE}" >> "${CFG}"
  fi
fi

export HOME="${DATA_HOME}"
export ZEROCLAW_CONFIG_DIR="${CFG_DIR}"
export ZEROCLAW_WORKSPACE="${DATA_HOME}/workspace"
export ZEROCLAW_gateway__allow_public_bind="${ZEROCLAW_gateway__allow_public_bind:-true}"

echo "Lucero WhatsApp sidecar starting (pair_phone=${PAIR_PHONE})"
echo "Config: ${CFG}"

# Prefer channel start for QR/pair-code + inbound WhatsApp Web.
# Fall back to daemon if channel subcommand is unavailable in the image.
if zeroclaw channel start --help >/dev/null 2>&1; then
  exec zeroclaw channel start
fi

if zeroclaw channels start --help >/dev/null 2>&1; then
  exec zeroclaw channels start
fi

exec zeroclaw daemon
