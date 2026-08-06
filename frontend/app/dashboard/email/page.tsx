"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Loader2, Mail, RefreshCw } from "lucide-react";
import { SecondaryShell } from "@/components/jarvis/SecondaryShell";
import { api } from "@/services/api";
import type { EmailLog, EmailTemplate, LuceroEmail } from "@/types";
import { formatRelativeTime } from "@/lib/utils";

type Tab = "inbox" | "drafts" | "templates" | "sent" | "history" | "logs";

export default function EmailPage() {
  const [tab, setTab] = useState<Tab>("inbox");
  const [emails, setEmails] = useState<LuceroEmail[]>([]);
  const [templates, setTemplates] = useState<EmailTemplate[]>([]);
  const [logs, setLogs] = useState<EmailLog[]>([]);
  const [selected, setSelected] = useState<LuceroEmail | null>(null);
  const [editing, setEditing] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const [draftTo, setDraftTo] = useState("");
  const [draftSubject, setDraftSubject] = useState("");
  const [draftBody, setDraftBody] = useState("");
  const [editSubject, setEditSubject] = useState("");
  const [editBody, setEditBody] = useState("");

  const [tplName, setTplName] = useState("");
  const [tplSubject, setTplSubject] = useState("");
  const [tplBody, setTplBody] = useState("");

  const load = useCallback(async () => {
    setError(null);
    try {
      if (tab === "logs") {
        setLogs(await api.emailLogs());
        return;
      }
      if (tab === "templates") {
        setTemplates(await api.emailTemplates());
        return;
      }
      if (tab === "inbox") {
        setEmails(await api.emailInbox());
        return;
      }
      if (tab === "drafts") {
        setEmails(await api.emailHistory({ folder: "drafts" }));
        return;
      }
      if (tab === "sent") {
        setEmails(await api.emailHistory({ folder: "sent" }));
        return;
      }
      setEmails(await api.emailHistory());
    } catch (err) {
      setError((err as Error).message);
    }
  }, [tab]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3200);
    return () => clearTimeout(t);
  }, [toast]);

  const tabs: { id: Tab; label: string }[] = useMemo(
    () => [
      { id: "inbox", label: "Inbox" },
      { id: "drafts", label: "Drafts" },
      { id: "templates", label: "Templates" },
      { id: "sent", label: "Sent" },
      { id: "history", label: "History" },
      { id: "logs", label: "Logs" },
    ],
    []
  );

  async function createDraft(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const row = await api.emailDraft({
        recipient: draftTo,
        subject: draftSubject,
        body_html: `<p>${draftBody.replace(/\n/g, "<br/>")}</p>`,
        body_text: draftBody,
      });
      setDraftTo("");
      setDraftSubject("");
      setDraftBody("");
      setSelected(row);
      setEditing(false);
      setToast("Draft created — preview & approve before send");
      setTab("inbox");
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function approve() {
    if (!selected) return;
    setBusy(true);
    try {
      const row = await api.emailApprove(selected.id);
      setSelected(row);
      setToast("Approved — ready to send");
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function send() {
    if (!selected) return;
    setBusy(true);
    try {
      const row = await api.emailSend(selected.id, true);
      setSelected(row);
      setToast(row.status === "sent" ? "Email sent via Resend" : "Send finished");
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function cancel() {
    if (!selected) return;
    setBusy(true);
    try {
      const row = await api.emailCancel(selected.id);
      setSelected(row);
      setToast("Cancelled");
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function saveEdit() {
    if (!selected) return;
    setBusy(true);
    try {
      const row = await api.emailUpdate(selected.id, {
        subject: editSubject,
        body_html: `<p>${editBody.replace(/\n/g, "<br/>")}</p>`,
        body_text: editBody,
      });
      setSelected(row);
      setEditing(false);
      setToast("Draft updated");
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function retry() {
    if (!selected) return;
    setBusy(true);
    try {
      const row = await api.emailRetry(selected.id);
      setSelected(row);
      setToast("Retry complete");
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function createTemplate(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    try {
      await api.emailCreateTemplate({
        name: tplName,
        subject: tplSubject,
        body_html: `<p>${tplBody.replace(/\n/g, "<br/>")}</p>`,
        body_text: tplBody,
      });
      setTplName("");
      setTplSubject("");
      setTplBody("");
      setToast("Template saved");
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  function openEmail(em: LuceroEmail) {
    setSelected(em);
    setEditing(false);
    setEditSubject(em.subject);
    setEditBody(em.body_text || em.body_html.replace(/<[^>]+>/g, ""));
  }

  return (
    <SecondaryShell title="Email">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="mx-auto max-w-5xl animate-fadeIn">
          <div className="mb-6 flex flex-wrap items-end justify-between gap-3">
            <div>
              <h1 className="font-display text-3xl mb-2 tracking-wide">Email</h1>
              <p className="text-sm text-jarvis-muted">
                Draft → preview → approve → send via Resend. Never auto-sends.
              </p>
            </div>
            <button
              type="button"
              onClick={() => load()}
              className="inline-flex items-center gap-2 rounded-lg border border-jarvis-border px-3 py-2 text-sm text-jarvis-muted hover:text-jarvis-cyan"
            >
              <RefreshCw size={14} /> Refresh
            </button>
          </div>

          {toast && (
            <div className="mb-4 rounded-xl border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-4 py-2 text-sm text-jarvis-cyan">
              {toast}
            </div>
          )}
          {error && (
            <p className="mb-4 text-sm text-jarvis-danger">{error}</p>
          )}

          <div className="mb-6 flex flex-wrap gap-2">
            {tabs.map((t) => (
              <button
                key={t.id}
                type="button"
                onClick={() => {
                  setTab(t.id);
                  setSelected(null);
                }}
                className={`rounded-lg px-3 py-1.5 text-sm transition ${
                  tab === t.id
                    ? "bg-jarvis-cyan text-jarvis-bg"
                    : "border border-jarvis-border text-jarvis-muted hover:text-jarvis-text"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {tab !== "templates" && tab !== "logs" && (
            <form
              onSubmit={createDraft}
              className="mb-8 rounded-2xl border border-jarvis-border bg-jarvis-elevated/40 p-5 space-y-3"
            >
              <p className="text-xs uppercase tracking-[0.16em] text-jarvis-cyan">
                New draft
              </p>
              <input
                required
                type="email"
                placeholder="Recipient"
                value={draftTo}
                onChange={(e) => setDraftTo(e.target.value)}
                className="w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
              />
              <input
                required
                placeholder="Subject"
                value={draftSubject}
                onChange={(e) => setDraftSubject(e.target.value)}
                className="w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
              />
              <textarea
                required
                rows={4}
                placeholder="Body"
                value={draftBody}
                onChange={(e) => setDraftBody(e.target.value)}
                className="w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
              />
              <button
                type="submit"
                disabled={busy}
                className="inline-flex items-center gap-2 rounded-lg bg-jarvis-cyan px-4 py-2 text-sm font-medium text-jarvis-bg disabled:opacity-50"
              >
                {busy && <Loader2 size={14} className="animate-spin" />}
                Create draft for review
              </button>
            </form>
          )}

          {tab === "templates" && (
            <form
              onSubmit={createTemplate}
              className="mb-8 rounded-2xl border border-jarvis-border bg-jarvis-elevated/40 p-5 space-y-3"
            >
              <input
                required
                placeholder="Template name"
                value={tplName}
                onChange={(e) => setTplName(e.target.value)}
                className="w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
              />
              <input
                required
                placeholder="Subject"
                value={tplSubject}
                onChange={(e) => setTplSubject(e.target.value)}
                className="w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
              />
              <textarea
                required
                rows={4}
                placeholder="Body"
                value={tplBody}
                onChange={(e) => setTplBody(e.target.value)}
                className="w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
              />
              <button
                type="submit"
                disabled={busy}
                className="rounded-lg bg-jarvis-cyan px-4 py-2 text-sm text-jarvis-bg"
              >
                Save template
              </button>
            </form>
          )}

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="space-y-2">
              {tab === "logs" ? (
                logs.length === 0 ? (
                  <p className="text-center text-sm text-jarvis-muted py-10">
                    No email logs yet.
                  </p>
                ) : (
                  logs.map((log) => (
                    <div
                      key={log.id}
                      className="rounded-xl border border-jarvis-border bg-jarvis-elevated/60 px-4 py-3 text-sm"
                    >
                      <div className="flex justify-between gap-2">
                        <span className="text-jarvis-cyan">{log.event}</span>
                        <span className="text-xs text-jarvis-muted">
                          {log.created_at
                            ? formatRelativeTime(log.created_at)
                            : ""}
                        </span>
                      </div>
                      <p className="mt-1 text-xs text-jarvis-muted truncate">
                        {log.email_id || "—"}
                      </p>
                    </div>
                  ))
                )
              ) : tab === "templates" ? (
                templates.length === 0 ? (
                  <p className="text-center text-sm text-jarvis-muted py-10">
                    No templates yet.
                  </p>
                ) : (
                  templates.map((t) => (
                    <div
                      key={t.id}
                      className="rounded-xl border border-jarvis-border bg-jarvis-elevated/60 px-4 py-3"
                    >
                      <p className="font-medium">{t.name}</p>
                      <p className="text-sm text-jarvis-muted">{t.subject}</p>
                      <p className="mt-1 text-xs text-jarvis-muted">
                        {t.category}
                      </p>
                    </div>
                  ))
                )
              ) : emails.length === 0 ? (
                <p className="text-center text-sm text-jarvis-muted py-10">
                  No emails in this view.
                </p>
              ) : (
                emails.map((em) => (
                  <button
                    key={em.id}
                    type="button"
                    onClick={() => openEmail(em)}
                    className={`w-full rounded-xl border px-4 py-3 text-left transition ${
                      selected?.id === em.id
                        ? "border-jarvis-cyan bg-jarvis-cyan/10"
                        : "border-jarvis-border bg-jarvis-elevated/60 hover:border-jarvis-cyan/40"
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{em.subject}</p>
                        <p className="truncate text-xs text-jarvis-muted">
                          {em.recipient}
                        </p>
                      </div>
                      <span className="shrink-0 rounded-md border border-jarvis-border px-2 py-0.5 text-[10px] uppercase tracking-wide text-jarvis-muted">
                        {em.status}
                      </span>
                    </div>
                  </button>
                ))
              )}
            </div>

            <div className="rounded-2xl border border-jarvis-border bg-jarvis-panel/50 p-5 min-h-[280px]">
              {!selected ? (
                <div className="flex h-full flex-col items-center justify-center text-jarvis-muted py-16">
                  <Mail size={28} className="mb-3 opacity-60" />
                  <p className="text-sm">Select an email to preview</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.16em] text-jarvis-cyan mb-1">
                      Preview
                    </p>
                    <h2 className="font-display text-xl">{selected.subject}</h2>
                    <p className="text-sm text-jarvis-muted">
                      To: {selected.recipient}
                    </p>
                    <p className="text-xs text-jarvis-muted mt-1">
                      Status: {selected.status}
                      {selected.error_message
                        ? ` — ${selected.error_message}`
                        : ""}
                    </p>
                  </div>

                  {editing ? (
                    <div className="space-y-2">
                      <input
                        value={editSubject}
                        onChange={(e) => setEditSubject(e.target.value)}
                        className="w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
                      />
                      <textarea
                        rows={8}
                        value={editBody}
                        onChange={(e) => setEditBody(e.target.value)}
                        className="w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
                      />
                      <button
                        type="button"
                        onClick={saveEdit}
                        disabled={busy}
                        className="rounded-lg bg-jarvis-cyan px-3 py-2 text-sm text-jarvis-bg"
                      >
                        Save edits
                      </button>
                    </div>
                  ) : (
                    <div
                      className="prose prose-invert max-w-none text-sm rounded-xl border border-jarvis-border bg-jarvis-bg/60 p-4"
                      dangerouslySetInnerHTML={{
                        __html:
                          selected.body_html ||
                          `<p>${selected.body_text || ""}</p>`,
                      }}
                    />
                  )}

                  <div className="flex flex-wrap gap-2 pt-2">
                    <button
                      type="button"
                      disabled={busy || selected.status === "sent"}
                      onClick={approve}
                      className="rounded-lg bg-jarvis-cyan px-3 py-2 text-sm text-jarvis-bg disabled:opacity-40"
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      disabled={busy || selected.status !== "approved"}
                      onClick={send}
                      className="rounded-lg border border-jarvis-cyan/50 px-3 py-2 text-sm text-jarvis-cyan disabled:opacity-40"
                    >
                      Send
                    </button>
                    <button
                      type="button"
                      disabled={busy || selected.status === "sent"}
                      onClick={() => {
                        setEditing(true);
                        setEditSubject(selected.subject);
                        setEditBody(
                          selected.body_text ||
                            selected.body_html.replace(/<[^>]+>/g, "")
                        );
                      }}
                      className="rounded-lg border border-jarvis-border px-3 py-2 text-sm text-jarvis-muted disabled:opacity-40"
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      disabled={busy || selected.status === "sent"}
                      onClick={cancel}
                      className="rounded-lg border border-jarvis-danger/40 px-3 py-2 text-sm text-jarvis-danger disabled:opacity-40"
                    >
                      Cancel
                    </button>
                    {selected.status === "failed" && (
                      <button
                        type="button"
                        disabled={busy}
                        onClick={retry}
                        className="rounded-lg border border-jarvis-border px-3 py-2 text-sm"
                      >
                        Retry
                      </button>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </SecondaryShell>
  );
}
