"use client";

import { FormEvent, useEffect, useRef, useState } from "react";
import {
  Download,
  Mic,
  MicOff,
  Send,
  Trash2,
  Keyboard,
  Square,
  Maximize2,
  Minimize2,
  PanelRightClose,
  PanelRightOpen,
  Minus,
} from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import type { MediaAsset, Message } from "@/types";
import { cn } from "@/lib/utils";
import { MessageBubble } from "@/components/chat/MessageBubble";

export type ChatPanelSize = "minimized" | "compact" | "normal" | "large" | "max";

export const CHAT_SIZE_STORAGE_KEY = "lucero-chat-size";

interface ConversationPanelProps {
  messages: Message[];
  streamBuffer: string;
  streaming: boolean;
  agentProgress?: string | null;
  activeMode?: string | null;
  activeAgents?: Array<{ id: string; name: string }>;
  forcedAgentId?: string | null;
  onClearForcedAgent?: () => void;
  error: string | null;
  transcript: string;
  micOn: boolean;
  speaking?: boolean;
  panelSize: ChatPanelSize;
  onPanelSizeChange: (size: ChatPanelSize) => void;
  onToggleMic: () => void;
  onPushToTalk: () => void;
  onStopSpeaking?: () => void;
  onSend: (text: string) => void;
  onClear: () => void;
  onRegenerate?: (message: Message) => void;
  onImprove?: (message: Message) => void;
  onEdit?: (message: Message, instruction: string) => void;
  onImageTool?: (
    tool: "upscale" | "remove_bg" | "variations",
    asset: MediaAsset,
    message: Message
  ) => void;
  onVideoTool?: (
    tool: "regenerate" | "change_voice" | "add_music",
    asset: MediaAsset,
    message: Message
  ) => void;
}

const SIZE_CYCLE: ChatPanelSize[] = ["compact", "normal", "large", "max"];

export function ConversationPanel({
  messages,
  streamBuffer,
  streaming,
  agentProgress,
  activeMode,
  activeAgents,
  forcedAgentId,
  onClearForcedAgent,
  error,
  transcript,
  micOn,
  speaking,
  panelSize,
  onPanelSizeChange,
  onToggleMic,
  onPushToTalk,
  onStopSpeaking,
  onSend,
  onClear,
  onRegenerate,
  onImprove,
  onEdit,
  onImageTool,
  onVideoTool,
}: ConversationPanelProps) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamBuffer, streaming, agentProgress]);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!input.trim() || streaming) return;
    onStopSpeaking?.();
    const text = input;
    setInput("");
    onSend(text);
  }

  function exportConversation() {
    const body = messages
      .map((m) => `${m.role.toUpperCase()}: ${m.content}`)
      .join("\n\n");
    const blob = new Blob([body || "No messages"], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `lucero-conversation-${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
  }

  function enlarge() {
    const idx = SIZE_CYCLE.indexOf(
      panelSize === "minimized" ? "compact" : panelSize
    );
    const next = SIZE_CYCLE[Math.min(idx + 1, SIZE_CYCLE.length - 1)];
    onPanelSizeChange(next);
  }

  function shrink() {
    if (panelSize === "max") {
      onPanelSizeChange("large");
      return;
    }
    const idx = SIZE_CYCLE.indexOf(panelSize);
    if (idx <= 0) {
      onPanelSizeChange("minimized");
      return;
    }
    onPanelSizeChange(SIZE_CYCLE[idx - 1]);
  }

  if (panelSize === "minimized") {
    return (
      <div className="flex h-full min-h-0 flex-col items-center justify-start gap-2 py-2">
        <button
          type="button"
          onClick={() => onPanelSizeChange("normal")}
          className="hud-card flex w-11 flex-col items-center gap-2 px-2 py-3 text-jarvis-cyan hover:bg-jarvis-cyan/10"
          title="Open chat"
        >
          <PanelRightOpen size={18} />
          <span className="write-vertical text-[10px] uppercase tracking-[0.18em]">
            Chat
          </span>
          {messages.length > 0 && (
            <span className="rounded-full bg-jarvis-cyan/20 px-1.5 text-[10px] text-jarvis-cyan">
              {messages.length}
            </span>
          )}
        </button>
      </div>
    );
  }

  const textSize =
    panelSize === "compact"
      ? "text-[11px] leading-snug [&_.prose-jarvis]:text-[11px] [&_.prose-jarvis_p]:mb-2 [&_.prose-jarvis_h1]:text-sm [&_.prose-jarvis_h2]:text-sm [&_.prose-jarvis_h3]:text-xs [&_.prose-jarvis_li]:text-[11px] [&_.prose-jarvis_code]:text-[10px]"
      : panelSize === "large" || panelSize === "max"
        ? "text-[15px] leading-relaxed"
        : "text-sm leading-relaxed";

  const messagePad =
    panelSize === "compact" ? "px-2.5 py-2 space-y-2" : "px-4 py-4 space-y-3";

  return (
    <div className="flex h-full min-h-0 flex-col hud-card overflow-hidden">
      <div className="flex items-center justify-between gap-2 border-b border-jarvis-border/70 px-3 py-2.5 sm:px-4">
        <div className="min-w-0">
          <h2
            className={cn(
              "tracking-[0.14em] uppercase text-jarvis-cyan",
              panelSize === "compact" ? "text-[11px]" : "text-sm"
            )}
          >
            Conversation
          </h2>
          <p
            className={cn(
              "uppercase tracking-[0.12em] text-jarvis-muted",
              panelSize === "compact" ? "text-[9px]" : "text-[10px]"
            )}
          >
            {forcedAgentId
              ? `Agent locked · ${forcedAgentId}`
              : activeAgents && activeAgents.length
                ? activeAgents.map((a) => a.name).join(" → ")
                : panelSize === "max"
                  ? "Maximized"
                  : panelSize === "large"
                    ? "Large"
                    : panelSize === "compact"
                      ? "Compact"
                      : "Normal"}
          </p>
        </div>

        <div className="flex flex-wrap items-center justify-end gap-0.5">
          <div className="mr-1 hidden items-center rounded-lg border border-jarvis-border/70 p-0.5 sm:flex">
            {(
              [
                ["compact", "S"],
                ["normal", "M"],
                ["large", "L"],
                ["max", "XL"],
              ] as const
            ).map(([size, label]) => (
              <button
                key={size}
                type="button"
                onClick={() => onPanelSizeChange(size)}
                className={cn(
                  "rounded-md px-2 py-1 text-[10px] font-medium tracking-wide transition",
                  panelSize === size
                    ? "bg-jarvis-cyan/20 text-jarvis-cyan"
                    : "text-jarvis-muted hover:text-jarvis-text"
                )}
                title={
                  size === "compact"
                    ? "Compact"
                    : size === "normal"
                      ? "Normal"
                      : size === "large"
                        ? "Large"
                        : "Maximize"
                }
              >
                {label}
              </button>
            ))}
          </div>

          <button
            type="button"
            onClick={shrink}
            className="rounded-lg p-2 text-jarvis-muted hover:text-jarvis-cyan sm:hidden"
            title="Smaller"
          >
            <Minimize2 size={15} />
          </button>
          <button
            type="button"
            onClick={enlarge}
            className="rounded-lg p-2 text-jarvis-muted hover:text-jarvis-cyan sm:hidden"
            title="Larger"
          >
            <Maximize2 size={15} />
          </button>
          <button
            type="button"
            onClick={() =>
              onPanelSizeChange(panelSize === "max" ? "normal" : "max")
            }
            className="rounded-lg p-2 text-jarvis-muted hover:text-jarvis-cyan"
            title={panelSize === "max" ? "Exit maximize" : "Maximize chat"}
          >
            {panelSize === "max" ? (
              <PanelRightClose size={15} />
            ) : (
              <Maximize2 size={15} />
            )}
          </button>
          <button
            type="button"
            onClick={() => onPanelSizeChange("minimized")}
            className="rounded-lg p-2 text-jarvis-muted hover:text-jarvis-cyan"
            title="Minimize chat"
          >
            <Minus size={15} />
          </button>
          <button
            type="button"
            onClick={onClear}
            className="rounded-lg p-2 text-jarvis-muted hover:text-jarvis-danger"
            title="Clear"
          >
            <Trash2 size={15} />
          </button>
          <button
            type="button"
            onClick={exportConversation}
            className="rounded-lg p-2 text-jarvis-muted hover:text-jarvis-cyan"
            title="Export conversation"
          >
            <Download size={15} />
          </button>
        </div>
      </div>

      <div
        className={cn(
          "flex-1 overflow-y-auto",
          messagePad,
          textSize
        )}
      >
        {messages.length === 0 && !streaming && (
          <div className="rounded-xl border border-jarvis-border/60 bg-jarvis-elevated/50 px-4 py-3 text-jarvis-muted leading-relaxed">
            Hello, I am L.U.C.E.R.O — your AI business partner for 759 /
            Blue Prince21 McKinzy. Ask about your brand, token, distributors,
            financials, or say{" "}
            <span className="text-jarvis-cyan">“Find tequila investors”</span>{" "}
            to run research.
          </div>
        )}

        {streaming && agentProgress && !streamBuffer && (
          <div className="rounded-xl border border-jarvis-cyan/30 bg-jarvis-cyan/5 px-4 py-3 text-jarvis-cyan">
            <p className="text-[10px] uppercase tracking-[0.16em] text-jarvis-muted mb-1">
              {activeAgents?.[0]?.name ||
                (activeMode === "research" ? "Research agent" : "L.U.C.E.R.O")}
            </p>
            {agentProgress}
          </div>
        )}

        {forcedAgentId && (
          <div className="rounded-xl border border-jarvis-border/60 bg-jarvis-elevated/40 px-3 py-2 text-xs text-jarvis-muted flex items-center justify-between gap-2">
            <span>
              Chatting with <span className="text-jarvis-cyan">{forcedAgentId}</span>{" "}
              agent
            </span>
            <button
              type="button"
              onClick={onClearForcedAgent}
              className="text-jarvis-cyan hover:underline"
            >
              Use auto-router
            </button>
          </div>
        )}

        {messages.map((m) =>
          m.role === "assistant" ? (
            <MessageBubble
              key={m.id}
              message={m}
              regenerating={streaming}
              onRegenerate={
                onRegenerate ? () => onRegenerate(m) : undefined
              }
              onImprove={onImprove ? () => onImprove(m) : undefined}
              onEdit={
                onEdit
                  ? () => {
                      const instruction = window.prompt(
                        "How should I revise this?",
                        "Make it punchier and keep the same structure"
                      );
                      if (instruction?.trim()) onEdit(m, instruction.trim());
                    }
                  : undefined
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
          ) : (
            <div
              key={m.id}
              className={cn(
                "rounded-xl px-3 py-2.5 animate-fadeIn ml-6 bg-jarvis-cyan/10 border border-jarvis-cyan/30",
                panelSize === "compact" && "px-2 py-1.5"
              )}
            >
              <p
                className={cn(
                  "mb-1 uppercase tracking-wider text-jarvis-muted",
                  panelSize === "compact" ? "text-[9px]" : "text-[10px]"
                )}
              >
                You
              </p>
              <p className="whitespace-pre-wrap">{m.content}</p>
            </div>
          )
        )}

        {streaming && streamBuffer && (
          <div className="mr-2 rounded-xl border border-jarvis-border bg-jarvis-elevated/80 px-3 py-2.5">
            <p className="mb-1 text-[10px] uppercase tracking-wider text-jarvis-muted">
              L.U.C.E.R.O
            </p>
            <div className="prose-jarvis">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  a: ({ href, children }) => {
                    const label = String(children);
                    const isFile =
                      /download|png|pdf|mp4/i.test(label) ||
                      /\.(png|pdf|jpg|jpeg|mp4)(\?|$)/i.test(href || "");
                    if (isFile && href) {
                      return (
                        <button
                          type="button"
                          className="text-jarvis-cyan underline"
                          onClick={(e) => {
                            e.preventDefault();
                            e.stopPropagation();
                            void import("@/lib/download").then(({ downloadViaProxy }) =>
                              downloadViaProxy(
                                href,
                                /pdf/i.test(label)
                                  ? "lucero.pdf"
                                  : "lucero.png"
                              )
                            );
                          }}
                        >
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
                  img: ({ src, alt }) =>
                    src ? (
                      // eslint-disable-next-line @next/next/no-img-element
                      <img
                        src={src}
                        alt={alt || ""}
                        className="max-h-64 rounded-lg"
                      />
                    ) : null,
                }}
              >
                {streamBuffer}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {streaming && !streamBuffer && (
          <div className="flex gap-1.5 px-2">
            {[0, 1, 2].map((i) => (
              <span
                key={i}
                className="h-1.5 w-1.5 rounded-full bg-jarvis-cyan animate-pulseDot"
                style={{ animationDelay: `${i * 0.2}s` }}
              />
            ))}
          </div>
        )}

        {transcript && (
          <p className="text-xs text-jarvis-cyan/90 italic">
            {transcript.startsWith("Listening")
              ? transcript
              : `Heard: ${transcript}`}
          </p>
        )}
        {error && <p className="text-xs text-jarvis-danger">{error}</p>}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={submit}
        className="border-t border-jarvis-border/70 p-3 space-y-2"
      >
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={onToggleMic}
            className={cn(
              "rounded-xl p-2.5 border transition",
              micOn
                ? "border-jarvis-cyan/50 bg-jarvis-cyan/15 text-jarvis-cyan shadow-glow-sm"
                : "border-jarvis-border text-jarvis-muted"
            )}
            title={micOn ? "Mute mic" : "Enable mic"}
          >
            {micOn ? <Mic size={18} /> : <MicOff size={18} />}
          </button>
          <button
            type="button"
            onClick={speaking ? onStopSpeaking : onPushToTalk}
            className={cn(
              "rounded-xl p-2.5 border transition",
              speaking
                ? "border-jarvis-danger/50 bg-jarvis-danger/15 text-jarvis-danger"
                : "border-jarvis-border text-jarvis-muted hover:text-jarvis-cyan hover:border-jarvis-cyan/40"
            )}
            title={speaking ? "Stop speaking" : "Push to talk"}
          >
            {speaking ? <Square size={18} /> : <Keyboard size={18} />}
          </button>
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message…"
            className="flex-1 rounded-xl border border-jarvis-border bg-jarvis-bg/80 px-3 py-2.5 text-sm outline-none focus:border-jarvis-cyan/60"
          />
          <button
            type="submit"
            disabled={streaming || !input.trim()}
            className="rounded-xl bg-jarvis-cyan/90 p-2.5 text-jarvis-bg hover:bg-jarvis-accent disabled:opacity-40"
          >
            <Send size={18} />
          </button>
        </div>
      </form>
    </div>
  );
}
