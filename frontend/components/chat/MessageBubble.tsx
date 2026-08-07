"use client";

import {
  Copy,
  Check,
  RefreshCw,
  Download,
  Share2,
  Pencil,
  Sparkles,
  Image as ImageIcon,
  Eraser,
  Layers,
  Music,
  Mic2,
} from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { MediaAsset, Message, OsJobSummary } from "@/types";
import { cn, forceDownload } from "@/lib/utils";
import { api } from "@/services/api";

interface MessageBubbleProps {
  message: Message;
  onRegenerate?: () => void;
  onImprove?: () => void;
  onEdit?: () => void;
  regenerating?: boolean;
  onImageTool?: (
    tool: "upscale" | "remove_bg" | "variations",
    asset: MediaAsset
  ) => void;
  onVideoTool?: (
    tool: "regenerate" | "change_voice" | "add_music",
    asset: MediaAsset
  ) => void;
}

export function MessageBubble({
  message,
  onRegenerate,
  onImprove,
  onEdit,
  regenerating,
  onImageTool,
  onVideoTool,
}: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const [copiedPrompt, setCopiedPrompt] = useState(false);
  const isUser = message.role === "user";
  const assets = message.assets || [];
  const jobs = message.jobs || [];
  const linkedFiles = extractFileLinks(message.content);
  const allAssets =
    assets.length > 0
      ? assets
      : linkedFiles.map((f, i) => ({
          id: `link-${i}`,
          kind: f.kind,
          title: f.title,
          url: f.url,
        }));

  function extractPrompt(text: string): string {
    const patterns = [
      /\*\*Flux:\*\*\s*([\s\S]+?)(?:\n\*\*|\n\n|$)/i,
      /\*\*FLUX:\*\*\s*([\s\S]+?)(?:\n\*\*|\n\n|$)/i,
      /\*\*DALL·E[^\n]*:\*\*\s*([\s\S]+?)(?:\n\*\*|\n\n|$)/i,
      /\*\*Midjourney:\*\*\s*([\s\S]+?)(?:\n\*\*|\n\n|$)/i,
      /\*\*AI video prompt:\*\*\s*([\s\S]+?)(?:\n\*\*|\n\n|$)/i,
    ];
    for (const re of patterns) {
      const m = text.match(re);
      if (m?.[1]?.trim()) return m[1].trim().replace(/\s+/g, " ");
    }
    return "";
  }

  async function copy() {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  async function copyPrompt() {
    const prompt = extractPrompt(message.content);
    if (!prompt) return;
    await navigator.clipboard.writeText(prompt);
    setCopiedPrompt(true);
    setTimeout(() => setCopiedPrompt(false), 1500);
  }

  function downloadText() {
    const blob = new Blob([message.content], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `lucero-${message.id.slice(0, 8)}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function share() {
    try {
      if (navigator.share) {
        await navigator.share({
          title: "L.U.C.E.R.O",
          text: message.content.slice(0, 500),
        });
      } else {
        await copy();
      }
    } catch {
      /* dismissed */
    }
  }

  return (
    <div
      className={cn(
        "group animate-fadeIn flex w-full",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      <div
        className={cn(
          "max-w-[min(720px,92%)] rounded-2xl px-4 py-3 text-sm",
          isUser
            ? "bg-jarvis-accent/15 border border-jarvis-accent/30 text-jarvis-text"
            : "bg-jarvis-elevated border border-jarvis-border"
        )}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap leading-relaxed">{message.content}</p>
        ) : (
          <div className="prose-jarvis">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                a: ({ href, children }) => {
                  const label = String(children);
                  const isDownload =
                    /download|png|pdf|mp4/i.test(label) ||
                    /\.(png|pdf|jpg|jpeg|mp4)(\?|$)/i.test(href || "");
                  if (isDownload && href) {
                    return (
                      <button
                        type="button"
                        onClick={() => {
                          const name = /pdf/i.test(label)
                            ? "lucero-flyer.pdf"
                            : /mp4/i.test(label)
                              ? "lucero-video.mp4"
                              : "lucero-flyer.png";
                          void forceDownload(href, name);
                        }}
                        className="my-2 inline-flex items-center gap-2 rounded-lg border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-3 py-2 text-sm font-medium text-jarvis-cyan hover:bg-jarvis-cyan/20"
                      >
                        <Download size={14} />
                        {children}
                      </button>
                    );
                  }
                  return (
                    <a href={href} target="_blank" rel="noreferrer">
                      {children}
                    </a>
                  );
                },
              }}
            >
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {!isUser && jobs.length > 0 && (
          <div className="mt-3 space-y-2">
            {jobs.map((job) => (
              <JobChip key={job.id} job={job} />
            ))}
          </div>
        )}

        {!isUser && allAssets.length > 0 && (
          <div className="mt-3 space-y-3">
            {allAssets.map((asset) => (
              <AssetBlock
                key={asset.id}
                asset={asset}
                onImageTool={onImageTool}
                onVideoTool={onVideoTool}
                onRegenerate={onRegenerate}
                regenerating={regenerating}
              />
            ))}
          </div>
        )}

        {!isUser && (
          <div className="mt-3 flex flex-wrap items-center gap-1 opacity-100">
            <ActionBtn onClick={copy} label={copied ? "Copied" : "Copy"}>
              {copied ? <Check size={12} /> : <Copy size={12} />}
            </ActionBtn>
            {extractPrompt(message.content) && (
              <ActionBtn
                onClick={copyPrompt}
                label={copiedPrompt ? "Prompt copied" : "Copy Prompt"}
              >
                {copiedPrompt ? <Check size={12} /> : <Copy size={12} />}
              </ActionBtn>
            )}
            {onEdit && (
              <ActionBtn onClick={onEdit} label="Edit">
                <Pencil size={12} />
              </ActionBtn>
            )}
            {onImprove && (
              <ActionBtn onClick={onImprove} label="Improve">
                <Sparkles size={12} />
              </ActionBtn>
            )}
            {onRegenerate && (
              <ActionBtn
                onClick={onRegenerate}
                label="Regenerate"
                disabled={regenerating}
              >
                <RefreshCw
                  size={12}
                  className={regenerating ? "animate-spin" : ""}
                />
              </ActionBtn>
            )}
            <ActionBtn onClick={downloadText} label="Download">
              <Download size={12} />
            </ActionBtn>
            <ActionBtn onClick={share} label="Share">
              <Share2 size={12} />
            </ActionBtn>
          </div>
        )}
      </div>
    </div>
  );
}

function extractFileLinks(
  text: string
): Array<{ title: string; url: string; kind: string }> {
  const out: Array<{ title: string; url: string; kind: string }> = [];
  const seen = new Set<string>();
  const re = /\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text || ""))) {
    const title = m[1].replace(/⬇️\s*/g, "").trim();
    const url = m[2];
    if (seen.has(url)) continue;
    seen.add(url);
    const lower = `${title} ${url}`.toLowerCase();
    let kind = "other";
    if (lower.includes("pdf") || url.includes(".pdf")) kind = "pdf";
    else if (
      lower.includes("png") ||
      lower.includes("jpg") ||
      lower.includes("image") ||
      url.includes(".png")
    )
      kind = "image";
    else if (lower.includes("mp4") || lower.includes("video")) kind = "video";
    out.push({ title, url, kind });
  }
  // Also bare image markdown ![alt](url)
  const imgRe = /!\[([^\]]*)\]\((https?:\/\/[^)]+)\)/g;
  while ((m = imgRe.exec(text || ""))) {
    const url = m[2];
    if (seen.has(url)) continue;
    seen.add(url);
    out.push({ title: m[1] || "Image", url, kind: "image" });
  }
  return out;
}

function ActionBtn({
  children,
  label,
  onClick,
  disabled,
}: {
  children: React.ReactNode;
  label: string;
  onClick: () => void;
  disabled?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] text-jarvis-muted hover:text-jarvis-text hover:bg-jarvis-bg disabled:opacity-50"
    >
      {children}
      {label}
    </button>
  );
}

function JobChip({ job }: { job: OsJobSummary }) {
  const running = job.status === "queued" || job.status === "running";
  return (
    <div className="rounded-lg border border-jarvis-border bg-jarvis-bg/60 px-3 py-2 text-[11px]">
      <div className="flex items-center justify-between gap-2">
        <span className="font-medium text-jarvis-text">
          {job.task_type.replace(/_/g, " ")}
        </span>
        <span
          className={cn(
            "uppercase tracking-wide",
            job.status === "succeeded" && "text-emerald-400",
            job.status === "failed" && "text-jarvis-danger",
            running && "text-jarvis-accent"
          )}
        >
          {job.status}
          {running && typeof job.progress === "number"
            ? ` ${job.progress}%`
            : ""}
        </span>
      </div>
      {job.progress_detail && (
        <p className="mt-1 text-jarvis-muted">{job.progress_detail}</p>
      )}
      {job.error_message && (
        <p className="mt-1 text-jarvis-danger">{job.error_message}</p>
      )}
    </div>
  );
}

function AssetBlock({
  asset,
  onImageTool,
  onVideoTool,
  onRegenerate,
  regenerating,
}: {
  asset: MediaAsset;
  onImageTool?: MessageBubbleProps["onImageTool"];
  onVideoTool?: MessageBubbleProps["onVideoTool"];
  onRegenerate?: () => void;
  regenerating?: boolean;
}) {
  const [downloading, setDownloading] = useState(false);

  async function downloadMedia() {
    if (!asset.url || downloading) return;
    setDownloading(true);
    try {
      const kind = (asset.kind || "").toLowerCase();
      const mime = (asset.mime || "").toLowerCase();
      let ext = "bin";
      if (kind === "pdf" || mime.includes("pdf")) ext = "pdf";
      else if (kind === "image" || mime.includes("png")) ext = "png";
      else if (mime.includes("jpeg") || mime.includes("jpg")) ext = "jpg";
      else if (kind === "video" || mime.includes("mp4")) ext = "mp4";
      const safe =
        (asset.title || "lucero-asset")
          .replace(/[^\w\-]+/g, "-")
          .replace(/-+/g, "-")
          .slice(0, 60) || "lucero-asset";
      const filename = `${safe}.${ext}`;

      // UUID assets → authenticated proxy (forces save, not navigate)
      const looksLikeUuid =
        /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
          asset.id
        );
      if (looksLikeUuid) {
        try {
          await api.osDownloadAsset(asset.id, filename);
          return;
        } catch {
          /* fall through to public URL blob download */
        }
      }
      await forceDownload(asset.url, filename);
    } finally {
      setDownloading(false);
    }
  }

  if (asset.kind === "image") {
    return (
      <div className="overflow-hidden rounded-xl border border-jarvis-cyan/40 bg-jarvis-bg/40">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={asset.url}
          alt={asset.title}
          className="max-h-[420px] w-full object-contain bg-black/30"
        />
        <div className="flex flex-wrap gap-2 border-t border-jarvis-border p-3">
          <button
            type="button"
            onClick={downloadMedia}
            disabled={downloading}
            className="inline-flex items-center gap-2 rounded-lg border border-jarvis-cyan/50 bg-jarvis-cyan/15 px-3 py-2 text-xs font-semibold text-jarvis-cyan hover:bg-jarvis-cyan/25 disabled:opacity-50"
          >
            <Download size={14} />
            {downloading ? "Saving…" : "Download PNG"}
          </button>
          <ActionBtn
            label="Upscale"
            onClick={() => onImageTool?.("upscale", asset)}
          >
            <ImageIcon size={12} />
          </ActionBtn>
          <ActionBtn
            label="Remove BG"
            onClick={() => onImageTool?.("remove_bg", asset)}
          >
            <Eraser size={12} />
          </ActionBtn>
          <ActionBtn
            label="Variations"
            onClick={() => onImageTool?.("variations", asset)}
          >
            <Layers size={12} />
          </ActionBtn>
          {onRegenerate && (
            <ActionBtn
              label="Regenerate"
              onClick={onRegenerate}
              disabled={regenerating}
            >
              <RefreshCw
                size={12}
                className={regenerating ? "animate-spin" : ""}
              />
            </ActionBtn>
          )}
        </div>
      </div>
    );
  }

  if (asset.kind === "pdf" || asset.mime === "application/pdf") {
    return (
      <div className="rounded-xl border border-jarvis-cyan/40 bg-jarvis-bg/40 p-3 space-y-2">
        <p className="text-[12px] text-jarvis-text font-medium">
          {asset.title || "Print-ready PDF"}
        </p>
        <p className="text-[11px] text-jarvis-muted">
          300 DPI print file — download and send to your printer.
        </p>
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={downloadMedia}
            disabled={downloading}
            className="inline-flex items-center gap-2 rounded-lg border border-jarvis-cyan/50 bg-jarvis-cyan/15 px-3 py-2 text-xs font-semibold text-jarvis-cyan hover:bg-jarvis-cyan/25 disabled:opacity-50"
          >
            <Download size={14} />
            {downloading ? "Saving…" : "Download PDF"}
          </button>
          {onRegenerate && (
            <ActionBtn label="Regenerate" onClick={onRegenerate}>
              <RefreshCw size={12} />
            </ActionBtn>
          )}
        </div>
      </div>
    );
  }

  if (
    asset.kind === "other" ||
    (asset.mime || "").includes("presentation")
  ) {
    return (
      <div className="rounded-xl border border-jarvis-border p-3 space-y-2">
        <p className="text-[12px] text-jarvis-text font-medium">
          {asset.title || "Presentation"}
        </p>
        <ActionBtn label="Download PPTX" onClick={downloadMedia}>
          <Download size={12} />
        </ActionBtn>
      </div>
    );
  }

  if (asset.kind === "video") {
    return (
      <div className="overflow-hidden rounded-xl border border-jarvis-border">
        <video src={asset.url} controls className="max-h-[420px] w-full bg-black" />
        <div className="flex flex-wrap gap-1 border-t border-jarvis-border p-2">
          <ActionBtn
            label="Regenerate"
            onClick={() => onVideoTool?.("regenerate", asset)}
          >
            <RefreshCw size={12} />
          </ActionBtn>
          <ActionBtn
            label="Change Voice"
            onClick={() => onVideoTool?.("change_voice", asset)}
          >
            <Mic2 size={12} />
          </ActionBtn>
          <ActionBtn
            label="Add Music"
            onClick={() => onVideoTool?.("add_music", asset)}
          >
            <Music size={12} />
          </ActionBtn>
          <ActionBtn label="Download MP4" onClick={downloadMedia}>
            <Download size={12} />
          </ActionBtn>
        </div>
      </div>
    );
  }

  if (asset.kind === "audio") {
    return (
      <div className="rounded-xl border border-jarvis-border p-3">
        <p className="mb-2 text-[11px] text-jarvis-muted">{asset.title}</p>
        <audio src={asset.url} controls className="w-full" />
      </div>
    );
  }

  return null;
}

export function TypingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="rounded-2xl border border-jarvis-border bg-jarvis-elevated px-4 py-3">
        <div className="flex gap-1.5">
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-jarvis-muted" />
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-jarvis-muted [animation-delay:150ms]" />
          <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-jarvis-muted [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  );
}
