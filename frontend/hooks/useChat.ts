"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, streamChat } from "@/services/api";
import type { Conversation, Message } from "@/types";

const DEFAULT_MODEL =
  process.env.NEXT_PUBLIC_DEFAULT_MODEL || "openai/gpt-4o-mini";

export function useChat() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [streamBuffer, setStreamBuffer] = useState("");
  const [model, setModel] = useState(DEFAULT_MODEL);
  const [status, setStatus] = useState<"idle" | "thinking" | "streaming" | "error">(
    "idle"
  );
  const [agentProgress, setAgentProgress] = useState<string | null>(null);
  const [activeMode, setActiveMode] = useState<string | null>(null);
  const [activeAgents, setActiveAgents] = useState<
    Array<{ id: string; name: string }>
  >([]);
  const [forcedAgentId, setForcedAgentId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const forcedAgentRef = useRef<string | null>(null);

  useEffect(() => {
    forcedAgentRef.current = forcedAgentId;
  }, [forcedAgentId]);

  const abortRef = useRef<AbortController | null>(null);
  const streamingRef = useRef(false);
  const activeIdRef = useRef<string | null>(null);
  const modelRef = useRef(DEFAULT_MODEL);

  useEffect(() => {
    activeIdRef.current = activeId;
  }, [activeId]);

  useEffect(() => {
    modelRef.current = model;
  }, [model]);

  const refreshHistory = useCallback(async () => {
    const list = await api.history();
    setConversations(list);
  }, []);

  useEffect(() => {
    refreshHistory().catch(() => undefined);
  }, [refreshHistory]);

  const selectConversation = useCallback(async (id: string | null) => {
    setActiveId(id);
    setError(null);
    setStreamBuffer("");
    if (!id) {
      setMessages([]);
      return;
    }
    const detail = await api.conversation(id);
    setMessages(detail.messages);
    if (detail.model) setModel(detail.model);
  }, []);

  const startNewChat = useCallback(() => {
    abortRef.current?.abort();
    setActiveId(null);
    setMessages([]);
    setStreamBuffer("");
    setError(null);
    setStatus("idle");
    streamingRef.current = false;
    setStreaming(false);
    setAgentProgress(null);
    setActiveMode(null);
  }, []);

  const sendMessage = useCallback(
    async (text: string, regenerateMessageId?: string): Promise<string | undefined> => {
      const content = text.trim();
      if (!content) return;

      // Wait briefly if a reply is already in flight (voice can overlap)
      let waits = 0;
      while (streamingRef.current && waits < 40) {
        await new Promise((r) => setTimeout(r, 250));
        waits += 1;
      }
      if (streamingRef.current) return;

      setError(null);
      streamingRef.current = true;
      setStreaming(true);
      setStatus("thinking");
      setStreamBuffer("");
      setAgentProgress("Routing your request…");
      setActiveMode(null);
      let finalReply = "";
      const currentActiveId = activeIdRef.current;
      const currentModel = modelRef.current;

      if (!regenerateMessageId) {
        const optimistic: Message = {
          id: `temp-${Date.now()}`,
          conversation_id: currentActiveId || "pending",
          role: "user",
          content,
          created_at: new Date().toISOString(),
        };
        setMessages((prev) => [...prev, optimistic]);
      } else {
        setMessages((prev) => {
          const idx = prev.findIndex((m) => m.id === regenerateMessageId);
          if (idx === -1) return prev;
          return prev.slice(0, idx);
        });
      }

      const controller = new AbortController();
      abortRef.current = controller;
      let conversationId = currentActiveId;

      try {
        await streamChat(
          {
            message: content,
            conversation_id: currentActiveId,
            model: currentModel,
            regenerate_message_id: regenerateMessageId || null,
            agent_id: forcedAgentRef.current,
          },
          {
            onMeta: (meta) => {
              conversationId = meta.conversation_id;
              setActiveId(meta.conversation_id);
              activeIdRef.current = meta.conversation_id;
              if (meta.mode) setActiveMode(meta.mode);
              if (meta.agents) setActiveAgents(meta.agents);
              setStatus("thinking");
            },
            onProgress: (progress) => {
              setStatus("thinking");
              const label = progress.agent_name
                ? `${progress.agent_name}: ${progress.detail || progress.step}`
                : progress.detail || progress.step;
              setAgentProgress(label);
            },
            onToken: (token) => {
              setStatus("streaming");
              setAgentProgress(null);
              setStreamBuffer((prev) => prev + token);
            },
            onDone: (done) => {
              finalReply = done.content;
              setStreamBuffer("");
              setAgentProgress(null);
              if (done.agents) setActiveAgents(done.agents);
              setMessages((prev) => [
                ...prev.filter((m) => !m.id.startsWith("temp-")),
                {
                  id: done.message_id,
                  conversation_id: done.conversation_id,
                  role: "assistant",
                  content: done.content,
                  model: currentModel,
                  created_at: new Date().toISOString(),
                },
              ]);
              setStatus("idle");
            },
            onError: (err) => {
              setError(err);
              setAgentProgress(null);
              setStatus("error");
            },
          },
          controller.signal
        );

        if (conversationId) {
          const detail = await api.conversation(conversationId);
          setMessages(detail.messages);
          const lastAssistant = [...detail.messages]
            .reverse()
            .find((m) => m.role === "assistant");
          if (lastAssistant?.content) finalReply = lastAssistant.content;
          await refreshHistory();
        }
        return finalReply || undefined;
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setError((err as Error).message || "Something went wrong");
          setStatus("error");
        }
        return undefined;
      } finally {
        streamingRef.current = false;
        setStreaming(false);
        setStreamBuffer("");
        setAgentProgress(null);
        abortRef.current = null;
      }
    },
    [refreshHistory]
  );

  const regenerate = useCallback(
    async (assistantMessage: Message) => {
      const idx = messages.findIndex((m) => m.id === assistantMessage.id);
      if (idx <= 0) return;
      const priorUser = [...messages.slice(0, idx)]
        .reverse()
        .find((m) => m.role === "user");
      if (!priorUser) return;
      await sendMessage(priorUser.content, assistantMessage.id);
    },
    [messages, sendMessage]
  );

  const removeConversation = useCallback(
    async (id: string) => {
      await api.deleteConversation(id);
      if (activeId === id) startNewChat();
      await refreshHistory();
    },
    [activeId, refreshHistory, startNewChat]
  );

  return {
    conversations,
    activeId,
    messages,
    streaming,
    streamBuffer,
    model,
    setModel,
    status,
    agentProgress,
    activeMode,
    activeAgents,
    forcedAgentId,
    setForcedAgentId,
    error,
    selectConversation,
    startNewChat,
    sendMessage,
    regenerate,
    removeConversation,
    refreshHistory,
  };
}
