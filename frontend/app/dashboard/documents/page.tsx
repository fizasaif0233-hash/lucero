"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import { FileUp, Loader2, Trash2 } from "lucide-react";
import { SecondaryShell } from "@/components/jarvis/SecondaryShell";
import { api } from "@/services/api";
import type { BusinessDocument } from "@/types";
import { formatRelativeTime } from "@/lib/utils";

export default function DocumentsPage() {
  const [docs, setDocs] = useState<BusinessDocument[]>([]);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const list = await api.documents();
      setDocs(list);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function onUpload(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const form = e.currentTarget;
    const input = form.elements.namedItem("file") as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    try {
      await api.uploadDocument(file);
      form.reset();
      await load();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setUploading(false);
    }
  }

  async function remove(id: string) {
    await api.deleteDocument(id);
    await load();
  }

  return (
    <SecondaryShell title="Documents">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="mx-auto max-w-3xl animate-fadeIn">
          <h1 className="font-display text-3xl mb-2 tracking-wide">Documents</h1>
          <p className="text-sm text-jarvis-muted mb-8">
            Upload PDF, TXT, DOCX, CSV, or XLSX. Shared knowledge also comes from
            Assets plus anthonywarrenmckinzy.com and 759inc.blue.
          </p>

          <form
            onSubmit={onUpload}
            className="mb-8 rounded-2xl border border-dashed border-jarvis-border bg-jarvis-panel/50 p-8 text-center"
          >
            <FileUp className="mx-auto mb-3 text-jarvis-accent" size={28} />
            <input
              name="file"
              type="file"
              accept=".pdf,.txt,.docx,.csv,.xlsx"
              required
              className="mx-auto block text-sm text-jarvis-muted file:mr-3 file:rounded-lg file:border-0 file:bg-jarvis-elevated file:px-3 file:py-1.5 file:text-jarvis-text"
            />
            <button
              type="submit"
              disabled={uploading}
              className="mt-4 inline-flex items-center gap-2 rounded-lg bg-jarvis-cyan px-4 py-2 text-sm font-medium text-jarvis-bg hover:bg-jarvis-accentDim disabled:opacity-50"
            >
              {uploading && <Loader2 size={16} className="animate-spin" />}
              {uploading ? "Processing…" : "Upload & index"}
            </button>
          </form>

          {error && (
            <p className="mb-4 text-sm text-jarvis-danger">{error}</p>
          )}

          <div className="space-y-2">
            {docs.length === 0 && (
              <p className="text-sm text-jarvis-muted py-8 text-center">
                No documents yet
              </p>
            )}
            {docs.map((d) => (
              <div
                key={d.id}
                className="flex items-center justify-between gap-3 rounded-xl border border-jarvis-border bg-jarvis-elevated/60 px-4 py-3"
              >
                <div className="min-w-0">
                  <p className="text-sm truncate">{d.original_filename}</p>
                  <p className="text-[11px] text-jarvis-muted mt-0.5">
                    {d.file_type.toUpperCase()} · {d.status}
                    {d.status === "ready" ? ` · ${d.chunk_count} chunks` : ""}
                    {" · "}
                    {formatRelativeTime(d.created_at)}
                  </p>
                  {d.error_message && (
                    <p className="text-[11px] text-jarvis-danger mt-1 truncate">
                      {d.error_message}
                    </p>
                  )}
                </div>
                <button
                  onClick={() => remove(d.id)}
                  className="p-2 text-jarvis-muted hover:text-jarvis-danger"
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
