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
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, [load]);

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
                  : "Link via Railway logs or local script"
              }
              icon={<Link2 size={16} />}
            />
          </div>

          <section className="hud-card mb-8 p-5">
            <h2 className="font-display text-lg tracking-wide mb-2">
              Link business WhatsApp
            </h2>
            <ol className="list-decimal list-inside space-y-2 text-sm text-jarvis-muted">
              <li>
                Keep the{" "}
                <code className="text-jarvis-cyan">lucero-whatsapp</code>{" "}
                sidecar running 24/7 on Railway (or run{" "}
                <code className="text-jarvis-cyan">
                  .\scripts\start-zeroclaw.ps1
                </code>{" "}
                locally).
              </li>
              <li>
                Open Railway logs in a terminal (not the web UI QR — it is not
                scannable):{" "}
                <code className="text-jarvis-cyan">
                  .\scripts\show-whatsapp-pair.ps1
                </code>
              </li>
              <li>
                On the <strong className="text-jarvis-text">business</strong>{" "}
                phone: WhatsApp → Settings → Linked Devices → Link a device →{" "}
                <strong className="text-jarvis-text">
                  Link with phone number instead
                </strong>{" "}
                → enter the 8-character pair code.
              </li>
              <li>
                Customers message that business number. Lucero replies to all
                DMs (optional named owners below get full agents).
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
