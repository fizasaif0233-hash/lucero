"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import { ArrowUp, Plus, Trash2 } from "lucide-react";
import { MessageBubble, TypingIndicator } from "@/components/chat/MessageBubble";
import { formatRelativeTime, cn } from "@/lib/utils";
import type { Conversation, Message } from "@/types";

interface ChatPanelProps {
  conversations: Conversation[];
  activeId: string | null;
  messages: Message[];
  streaming: boolean;
  streamBuffer: string;
  error: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onSend: (text: string) => void;
  onRegenerate: (message: Message) => void;
  onImprove?: (message: Message) => void;
  onEdit?: (message: Message) => void;
  onImageTool?: (
    tool: "upscale" | "remove_bg" | "variations",
    asset: import("@/types").MediaAsset,
    message: Message
  ) => void;
  onVideoTool?: (
    tool: "regenerate" | "change_voice" | "add_music",
    asset: import("@/types").MediaAsset,
    message: Message
  ) => void;
}

export function ChatPanel({
  conversations,
  activeId,
  messages,
  streaming,
  streamBuffer,
  error,
  onSelect,
  onNew,
  onDelete,
  onSend,
  onRegenerate,
  onImprove,
  onEdit,
  onImageTool,
  onVideoTool,
}: ChatPanelProps) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamBuffer, streaming]);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() || streaming) return;
    const text = input;
    setInput("");
    onSend(text);
  }

  return (
    <div className="flex h-full min-h-0">
      {/* Conversation list */}
      <div className="hidden md:flex w-64 shrink-0 flex-col border-r border-jarvis-border bg-jarvis-panel/30">
        <div className="flex items-center justify-between px-3 py-3 border-b border-jarvis-border">
          <span className="text-xs uppercase tracking-wider text-jarvis-muted">
            Conversations
          </span>
          <button
            onClick={onNew}
            className="rounded-md p-1.5 text-jarvis-muted hover:text-jarvis-accent hover:bg-jarvis-elevated"
            title="New chat"
          >
            <Plus size={16} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {conversations.length === 0 && (
            <p className="px-2 py-6 text-center text-xs text-jarvis-muted">
              No conversations yet
            </p>
          )}
          {conversations.map((c) => (
            <div
              key={c.id}
              className={cn(
                "group flex items-start gap-1 rounded-lg px-2 py-2 cursor-pointer transition",
                activeId === c.id
                  ? "bg-jarvis-elevated border border-jarvis-border"
                  : "hover:bg-jarvis-elevated/50"
              )}
            >
              <button
                className="flex-1 text-left min-w-0"
                onClick={() => onSelect(c.id)}
              >
                <p className="text-sm truncate">{c.title}</p>
                <p className="text-[11px] text-jarvis-muted mt-0.5">
                  {formatRelativeTime(c.updated_at)}
                </p>
              </button>
              <button
                onClick={() => onDelete(c.id)}
                className="opacity-0 group-hover:opacity-100 p-1 text-jarvis-muted hover:text-jarvis-danger"
                title="Delete"
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Main chat */}
      <div className="flex flex-1 min-w-0 flex-col">
        <div ref={listRef} className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
          {messages.length === 0 && !streaming && (
            <div className="h-full flex flex-col items-center justify-center text-center px-6">
              <p className="font-display text-4xl mb-3">L.U.C.E.R.O</p>
              <p className="text-jarvis-muted max-w-md text-sm leading-relaxed">
                Your executive business assistant. Ask about planning, documents,
                marketing, operations — grounded in your knowledge base.
              </p>
            </div>
          )}

          {messages.map((m) => (
            <MessageBubble
              key={m.id}
              message={m}
              regenerating={streaming}
              onRegenerate={
                m.role === "assistant" ? () => onRegenerate(m) : undefined
              }
              onImprove={
                m.role === "assistant" && onImprove
                  ? () => onImprove(m)
                  : undefined
              }
              onEdit={
                m.role === "assistant" && onEdit ? () => onEdit(m) : undefined
              }
              onImageTool={
                onImageTool
                  ? (tool, asset) => onImageTool(tool, asset, m)
                  : undefined
              }
              onVideoTool={
                onVideoTool
                  ? (tool, asset) => onVideoTool(tool, asset, m)
                  : undefined
              }
            />
          ))}

          {streaming && streamBuffer && (
            <MessageBubble
              message={{
                id: "streaming",
                conversation_id: activeId || "pending",
                role: "assistant",
                content: streamBuffer,
                created_at: new Date().toISOString(),
              }}
            />
          )}

          {streaming && !streamBuffer && <TypingIndicator />}

          {error && (
            <p className="text-center text-sm text-jarvis-danger">{error}</p>
          )}

          <div ref={bottomRef} />
        </div>

        <form
          onSubmit={submit}
          className="border-t border-jarvis-border p-4 bg-jarvis-panel/40"
        >
          <div className="mx-auto flex max-w-3xl items-end gap-2 rounded-2xl border border-jarvis-border bg-jarvis-bg px-3 py-2 focus-within:border-jarvis-accent/60">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  submit(e);
                }
              }}
              rows={1}
              placeholder="Message L.U.C.E.R.O…"
              className="max-h-40 min-h-[44px] flex-1 resize-none bg-transparent py-2.5 text-sm outline-none placeholder:text-jarvis-muted"
            />
            <button
              type="submit"
              disabled={streaming || !input.trim()}
              className="mb-1 rounded-xl bg-jarvis-accent p-2.5 text-jarvis-bg hover:bg-jarvis-accentDim disabled:opacity-40 transition"
            >
              <ArrowUp size={18} />
            </button>
          </div>
          <p className="mt-2 text-center text-[11px] text-jarvis-muted">
            L.U.C.E.R.O uses your uploaded documents. It will not invent business facts.
          </p>
        </form>
      </div>
    </div>
  );
}
