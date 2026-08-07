"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { api, streamChat } from "@/services/api";
import type { Conversation, MediaAsset, Message, OsJobSummary } from "@/types";

const DEFAULT_MODEL =
  process.env.NEXT_PUBLIC_DEFAULT_MODEL || "qwen/qwen3.7-plus";

function assetsFromJob(job: OsJobSummary): MediaAsset[] {
  const saved = job.result?.saved_assets || [];
  return saved
    .filter((a) => a.url)
    .map((a) => ({
      id: a.id,
      kind: a.kind,
      title: a.title,
      url: a.url as string,
      mime: a.mime,
    }));
}

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
  const pollTimers = useRef<Record<string, ReturnType<typeof setInterval>>>({});

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

  useEffect(() => {
    return () => {
      Object.values(pollTimers.current).forEach(clearInterval);
    };
  }, []);

  const refreshHistory = useCallback(async () => {
    const list = await api.history();
    setConversations(list);
  }, []);

  useEffect(() => {
    refreshHistory().catch(() => undefined);
  }, [refreshHistory]);

  const mergeJobIntoMessage = useCallback(
    (messageId: string, job: OsJobSummary) => {
      setMessages((prev) =>
        prev.map((m) => {
          if (m.id !== messageId) return m;
          const jobs = [...(m.jobs || [])];
          const idx = jobs.findIndex((j) => j.id === job.id);
          if (idx >= 0) jobs[idx] = { ...jobs[idx], ...job };
          else jobs.push(job);
          const newAssets = assetsFromJob(job);
          const assets = [...(m.assets || [])];
          for (const a of newAssets) {
            if (!assets.some((x) => x.id === a.id)) assets.push(a);
          }
          return { ...m, jobs, assets };
        })
      );
    },
    []
  );

  const pollJob = useCallback(
    (jobId: string, messageId: string) => {
      if (pollTimers.current[jobId]) return;
      pollTimers.current[jobId] = setInterval(async () => {
        try {
          const job = (await api.osGetJob(jobId)) as OsJobSummary;
          mergeJobIntoMessage(messageId, job);
          if (job.status === "succeeded" || job.status === "failed") {
            clearInterval(pollTimers.current[jobId]);
            delete pollTimers.current[jobId];
          }
        } catch {
          /* keep polling briefly */
        }
      }, 2500);
    },
    [mergeJobIntoMessage]
  );

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
      let pendingJobs: OsJobSummary[] = [];

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
            onJob: (job) => {
              pendingJobs = [
                ...pendingJobs.filter((j) => j.id !== job.id),
                job as OsJobSummary,
              ];
              setAgentProgress(`Media: ${job.task_type} (${job.status})`);
            },
            onDone: (done) => {
              finalReply = done.content;
              setStreamBuffer("");
              setAgentProgress(null);
              if (done.agents) setActiveAgents(done.agents);
              const jobs = (done.jobs || pendingJobs) as OsJobSummary[];
              setMessages((prev) => [
                ...prev.filter((m) => !m.id.startsWith("temp-")),
                {
                  id: done.message_id,
                  conversation_id: done.conversation_id,
                  role: "assistant",
                  content: done.content,
                  model: currentModel,
                  created_at: new Date().toISOString(),
                  jobs,
                },
              ]);
              for (const job of jobs) {
                pollJob(job.id, done.message_id);
              }
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
    [refreshHistory, pollJob]
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

  const improve = useCallback(
    async (assistantMessage: Message) => {
      await sendMessage(
        `Improve and tighten this deliverable. Keep ACTION format. Prior version:\n\n${assistantMessage.content.slice(0, 6000)}`
      );
    },
    [sendMessage]
  );

  const editPrompt = useCallback(
    async (assistantMessage: Message, instruction: string) => {
      await sendMessage(
        `${instruction.trim()}\n\nBase on this previous output:\n\n${assistantMessage.content.slice(0, 6000)}`
      );
    },
    [sendMessage]
  );

  const runImageTool = useCallback(
    async (
      tool: "upscale" | "remove_bg" | "variations",
      asset: MediaAsset,
      message: Message
    ) => {
      try {
        setAgentProgress(`Running ${tool}…`);
        let job: any;
        if (tool === "upscale") job = await api.osUpscale(asset.url);
        else if (tool === "remove_bg") job = await api.osRemoveBg(asset.url);
        else
          job = await api.osVariations(
            "Premium Blue Prince21 McKinzy tequila brand visual variation",
            asset.url
          );
        mergeJobIntoMessage(message.id, job as OsJobSummary);
        if (job?.id && (job.status === "queued" || job.status === "running")) {
          pollJob(job.id, message.id);
        }
      } catch (err) {
        setError((err as Error).message || "Image tool failed");
      } finally {
        setAgentProgress(null);
      }
    },
    [mergeJobIntoMessage, pollJob]
  );

  const runVideoTool = useCallback(
    async (
      tool: "regenerate" | "change_voice" | "add_music",
      _asset: MediaAsset,
      message: Message
    ) => {
      try {
        setAgentProgress(`Video: ${tool}…`);
        const voice =
          tool === "change_voice" ? "am_adam" : "af_bella";
        const job = await api.osCreateJob({
          task_type: "commercial_video",
          conversation_id: message.conversation_id,
          input: {
            assistant_text: message.content,
            user_message:
              tool === "add_music"
                ? "Regenerate commercial with stronger cinematic score feel"
                : "Regenerate commercial video",
            voice,
            title:
              tool === "add_music"
                ? "Commercial with music direction"
                : "Commercial regenerate",
          },
        });
        mergeJobIntoMessage(message.id, job as OsJobSummary);
        pollJob(job.id, message.id);
      } catch (err) {
        setError((err as Error).message || "Video tool failed");
      } finally {
        setAgentProgress(null);
      }
    },
    [mergeJobIntoMessage, pollJob]
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
    improve,
    editPrompt,
    runImageTool,
    runVideoTool,
    removeConversation,
    refreshHistory,
  };
}
