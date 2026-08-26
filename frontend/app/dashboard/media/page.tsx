"use client";

import { useCallback, useEffect, useState } from "react";
import { Download, ImageIcon, Loader2, RefreshCw } from "lucide-react";
import { SecondaryShell } from "@/components/jarvis/SecondaryShell";
import { api } from "@/services/api";
import { downloadViaProxy } from "@/lib/download";
import { formatRelativeTime } from "@/lib/utils";

type GenAsset = {
  id: string;
  kind: string;
  title: string;
  public_url?: string | null;
  mime?: string;
  created_at?: string;
};

export default function GeneratedMediaPage() {
  const [assets, setAssets] = useState<GenAsset[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.osListAssets();
      setAssets(res.assets || []);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function saveAsset(asset: GenAsset) {
    const url = asset.public_url;
    if (!url) return;
    setBusyId(asset.id);
    try {
      const mime = (asset.mime || "").toLowerCase();
      const kind = (asset.kind || "").toLowerCase();
      let ext = "bin";
      if (kind === "pdf" || mime.includes("pdf")) ext = "pdf";
      else if (kind === "image" || mime.includes("png")) ext = "png";
      else if (mime.includes("jpeg") || mime.includes("jpg")) ext = "jpg";
      else if (kind === "video" || mime.includes("mp4")) ext = "mp4";
      const name =
        (asset.title || "lucero-asset")
          .replace(/[^\w\-]+/g, "-")
          .slice(0, 50) + `.${ext}`;
      try {
        await api.osDownloadAsset(asset.id, name);
      } catch {
        await downloadViaProxy(url, name);
      }
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusyId(null);
    }
  }

  const images = assets.filter(
    (a) =>
      a.kind === "image" ||
      (a.mime || "").includes("png") ||
      (a.mime || "").includes("jpeg") ||
      (a.mime || "").includes("image")
  );
  const others = assets.filter((a) => !images.includes(a));

  return (
    <SecondaryShell title="Generated Media">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="mx-auto max-w-6xl animate-fadeIn">
          <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h1 className="font-display text-3xl tracking-wide mb-2">
                Generated Media
              </h1>
              <p className="text-sm text-jarvis-muted max-w-xl">
                History of images, PDFs, and files Lucero created —
                flyers now use the official Blue Prince 21 bottles.
              </p>
            </div>
            <button
              type="button"
              onClick={load}
              className="inline-flex items-center gap-2 rounded-lg border border-jarvis-border px-3 py-2 text-sm text-jarvis-muted hover:text-jarvis-text"
            >
              <RefreshCw size={14} className={loading ? "animate-spin" : ""} />
              Refresh
            </button>
          </div>

          <section className="mb-10">
            <div className="mb-4 flex items-end justify-between gap-3">
              <h2 className="text-xs uppercase tracking-[0.16em] text-jarvis-cyan">
                Official bottles
              </h2>
              <a
                href="/dashboard/brand"
                className="text-[11px] text-jarvis-cyan hover:underline"
              >
                Magazine flyers
              </a>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {[
                ["/brand/product/blanco.jpeg", "Tequila Blanco"],
                ["/brand/product/anejo.jpeg", "Tequila Añejo"],
                ["/brand/product/pair.jpeg", "Blanco & Añejo"],
              ].map(([src, label]) => (
                <figure
                  key={src}
                  className="overflow-hidden rounded-xl border border-jarvis-border bg-jarvis-panel/50"
                >
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={src} alt={label} className="h-48 w-full object-cover bg-black/40" />
                  <figcaption className="px-3 py-2 text-sm">{label}</figcaption>
                </figure>
              ))}
            </div>
          </section>

          {error && (
            <p className="mb-4 text-sm text-jarvis-danger">{error}</p>
          )}

          {loading && assets.length === 0 ? (
            <div className="flex items-center gap-2 text-jarvis-muted text-sm">
              <Loader2 size={16} className="animate-spin" />
              Loading your media library…
            </div>
          ) : assets.length === 0 ? (
            <div className="rounded-2xl border border-dashed border-jarvis-border bg-jarvis-panel/40 p-10 text-center">
              <ImageIcon className="mx-auto mb-3 text-jarvis-cyan" size={28} />
              <p className="text-jarvis-text font-medium">No generated files yet</p>
              <p className="mt-2 text-sm text-jarvis-muted">
                Ask Lucero to create a flyer, Facebook post, or landing page —
                finished PNGs/PDFs will show up here.
              </p>
            </div>
          ) : (
            <>
              {images.length > 0 && (
                <section className="mb-10">
                  <h2 className="mb-4 text-xs uppercase tracking-[0.16em] text-jarvis-cyan">
                    Images ({images.length})
                  </h2>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                    {images.map((asset) => (
                      <article
                        key={asset.id}
                        className="overflow-hidden rounded-xl border border-jarvis-border bg-jarvis-panel/50"
                      >
                        {asset.public_url ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img
                            src={asset.public_url}
                            alt={asset.title}
                            className="h-48 w-full object-cover bg-black/40"
                          />
                        ) : (
                          <div className="flex h-48 items-center justify-center bg-jarvis-elevated text-jarvis-muted text-sm">
                            No preview
                          </div>
                        )}
                        <div className="p-3 space-y-2">
                          <p className="text-sm text-jarvis-text line-clamp-2">
                            {asset.title || "Untitled"}
                          </p>
                          <p className="text-[11px] text-jarvis-muted">
                            {asset.created_at
                              ? formatRelativeTime(asset.created_at)
                              : ""}
                          </p>
                          <button
                            type="button"
                            disabled={busyId === asset.id || !asset.public_url}
                            onClick={() => void saveAsset(asset)}
                            className="inline-flex items-center gap-2 rounded-lg border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-3 py-1.5 text-xs font-semibold text-jarvis-cyan hover:bg-jarvis-cyan/20 disabled:opacity-50"
                          >
                            <Download size={12} />
                            {busyId === asset.id ? "Saving…" : "Download"}
                          </button>
                        </div>
                      </article>
                    ))}
                  </div>
                </section>
              )}

              {others.length > 0 && (
                <section>
                  <h2 className="mb-4 text-xs uppercase tracking-[0.16em] text-jarvis-cyan">
                    Files ({others.length})
                  </h2>
                  <ul className="space-y-2">
                    {others.map((asset) => (
                      <li
                        key={asset.id}
                        className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-jarvis-border bg-jarvis-panel/50 px-4 py-3"
                      >
                        <div>
                          <p className="text-sm text-jarvis-text">
                            {asset.title || asset.kind}
                          </p>
                          <p className="text-[11px] text-jarvis-muted">
                            {asset.kind}
                            {asset.created_at
                              ? ` · ${formatRelativeTime(asset.created_at)}`
                              : ""}
                          </p>
                        </div>
                        <button
                          type="button"
                          disabled={busyId === asset.id || !asset.public_url}
                          onClick={() => void saveAsset(asset)}
                          className="inline-flex items-center gap-2 rounded-lg border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-3 py-1.5 text-xs font-semibold text-jarvis-cyan disabled:opacity-50"
                        >
                          <Download size={12} />
                          {busyId === asset.id ? "Saving…" : "Download"}
                        </button>
                      </li>
                    ))}
                  </ul>
                </section>
              )}
            </>
          )}
        </div>
      </div>
    </SecondaryShell>
  );
}
