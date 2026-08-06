"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { Trash2 } from "lucide-react";
import { SecondaryShell } from "@/components/jarvis/SecondaryShell";
import { api } from "@/services/api";
import type { MemoryItem } from "@/types";
import { formatRelativeTime } from "@/lib/utils";

export default function MemoryPage() {
  const [items, setItems] = useState<MemoryItem[]>([]);
  const [content, setContent] = useState("");
  const [category, setCategory] = useState("general");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    try {
      setItems(await api.memory());
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    if (!content.trim()) return;
    setSaving(true);
    setError(null);
    try {
      await api.createMemory({ content: content.trim(), category });
      setContent("");
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  async function remove(id: string) {
    await api.deleteMemory(id);
    await load();
  }

  return (
    <SecondaryShell title="Memory">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="mx-auto max-w-3xl animate-fadeIn">
          <h1 className="font-display text-3xl mb-2 tracking-wide">Memory</h1>
          <p className="text-sm text-jarvis-muted mb-8">
            Long-term business facts L.U.C.E.R.O should remember across conversations.
          </p>

          <form
            onSubmit={onSubmit}
            className="mb-8 rounded-2xl border border-jarvis-border bg-jarvis-panel/50 p-5 space-y-3"
          >
            <textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              rows={3}
              placeholder="e.g. Tequila brand launches in Q3; restaurant seating capacity is 84…"
              className="w-full rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2.5 text-sm outline-none focus:border-jarvis-accent resize-y"
            />
            <div className="flex flex-wrap items-center gap-3">
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="rounded-lg border border-jarvis-border bg-jarvis-bg px-3 py-2 text-sm outline-none"
              >
                <option value="general">General</option>
                <option value="tequila">Tequila</option>
                <option value="token">Token</option>
                <option value="restaurant">Restaurant</option>
                <option value="marketing">Marketing</option>
              </select>
              <button
                type="submit"
                disabled={saving || !content.trim()}
                className="rounded-lg bg-jarvis-accent px-4 py-2 text-sm font-medium text-jarvis-bg hover:bg-jarvis-accentDim disabled:opacity-50"
              >
                {saving ? "Saving…" : "Save memory"}
              </button>
            </div>
          </form>

          {error && (
            <p className="mb-4 text-sm text-jarvis-danger">{error}</p>
          )}

          <div className="space-y-2">
            {items.length === 0 && (
              <p className="text-sm text-jarvis-muted py-8 text-center">
                No memories yet
              </p>
            )}
            {items.map((m) => (
              <div
                key={m.id}
                className="flex items-start justify-between gap-3 rounded-xl border border-jarvis-border bg-jarvis-elevated/60 px-4 py-3"
              >
                <div className="min-w-0">
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">
                    {m.content}
                  </p>
                  <p className="text-[11px] text-jarvis-muted mt-1 capitalize">
                    {m.category} · {formatRelativeTime(m.updated_at)}
                  </p>
                </div>
                <button
                  onClick={() => remove(m.id)}
                  className="p-2 text-jarvis-muted hover:text-jarvis-danger shrink-0"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            ))}
          </div>
        </div>
      </div>
    </SecondaryShell>
  );
}
