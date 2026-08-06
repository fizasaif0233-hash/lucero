"use client";

import { useCallback, useEffect, useState } from "react";
import {
  Check,
  Link2,
  MessageCircle,
  Plus,
  Radio,
  RefreshCw,
  Trash2,
} from "lucide-react";
import { SecondaryShell } from "@/components/jarvis/SecondaryShell";
import { api } from "@/services/api";
import type { ChannelIdentity, ChannelStatus } from "@/types";

export default function ChannelsPage() {
  const [status, setStatus] = useState<ChannelStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [phone, setPhone] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [asOwner, setAsOwner] = useState(true);

  const load = useCallback(async () => {
    try {
      setError(null);
      const s = await api.channelStatus();
      setStatus(s);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
    const linked = status?.whatsapp_linked;
    const ms = linked ? 15000 : 3000;
    const id = setInterval(load, ms);
    return () => clearInterval(id);
  }, [load, status?.whatsapp_linked]);

  async function addNumber() {
    if (!phone.trim()) return;
    setBusy(true);
    try {
      await api.createChannelIdentity({
        channel: "whatsapp",
        external_id: phone.trim(),
        display_name: displayName.trim() || undefined,
        allowed: true,
        is_owner: asOwner,
      });
      setPhone("");
      setDisplayName("");
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function toggleAllowed(row: ChannelIdentity) {
    setBusy(true);
    try {
      await api.updateChannelIdentity(row.id, { allowed: !row.allowed });
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function removeIdentity(id: string) {
    setBusy(true);
    try {
      await api.deleteChannelIdentity(id);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const online = status?.gateway_online;
  const linked = status?.whatsapp_linked;
  const bridgeOk = status?.bridge_enabled && status?.bridge_configured;

  return (
    <SecondaryShell title="Channels">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="mx-auto max-w-4xl animate-fadeIn">
          <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
            <div>
              <h1 className="font-display text-3xl tracking-wide mb-2">
                Channels
              </h1>
              <p className="text-sm text-jarvis-muted max-w-2xl">
                Link your business WhatsApp once. Customers just message that
                number — Lucero replies through agents and RAG. Mode:{" "}
                <span className="text-jarvis-cyan">
                  {status?.reply_mode === "allowlist"
                    ? "allowlist only"
                    : "all customers"}
                </span>
                . Default inbound agent:{" "}
                <span className="text-jarvis-cyan">
                  {status?.default_agent || "support"}
                </span>
                .
              </p>
            </div>
            <button
              type="button"
              onClick={load}
              className="inline-flex items-center gap-2 rounded-xl border border-jarvis-border px-3 py-2 text-xs text-jarvis-muted hover:text-jarvis-cyan hover:border-jarvis-cyan/40"
            >
              <RefreshCw size={14} />
              Refresh
            </button>
          </div>

          {error && (
            <div className="mb-6 rounded-xl border border-jarvis-danger/40 bg-jarvis-danger/10 px-4 py-3 text-sm text-jarvis-danger">
              {error}
            </div>
          )}

          <div className="mb-8 grid gap-3 sm:grid-cols-3">
            <StatusTile
              label="Bridge"
              ok={!!bridgeOk}
              detail={
                bridgeOk
                  ? "OpenAI /v1 enabled"
                  : "Set ENABLE_CHANNEL_BRIDGE + API key"
              }
              icon={<Radio size={16} />}
            />
            <StatusTile
              label="ZeroClaw"
              ok={!!online}
              detail={online ? "Gateway heartbeat online" : "Not reporting yet"}
              icon={<MessageCircle size={16} />}
            />
            <StatusTile
              label="WhatsApp"
              ok={!!linked}
              detail={
                linked
                  ? "Linked Devices session"
                  : status?.pairing_qr_data_url
                    ? "Scan the QR below"
                    : "Waiting for QR from sidecar"
              }
              icon={<Link2 size={16} />}
            />
          </div>

          <section className="hud-card mb-8 p-5">
            <h2 className="font-display text-lg tracking-wide mb-2">
              Link your WhatsApp
            </h2>
            {!linked && !status?.pairing_qr_data_url ? (
              <div className="mb-6 rounded-xl border border-jarvis-border bg-jarvis-elevated/50 px-4 py-4 text-sm text-jarvis-muted">
                <p className="mb-2 text-jarvis-text">
                  No live QR yet from the cloud WhatsApp sidecar.
                </p>
                <p className="mb-2">
                  On your PC (so the client can scan a clear QR), run:
                </p>
                <pre className="mb-2 overflow-x-auto rounded-lg bg-black/40 p-3 text-xs text-jarvis-cyan">
{`cd "C:\\Users\\Tech Trends\\Desktop\\Jarvis"
.\\scripts\\pair-whatsapp-then-upload.ps1`}
                </pre>
                <p>
                  Client scans that terminal QR with WhatsApp → Linked Devices,
                  then run{" "}
                  <code className="text-jarvis-cyan">
                    .\scripts\pair-whatsapp-then-upload.ps1 -UploadOnly
                  </code>{" "}
                  to keep it online 24/7 on Railway.
                </p>
              </div>
            ) : null}
            {!linked && status?.pairing_qr_data_url ? (
              <div className="mb-6 flex flex-col items-center gap-4">
                <p className="text-sm text-jarvis-muted text-center max-w-md">
                  Client: open this page on a computer, then on the{" "}
                  <strong className="text-jarvis-text">business phone</strong>{" "}
                  go to WhatsApp → Settings → Linked Devices → Link a device and
                  scan this QR.
                </p>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={status.pairing_qr_data_url}
                  alt="WhatsApp link QR code"
                  width={280}
                  height={280}
                  className="rounded-lg bg-white p-3 shadow-lg"
                />
                {status.pairing_updated_at ? (
                  <p className="text-[11px] text-jarvis-muted">
                    QR refreshed {status.pairing_updated_at} — scan the latest
                    one if it keeps updating.
                  </p>
                ) : null}
              </div>
            ) : null}
            {!linked && status?.pairing_code ? (
              <div className="mb-6 rounded-xl border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-4 py-4 text-center">
                <p className="text-xs uppercase tracking-wider text-jarvis-muted mb-2">
                  Or enter pair code on the phone
                </p>
                <p className="font-display text-3xl tracking-[0.3em] text-jarvis-cyan">
                  {status.pairing_code}
                </p>
                <p className="mt-2 text-xs text-jarvis-muted">
                  Linked Devices → Link a device → Link with phone number
                  instead
                </p>
              </div>
            ) : null}
            {linked ? (
              <p className="mb-4 text-sm text-jarvis-cyan">
                WhatsApp is linked. Customers can message the business number —
                Lucero will reply.
              </p>
            ) : null}
            <ol className="list-decimal list-inside space-y-2 text-sm text-jarvis-muted">
              <li>
                Client logs into Lucero and opens{" "}
                <strong className="text-jarvis-text">Dashboard → Channels</strong>{" "}
                on a computer (not only the phone).
              </li>
              <li>
                Scan the QR above with the business WhatsApp (Linked Devices).
              </li>
              <li>
                Customers message that business WhatsApp number — Lucero replies
                to all DMs.
              </li>
            </ol>
            {status?.pairing_docs ? (
              <p className="mt-3 text-xs text-jarvis-muted">
                {status.pairing_docs}
              </p>
            ) : null}
            {status?.last_message_at && (
              <p className="mt-3 text-xs text-jarvis-muted">
                Last channel message: {status.last_message_at}
                {status.last_external_id
                  ? ` · ${status.last_external_id}`
                  : ""}
              </p>
            )}
          </section>

          <section className="hud-card p-5">
            <h2 className="font-display text-lg tracking-wide mb-4">
              Named identities (optional)
            </h2>
            <p className="mb-4 text-xs text-jarvis-muted">
              Not required for every customer. Add Owner / Wife numbers only if
              you want full multi-agent routing for those phones. Everyone else
              uses the default Support path when reply mode is all customers.
            </p>
            <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-end">
              <label className="flex-1 text-xs text-jarvis-muted">
                E.164 phone
                <input
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="+15551234567"
                  className="mt-1 w-full rounded-xl border border-jarvis-border bg-jarvis-elevated px-3 py-2 text-sm text-jarvis-text"
                />
              </label>
              <label className="flex-1 text-xs text-jarvis-muted">
                Display name
                <input
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  placeholder="Owner"
                  className="mt-1 w-full rounded-xl border border-jarvis-border bg-jarvis-elevated px-3 py-2 text-sm text-jarvis-text"
                />
              </label>
              <label className="flex items-center gap-2 pb-2 text-xs text-jarvis-muted">
                <input
                  type="checkbox"
                  checked={asOwner}
                  onChange={(e) => setAsOwner(e.target.checked)}
                />
                Owner (full agents)
              </label>
              <button
                type="button"
                disabled={busy || !phone.trim()}
                onClick={addNumber}
                className="inline-flex items-center justify-center gap-2 rounded-xl border border-jarvis-cyan/50 bg-jarvis-cyan/10 px-4 py-2 text-sm text-jarvis-cyan disabled:opacity-40"
              >
                <Plus size={14} />
                Allowlist
              </button>
            </div>

            <div className="space-y-2">
              {(status?.identities || []).length === 0 && (
                <p className="text-sm text-jarvis-muted">
                  No named identities yet. Customers can still message the
                  linked business WhatsApp — Lucero replies via the default
                  channel user / Support agent.
                </p>
              )}
              {(status?.identities || []).map((row) => (
                <div
                  key={row.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-jarvis-border/70 bg-jarvis-elevated/40 px-3 py-2.5"
                >
                  <div>
                    <div className="text-sm text-jarvis-text">
                      {row.external_id}
                      {row.display_name ? (
                        <span className="text-jarvis-muted">
                          {" "}
                          · {row.display_name}
                        </span>
                      ) : null}
                    </div>
                    <div className="text-[10px] uppercase tracking-wider text-jarvis-muted">
                      {row.channel}
                      {row.is_owner ? " · owner" : " · support default"}
                      {row.allowed ? " · allowed" : " · blocked"}
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => toggleAllowed(row)}
                      className="rounded-lg border border-jarvis-border px-2.5 py-1.5 text-xs text-jarvis-muted hover:text-jarvis-cyan"
                    >
                      {row.allowed ? "Block" : "Allow"}
                    </button>
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => removeIdentity(row.id)}
                      className="rounded-lg border border-jarvis-border p-1.5 text-jarvis-muted hover:text-jarvis-danger"
                      title="Remove"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </section>
        </div>
      </div>
    </SecondaryShell>
  );
}

function StatusTile({
  label,
  ok,
  detail,
  icon,
}: {
  label: string;
  ok: boolean;
  detail: string;
  icon: React.ReactNode;
}) {
  return (
    <div className="hud-card p-4">
      <div className="mb-2 flex items-center justify-between">
        <span className="flex items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-jarvis-cyan">
          {icon}
          {label}
        </span>
        <span
          className={`flex h-6 w-6 items-center justify-center rounded-full border ${
            ok
              ? "border-jarvis-success/40 text-jarvis-success"
              : "border-jarvis-border text-jarvis-muted"
          }`}
        >
          {ok ? <Check size={12} /> : <span className="h-1.5 w-1.5 rounded-full bg-jarvis-muted" />}
        </span>
      </div>
      <p className="text-sm text-jarvis-text">{ok ? "Ready" : "Waiting"}</p>
      <p className="mt-1 text-[11px] text-jarvis-muted">{detail}</p>
    </div>
  );
}
