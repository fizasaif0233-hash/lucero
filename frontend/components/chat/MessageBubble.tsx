"use client";

import { Copy, Check, RefreshCw } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { Message } from "@/types";
import { cn } from "@/lib/utils";

interface MessageBubbleProps {
  message: Message;
  onRegenerate?: () => void;
  regenerating?: boolean;
}

export function MessageBubble({
  message,
  onRegenerate,
  regenerating,
}: MessageBubbleProps) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === "user";

  async function copy() {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
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
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {!isUser && (
          <div className="mt-3 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition">
            <button
              onClick={copy}
              className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] text-jarvis-muted hover:text-jarvis-text hover:bg-jarvis-bg"
            >
              {copied ? <Check size={12} /> : <Copy size={12} />}
              {copied ? "Copied" : "Copy"}
            </button>
            {onRegenerate && (
              <button
                onClick={onRegenerate}
                disabled={regenerating}
                className="inline-flex items-center gap-1.5 rounded-md px-2 py-1 text-[11px] text-jarvis-muted hover:text-jarvis-text hover:bg-jarvis-bg disabled:opacity-50"
              >
                <RefreshCw size={12} className={regenerating ? "animate-spin" : ""} />
                Regenerate
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function TypingIndicator() {
  return (
    <div className="flex justify-start animate-fadeIn">
      <div className="rounded-2xl border border-jarvis-border bg-jarvis-elevated px-4 py-3">
        <div className="flex items-center gap-1.5">
          {[0, 1, 2].map((i) => (
            <span
              key={i}
              className="h-1.5 w-1.5 rounded-full bg-jarvis-accent animate-pulseDot"
              style={{ animationDelay: `${i * 0.2}s` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}
