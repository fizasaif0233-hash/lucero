"use client";

import { Suspense, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Bot, Calendar, Images, Mail, MessageCircle, Workflow } from "lucide-react";
import {
  CHAT_SIZE_STORAGE_KEY,
  ConversationPanel,
  type ChatPanelSize,
} from "@/components/jarvis/ConversationPanel";
import { HudTopBar } from "@/components/jarvis/HudTopBar";
import { LeftWidgets } from "@/components/jarvis/LeftWidgets";
import { OrbCore } from "@/components/jarvis/OrbCore";
import { useChat } from "@/hooks/useChat";
import { useVoice } from "@/hooks/useVoice";
import { api } from "@/services/api";
import { createClient } from "@/lib/supabase/client";
import { cn } from "@/lib/utils";

function loadChatSize(): ChatPanelSize {
  if (typeof window === "undefined") return "normal";
  const saved = window.localStorage.getItem(CHAT_SIZE_STORAGE_KEY);
  if (
    saved === "minimized" ||
    saved === "compact" ||
    saved === "normal" ||
    saved === "large" ||
    saved === "max"
  ) {
    return saved;
  }
  return "normal";
}

function DashboardInner() {
  const chat = useChat();
  const searchParams = useSearchParams();
  const [backendOnline, setBackendOnline] = useState(true);
  const [userName, setUserName] = useState<string | null>(null);
  const [knowledgeReady, setKnowledgeReady] = useState(false);
  const [chatSize, setChatSize] = useState<ChatPanelSize>("normal");
  const sessionStartedAt = useRef(Date.now()).current;
  const sendMessageRef = useRef(chat.sendMessage);

  useEffect(() => {
    setChatSize(loadChatSize());
  }, []);

  useEffect(() => {
    const agent = searchParams.get("agent");
    if (agent) chat.setForcedAgentId(agent);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const handleChatSizeChange = useCallback((size: ChatPanelSize) => {
    setChatSize(size);
    window.localStorage.setItem(CHAT_SIZE_STORAGE_KEY, size);
  }, []);

  useEffect(() => {
    sendMessageRef.current = chat.sendMessage;
  }, [chat.sendMessage]);

  const handleVoiceCommand = useCallback(async (text: string) => {
    return await sendMessageRef.current(text);
  }, []);

  const voice = useVoice({
    enabled: true,
    onCommand: handleVoiceCommand,
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "https://lucero-api-production.up.railway.app"}/health`
        );
        if (!cancelled) setBackendOnline(res.ok);
      } catch {
        if (!cancelled) setBackendOnline(false);
      }

      try {
        const me = await api.me();
        if (!cancelled) setUserName(me.full_name || me.email);
      } catch {
        const supabase = createClient();
        const { data } = await supabase.auth.getUser();
        if (!cancelled) {
          setUserName(
            data.user?.user_metadata?.full_name || data.user?.email || null
          );
        }
      }

      try {
        const docs = await api.documents();
        if (!cancelled) setKnowledgeReady(docs.some((d) => d.status === "ready"));
      } catch {
        if (!cancelled) setKnowledgeReady(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const voiceModeLabel = useMemo(() => {
    switch (voice.phase) {
      case "listening":
        return "Listening";
      case "thinking":
        return "Thinking";
      case "speaking":
        return "Speaking";
      case "unsupported":
        return "N/A";
      default:
        return "Ready";
    }
  }, [voice.phase]);

  async function handleTypedSend(text: string) {
    const reply = await chat.sendMessage(text);
    if (reply && voice.speakerOn) {
      await voice.speak(reply);
    }
  }

  const maximized = chatSize === "max";
  const gridClass = maximized
    ? "grid-cols-1"
    : chatSize === "minimized"
      ? "lg:grid-cols-[260px_minmax(0,1fr)_56px] xl:grid-cols-[280px_minmax(0,1fr)_64px]"
      : chatSize === "compact"
        ? "lg:grid-cols-[220px_minmax(0,1fr)_280px] xl:grid-cols-[240px_minmax(0,1fr)_300px]"
        : chatSize === "large"
          ? "lg:grid-cols-[200px_minmax(0,0.7fr)_520px] xl:grid-cols-[220px_minmax(0,0.65fr)_580px]"
          : "lg:grid-cols-[260px_minmax(0,1fr)_360px] xl:grid-cols-[280px_minmax(0,1fr)_400px]";

  return (
    <div className="flex h-dvh max-h-dvh flex-col overflow-hidden">
      <HudTopBar
        online={backendOnline && !chat.error}
        userName={userName}
        speakerOn={voice.speakerOn}
        onToggleSpeaker={voice.toggleSpeaker}
      />

      <div
        className={cn(
          "grid min-h-0 flex-1 overflow-hidden grid-cols-1 transition-[grid-template-columns] duration-300",
          gridClass
        )}
      >
        {!maximized && (
          <aside className="hidden min-h-0 overflow-hidden lg:block border-r border-jarvis-border/60">
            <LeftWidgets
              knowledgeReady={knowledgeReady}
              messageCount={chat.messages.filter((m) => m.role === "user").length}
              sessionStartedAt={sessionStartedAt}
              voiceModeLabel={voiceModeLabel}
            />
          </aside>
        )}

        {!maximized && (
          <section className="relative flex min-h-0 flex-col items-center overflow-y-auto overflow-x-hidden px-3 py-3 sm:px-4">
            <div className="my-auto flex w-full flex-col items-center gap-3 py-2">
              <OrbCore
                mode={voice.mode}
                phase={voice.phase}
                onOrbClick={
                  voice.phase === "speaking" ? voice.interrupt : voice.pushToTalk
                }
              />

              <div className="flex flex-wrap items-center justify-center gap-2">
                <Link
                  href="/dashboard/agents"
                  className="inline-flex items-center gap-2 rounded-2xl border border-jarvis-cyan/50 bg-jarvis-cyan/10 px-3.5 py-2.5 text-[11px] uppercase tracking-[0.14em] text-jarvis-cyan shadow-glow-sm hover:bg-jarvis-cyan/20"
                >
                  <Bot size={14} />
                  AI Agents
                </Link>
                <Link
                  href="/media"
                  className="inline-flex items-center gap-2 rounded-2xl border border-jarvis-cyan/50 bg-jarvis-cyan/10 px-3.5 py-2.5 text-[11px] uppercase tracking-[0.14em] text-jarvis-cyan shadow-glow-sm hover:bg-jarvis-cyan/20"
                >
                  <Images size={14} />
                  Media
                </Link>
                <Link
                  href="/dashboard/channels"
                  className="inline-flex items-center gap-2 rounded-2xl border border-jarvis-cyan/50 bg-jarvis-cyan/10 px-3.5 py-2.5 text-[11px] uppercase tracking-[0.14em] text-jarvis-cyan shadow-glow-sm hover:bg-jarvis-cyan/20"
                >
                  <MessageCircle size={14} />
                  Channels
                </Link>
                <Link
                  href="/dashboard/automation"
                  className="inline-flex items-center gap-2 rounded-2xl border border-jarvis-cyan/50 bg-jarvis-cyan/10 px-3.5 py-2.5 text-[11px] uppercase tracking-[0.14em] text-jarvis-cyan shadow-glow-sm hover:bg-jarvis-cyan/20"
                >
                  <Workflow size={14} />
                  Automation
                </Link>
                <Link
                  href="/dashboard/email"
                  className="inline-flex items-center gap-2 rounded-2xl border border-jarvis-cyan/50 bg-jarvis-cyan/10 px-3.5 py-2.5 text-[11px] uppercase tracking-[0.14em] text-jarvis-cyan shadow-glow-sm hover:bg-jarvis-cyan/20"
                >
                  <Mail size={14} />
                  Email
                </Link>
                <Link
                  href="/dashboard/calendar"
                  className="inline-flex items-center gap-2 rounded-2xl border border-jarvis-cyan/50 bg-jarvis-cyan/10 px-3.5 py-2.5 text-[11px] uppercase tracking-[0.14em] text-jarvis-cyan shadow-glow-sm hover:bg-jarvis-cyan/20"
                >
                  <Calendar size={14} />
                  Calendar
                </Link>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-2 pb-1">
                <button
                  onClick={voice.toggleMic}
                  className={`rounded-2xl border px-3.5 py-2.5 text-[11px] uppercase tracking-[0.14em] transition ${
                    voice.micOn
                      ? "border-jarvis-cyan/50 bg-jarvis-cyan/10 text-jarvis-cyan shadow-glow-sm"
                      : "border-jarvis-border text-jarvis-muted"
                  }`}
                >
                  Mic {voice.micOn ? "On" : "Off"}
                </button>
                {voice.phase === "speaking" ? (
                  <button
                    onClick={voice.interrupt}
                    className="rounded-2xl border border-jarvis-danger/60 bg-jarvis-danger/15 px-4 py-2.5 text-[11px] uppercase tracking-[0.14em] text-jarvis-danger shadow-glow-sm hover:bg-jarvis-danger/25"
                  >
                    Stop speaking
                  </button>
                ) : (
                  <button
                    onClick={voice.pushToTalk}
                    className="rounded-2xl border border-jarvis-cyan/60 bg-jarvis-cyan/15 px-4 py-2.5 text-[11px] uppercase tracking-[0.14em] text-jarvis-cyan shadow-glow-sm hover:bg-jarvis-cyan/25"
                  >
                    Talk now
                  </button>
                )}
                <button
                  onClick={voice.toggleSpeaker}
                  className={`rounded-2xl border px-3.5 py-2.5 text-[11px] uppercase tracking-[0.14em] transition ${
                    voice.speakerOn
                      ? "border-jarvis-cyan/50 bg-jarvis-cyan/10 text-jarvis-cyan"
                      : "border-jarvis-border text-jarvis-muted"
                  }`}
                >
                  Voice {voice.speakerOn ? "On" : "Off"}
                </button>
              </div>

              {voice.error && (
                <p className="text-center text-xs text-jarvis-danger">
                  {voice.error}
                </p>
              )}
            </div>
          </section>
        )}

        <aside
          className={cn(
            "min-h-0 overflow-hidden border-jarvis-border/60 p-2 sm:p-3",
            maximized
              ? "border-0"
              : "border-t lg:border-t-0 lg:border-l",
            chatSize === "minimized" && "flex justify-center"
          )}
        >
          <ConversationPanel
            messages={chat.messages}
            streamBuffer={chat.streamBuffer}
            streaming={chat.streaming}
            agentProgress={chat.agentProgress}
            activeMode={chat.activeMode}
            activeAgents={chat.activeAgents}
            forcedAgentId={chat.forcedAgentId}
            onClearForcedAgent={() => chat.setForcedAgentId(null)}
            error={chat.error}
            transcript={voice.transcript}
            micOn={voice.micOn}
            speaking={voice.phase === "speaking"}
            panelSize={chatSize}
            onPanelSizeChange={handleChatSizeChange}
            onToggleMic={voice.toggleMic}
            onPushToTalk={voice.pushToTalk}
            onStopSpeaking={voice.interrupt}
            onSend={handleTypedSend}
            onClear={chat.startNewChat}
            onRegenerate={chat.regenerate}
            onImprove={chat.improve}
            onEdit={(msg, instruction) => chat.editPrompt(msg, instruction)}
            onImageTool={chat.runImageTool}
            onVideoTool={chat.runVideoTool}
          />
        </aside>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-jarvis-bg" />}>
      <DashboardInner />
    </Suspense>
  );
}
