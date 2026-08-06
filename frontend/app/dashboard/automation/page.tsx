"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bot,
  Calendar,
  Check,
  FileBarChart,
  History,
  Loader2,
  Mail,
  Megaphone,
  Pencil,
  Search,
  Users,
  Headphones,
  Play,
  X,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { SecondaryShell } from "@/components/jarvis/SecondaryShell";
import { api } from "@/services/api";
import type {
  AutomationHistoryItem,
  AutomationItem,
  AutomationModuleInfo,
  AutomationRun,
} from "@/types";
import { formatRelativeTime } from "@/lib/utils";

const ICONS: Record<string, React.ComponentType<{ size?: number }>> = {
  email: Mail,
  calendar: Calendar,
  marketing: Megaphone,
  research: Search,
  report: FileBarChart,
  support: Headphones,
  crm: Users,
};

const DEFAULT_PROMPTS: Record<string, string> = {
  email: "Email all distributors.",
  calendar: "Schedule a tequila tasting next Friday at 6 PM.",
  marketing: "Generate this week's marketing content.",
  research: "Research premium tequila distributors.",
  report: "Generate this week's executive business report.",
  support: "Create replies for today's customer messages.",
  crm: "Prioritize my CRM contacts and recommend follow-up actions.",
};

export default function AutomationPage() {
  const [modules, setModules] = useState<AutomationModuleInfo[]>([]);
  const [history, setHistory] = useState<AutomationHistoryItem[]>([]);
  const [activeRun, setActiveRun] = useState<AutomationRun | null>(null);
  const [editingItem, setEditingItem] = useState<AutomationItem | null>(null);
  const [promptDraft, setPromptDraft] = useState("");
  const [selectedModule, setSelectedModule] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [historyFilter, setHistoryFilter] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const [mods, runs] = await Promise.all([
        api.automationModules(),
        api.automationHistory(historyFilter || undefined),
      ]);
      setModules(mods);
      setHistory(runs);
    } catch (err) {
      setError((err as Error).message);
    }
  }, [historyFilter]);

  useEffect(() => {
    load();
  }, [load]);

  async function openRunDialog(moduleId: string) {
    setSelectedModule(moduleId);
    setPromptDraft(DEFAULT_PROMPTS[moduleId] || "");
    setError(null);
  }

  async function startAutomation() {
    if (!selectedModule || !promptDraft.trim()) return;
    setRunning(true);
    setError(null);
    try {
      const run = await api.automationStart({
        module: selectedModule,
        prompt: promptDraft.trim(),
      });
      setActiveRun(run);
      setSelectedModule(null);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setRunning(false);
    }
  }

  async function approve() {
    if (!activeRun) return;
    setActing(true);
    setError(null);
    try {
      const run = await api.automationApprove(activeRun.id);
      setActiveRun(run);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setActing(false);
    }
  }

  async function cancel() {
    if (!activeRun) return;
    setActing(true);
    try {
      const run = await api.automationCancel(activeRun.id);
      setActiveRun(run);
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setActing(false);
    }
  }

  async function openHistoryRun(id: string) {
    setError(null);
    try {
      const run = await api.automationRun(id);
      setActiveRun(run);
      setShowHistory(false);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function saveEdit() {
    if (!editingItem || !activeRun) return;
    setActing(true);
    try {
      await api.automationUpdateItem(editingItem.id, {
        title: editingItem.title,
        content: editingItem.content,
      });
      const run = await api.automationRun(activeRun.id);
      setActiveRun(run);
      setEditingItem(null);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setActing(false);
    }
  }

  const confirmation = useMemo(() => {
    const preview = activeRun?.preview || {};
    return (
      (preview.confirmation_prompt as string) ||
      "Review complete. Approve to execute this automation?"
    );
  }, [activeRun]);

  const canApprove =
    activeRun &&
    (activeRun.status === "awaiting_approval" ||
      activeRun.status === "draft_ready");

  return (
    <SecondaryShell title="Automation">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="mx-auto max-w-6xl animate-fadeIn">
          <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="font-display text-3xl tracking-wide mb-2">
                Automation
              </h1>
              <p className="text-sm text-jarvis-muted max-w-2xl">
                L.U.C.E.R.O prepares business tasks as drafts. You always review
                and approve before anything is executed.
              </p>
            </div>
            <button
              type="button"
              onClick={() => setShowHistory((v) => !v)}
              className="inline-flex items-center gap-2 rounded-xl border border-jarvis-border px-4 py-2 text-sm text-jarvis-muted hover:text-jarvis-cyan hover:border-jarvis-cyan/40"
            >
              <History size={16} />
              History
            </button>
          </div>

          {error && (
            <div className="mb-6 rounded-xl border border-jarvis-danger/40 bg-jarvis-danger/10 px-4 py-3 text-sm text-jarvis-danger">
              {error}
              <p className="mt-1 text-xs opacity-80">
                If this mentions a missing table, run{" "}
                <code className="font-mono">migrations/003_automation.sql</code>{" "}
                in Supabase.
              </p>
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {modules.map((mod) => {
              const Icon = ICONS[mod.id] || Bot;
              return (
                <div key={mod.id} className="hud-card flex flex-col p-5">
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div className="rounded-xl border border-jarvis-cyan/30 bg-jarvis-cyan/10 p-2.5 text-jarvis-cyan">
                      <Icon size={18} />
                    </div>
                    <span className="rounded-full border border-jarvis-border px-2 py-0.5 text-[10px] uppercase tracking-wider text-jarvis-muted">
                      {mod.status}
                    </span>
                  </div>
                  <h2 className="font-display text-lg tracking-wide mb-2">
                    {mod.title}
                  </h2>
                  <p className="text-sm text-jarvis-muted flex-1 mb-4">
                    {mod.description}
                  </p>
                  <p className="mb-4 text-xs text-jarvis-cyan/80 italic">
                    “{mod.example}”
                  </p>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => openRunDialog(mod.id)}
                      className="inline-flex flex-1 items-center justify-center gap-2 rounded-xl bg-jarvis-cyan/90 px-3 py-2.5 text-sm font-medium text-jarvis-bg hover:bg-jarvis-accent"
                    >
                      <Play size={14} />
                      Run
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setHistoryFilter(mod.id);
                        setShowHistory(true);
                      }}
                      className="rounded-xl border border-jarvis-border px-3 py-2.5 text-sm text-jarvis-muted hover:text-jarvis-cyan"
                    >
                      History
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Prompt dialog */}
      {selectedModule && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="hud-card w-full max-w-lg p-6">
            <h3 className="font-display text-xl mb-2 tracking-wide">
              Run automation
            </h3>
            <p className="text-sm text-jarvis-muted mb-4">
              Describe the task. L.U.C.E.R.O will prepare a draft for your
              approval — nothing sends automatically.
            </p>
            <textarea
              value={promptDraft}
              onChange={(e) => setPromptDraft(e.target.value)}
              rows={4}
              className="w-full rounded-xl border border-jarvis-border bg-jarvis-bg/80 px-3 py-2.5 text-sm outline-none focus:border-jarvis-cyan/60"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setSelectedModule(null)}
                className="rounded-xl border border-jarvis-border px-4 py-2 text-sm text-jarvis-muted"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={running || !promptDraft.trim()}
                onClick={startAutomation}
                className="inline-flex items-center gap-2 rounded-xl bg-jarvis-cyan px-4 py-2 text-sm font-medium text-jarvis-bg disabled:opacity-50"
              >
                {running && <Loader2 size={14} className="animate-spin" />}
                {running ? "Planning…" : "Prepare draft"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* History drawer */}
      {showHistory && (
        <div className="fixed inset-0 z-40 flex justify-end bg-black/50 backdrop-blur-sm">
          <div className="h-full w-full max-w-md border-l border-jarvis-border bg-jarvis-panel p-5 overflow-y-auto">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="font-display tracking-wide">History</h3>
              <button
                type="button"
                onClick={() => {
                  setShowHistory(false);
                  setHistoryFilter(null);
                }}
                className="text-jarvis-muted hover:text-jarvis-cyan"
              >
                <X size={18} />
              </button>
            </div>
            <div className="space-y-2">
              {history.length === 0 && (
                <p className="text-sm text-jarvis-muted">No runs yet.</p>
              )}
              {history.map((run) => (
                <button
                  key={run.id}
                  type="button"
                  onClick={() => openHistoryRun(run.id)}
                  className="w-full rounded-xl border border-jarvis-border bg-jarvis-elevated/40 px-3 py-3 text-left hover:border-jarvis-cyan/40"
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium">{run.title}</span>
                    <span className="text-[10px] uppercase text-jarvis-muted">
                      {run.status}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-jarvis-muted line-clamp-2">
                    {run.prompt}
                  </p>
                  <p className="mt-1 text-[10px] text-jarvis-muted">
                    {run.module}
                    {run.created_at
                      ? ` · ${formatRelativeTime(run.created_at)}`
                      : ""}
                  </p>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Preview / approval screen */}
      {activeRun && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-3 sm:p-6 backdrop-blur-sm">
          <div className="hud-card flex max-h-[92vh] w-full max-w-4xl flex-col overflow-hidden">
            <div className="flex items-start justify-between gap-3 border-b border-jarvis-border/70 px-5 py-4">
              <div>
                <p className="text-[10px] uppercase tracking-[0.16em] text-jarvis-cyan">
                  {activeRun.module} · {activeRun.status}
                </p>
                <h3 className="font-display text-xl tracking-wide mt-1">
                  {activeRun.title}
                </h3>
                {activeRun.plan_summary && (
                  <p className="mt-2 text-sm text-jarvis-muted">
                    {activeRun.plan_summary}
                  </p>
                )}
              </div>
              <button
                type="button"
                onClick={() => setActiveRun(null)}
                className="text-jarvis-muted hover:text-jarvis-cyan"
              >
                <X size={18} />
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
              {activeRun.error_message && (
                <p className="text-sm text-jarvis-danger">
                  {activeRun.error_message}
                </p>
              )}

              {activeRun.items.map((item) => (
                <div
                  key={item.id}
                  className="rounded-xl border border-jarvis-border bg-jarvis-elevated/50 p-4"
                >
                  <div className="mb-2 flex items-center justify-between gap-2">
                    <h4 className="text-sm font-medium">{item.title}</h4>
                    {canApprove && (
                      <button
                        type="button"
                        onClick={() => setEditingItem(item)}
                        className="inline-flex items-center gap-1 text-xs text-jarvis-muted hover:text-jarvis-cyan"
                      >
                        <Pencil size={12} />
                        Edit
                      </button>
                    )}
                  </div>
                  <ItemPreview item={item} />
                </div>
              ))}

              {activeRun.status === "executed" && (
                <div className="rounded-xl border border-jarvis-success/40 bg-jarvis-success/10 px-4 py-3 text-sm">
                  {(activeRun.result?.summary as string) ||
                    "Automation executed and saved to history."}
                </div>
              )}
            </div>

            <div className="border-t border-jarvis-border/70 px-5 py-4">
              {canApprove ? (
                <>
                  <p className="mb-3 text-sm text-jarvis-text">{confirmation}</p>
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      disabled={acting}
                      onClick={approve}
                      className="inline-flex items-center gap-2 rounded-xl bg-jarvis-cyan px-4 py-2.5 text-sm font-medium text-jarvis-bg disabled:opacity-50"
                    >
                      {acting ? (
                        <Loader2 size={14} className="animate-spin" />
                      ) : (
                        <Check size={14} />
                      )}
                      Approve
                    </button>
                    <button
                      type="button"
                      disabled={acting}
                      onClick={() =>
                        activeRun.items[0] && setEditingItem(activeRun.items[0])
                      }
                      className="inline-flex items-center gap-2 rounded-xl border border-jarvis-border px-4 py-2.5 text-sm text-jarvis-muted hover:text-jarvis-cyan"
                    >
                      <Pencil size={14} />
                      Edit
                    </button>
                    <button
                      type="button"
                      disabled={acting}
                      onClick={cancel}
                      className="inline-flex items-center gap-2 rounded-xl border border-jarvis-danger/40 px-4 py-2.5 text-sm text-jarvis-danger"
                    >
                      <X size={14} />
                      Cancel
                    </button>
                  </div>
                </>
              ) : (
                <button
                  type="button"
                  onClick={() => setActiveRun(null)}
                  className="rounded-xl border border-jarvis-border px-4 py-2.5 text-sm text-jarvis-muted"
                >
                  Close
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Edit modal */}
      {editingItem && (
        <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/70 p-4">
          <div className="hud-card w-full max-w-2xl p-5">
            <h3 className="font-display text-lg mb-3">Edit draft</h3>
            <input
              value={editingItem.title}
              onChange={(e) =>
                setEditingItem({ ...editingItem, title: e.target.value })
              }
              className="mb-3 w-full rounded-xl border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm"
            />
            <textarea
              value={JSON.stringify(editingItem.content, null, 2)}
              onChange={(e) => {
                try {
                  const parsed = JSON.parse(e.target.value);
                  setEditingItem({ ...editingItem, content: parsed });
                } catch {
                  /* keep typing */
                }
              }}
              rows={14}
              className="w-full rounded-xl border border-jarvis-border bg-jarvis-bg px-3 py-2 font-mono text-xs"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setEditingItem(null)}
                className="rounded-xl border border-jarvis-border px-4 py-2 text-sm"
              >
                Close
              </button>
              <button
                type="button"
                disabled={acting}
                onClick={saveEdit}
                className="rounded-xl bg-jarvis-cyan px-4 py-2 text-sm font-medium text-jarvis-bg"
              >
                Save edits
              </button>
            </div>
          </div>
        </div>
      )}
    </SecondaryShell>
  );
}

function ItemPreview({ item }: { item: AutomationItem }) {
  const c = item.content || {};

  if (item.item_type === "email" || item.item_type === "support_reply") {
    return (
      <div className="space-y-1 text-sm">
        {"to" in c && (
          <p className="text-jarvis-muted">
            To: <span className="text-jarvis-text">{String(c.to)}</span>
            {c.to_name ? ` (${String(c.to_name)})` : ""}
          </p>
        )}
        {"customer" in c && (
          <p className="text-jarvis-muted">
            Customer:{" "}
            <span className="text-jarvis-text">{String(c.customer)}</span>
          </p>
        )}
        {"subject" in c && (
          <p>
            <span className="text-jarvis-muted">Subject:</span>{" "}
            {String(c.subject)}
          </p>
        )}
        <pre className="mt-2 whitespace-pre-wrap rounded-lg bg-jarvis-bg/60 p-3 text-xs leading-relaxed">
          {String(c.body || "")}
        </pre>
      </div>
    );
  }

  if (item.item_type === "booking") {
    return (
      <div className="grid gap-1 text-sm">
        <p>
          <span className="text-jarvis-muted">When:</span>{" "}
          {String(c.starts_at || "")}
          {c.ends_at ? ` → ${String(c.ends_at)}` : ""}
        </p>
        {!!c.location && (
          <p>
            <span className="text-jarvis-muted">Where:</span>{" "}
            {String(c.location)}
          </p>
        )}
        {!!c.description && (
          <p className="text-jarvis-muted">{String(c.description)}</p>
        )}
      </div>
    );
  }

  if (item.item_type === "marketing") {
    return (
      <div className="text-sm">
        <p className="mb-1 text-[10px] uppercase tracking-wider text-jarvis-cyan">
          {String(c.channel || "")}
        </p>
        <pre className="whitespace-pre-wrap rounded-lg bg-jarvis-bg/60 p-3 text-xs">
          {String(c.body || "")}
        </pre>
      </div>
    );
  }

  if (item.item_type === "report") {
    return (
      <div className="prose-jarvis text-sm max-h-80 overflow-y-auto">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>
          {String(c.markdown || "")}
        </ReactMarkdown>
      </div>
    );
  }

  if (item.item_type === "crm_bucket") {
    const contacts = (c.contacts as Array<Record<string, string>>) || [];
    return (
      <div className="space-y-1">
        <p className="text-xs text-jarvis-muted mb-2">
          {contacts.length} contacts · {String(c.priority)}
        </p>
        {contacts.slice(0, 8).map((contact, i) => (
          <p key={i} className="text-xs">
            <span className="text-jarvis-text">{contact.company}</span>
            {contact.email ? (
              <span className="text-jarvis-muted"> · {contact.email}</span>
            ) : null}
          </p>
        ))}
      </div>
    );
  }

  if (item.item_type === "crm_followups") {
    const followups =
      (c.followups as Array<Record<string, string>>) || [];
    return (
      <ul className="space-y-2 text-sm">
        {followups.map((f, i) => (
          <li key={i} className="rounded-lg bg-jarvis-bg/50 px-3 py-2">
            <p className="font-medium">
              {f.company}{" "}
              <span className="text-[10px] uppercase text-jarvis-cyan">
                {f.priority}
              </span>
            </p>
            <p className="text-xs text-jarvis-muted">{f.action}</p>
          </li>
        ))}
      </ul>
    );
  }

  return (
    <pre className="overflow-x-auto rounded-lg bg-jarvis-bg/60 p-3 text-[11px]">
      {JSON.stringify(c, null, 2)}
    </pre>
  );
}
