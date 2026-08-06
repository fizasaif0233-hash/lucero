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
                WhatsApp (and later Telegram) connect through ZeroClaw. Every
                reply still runs through L.U.C.E.R.O agents and RAG. Default
                inbound agent:{" "}
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
                  : "Scan QR via start-zeroclaw.ps1"
              }
              icon={<Link2 size={16} />}
            />
          </div>

          <section className="hud-card mb-8 p-5">
            <h2 className="font-display text-lg tracking-wide mb-2">
              Pair WhatsApp Web
            </h2>
            <ol className="list-decimal list-inside space-y-2 text-sm text-jarvis-muted">
              <li>Start the backend with the channel bridge enabled.</li>
              <li>
                Run{" "}
                <code className="text-jarvis-cyan">
                  .\scripts\start-zeroclaw.ps1
                </code>{" "}
                (needs Rust +{" "}
                <code className="text-jarvis-cyan">whatsapp-web</code> feature).
              </li>
              <li>
                On your phone: WhatsApp → Settings → Linked Devices → scan the
                QR from the terminal.
              </li>
              <li>
                Message an allowlisted number below; L.U.C.E.R.O replies with RAG
                / agents.
              </li>
            </ol>
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
              Allowed numbers
            </h2>
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
                  No explicit identities yet. Run migration{" "}
                  <code className="text-jarvis-cyan">
                    004_channel_identities.sql
                  </code>{" "}
                  and add Owner / Wife numbers to tighten allowlisting. Until
                  then, the configured default channel user can still handle
                  inbound messages.
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
