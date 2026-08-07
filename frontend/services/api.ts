import { createClient } from "@/lib/supabase/client";
import type {
  AutomationHistoryItem,
  AutomationModuleInfo,
  AutomationRun,
  Booking,
  BusinessDocument,
  CalendarEvent,
  ChatDone,
  ChatMeta,
  ChatProgress,
  Conversation,
  ConversationDetail,
  Customer,
  EmailLog,
  EmailTemplate,
  LuceroEmail,
  MemoryItem,
  Reminder,
  SpecialistAgentInfo,
  UserProfile,
  ChannelStatus,
  ChannelIdentity,
} from "@/types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  "https://lucero-api-production.up.railway.app";

async function getAccessToken(): Promise<string> {
  const supabase = createClient();

  // Prefer a validated/refreshed session over a possibly stale cached token
  const { data: userData, error: userError } = await supabase.auth.getUser();
  if (userError || !userData.user) {
    throw new Error("Not authenticated — please sign in again");
  }

  const { data, error } = await supabase.auth.getSession();
  if (error || !data.session?.access_token) {
    const refreshed = await supabase.auth.refreshSession();
    const token = refreshed.data.session?.access_token;
    if (!token) throw new Error("Not authenticated — please sign in again");
    return token;
  }

  return data.session.access_token;
}

async function buildAuthedRequest(
  path: string,
  token: string,
  options: RequestInit
): Promise<Response> {
  return fetch(`${API_URL}/api/v1${path}`, {
    ...options,
    headers: {
      ...(options.headers || {}),
      Authorization: `Bearer ${token}`,
      ...(options.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
    },
  });
}

async function apiFetch<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const supabase = createClient();
  let token = await getAccessToken();
  let res = await buildAuthedRequest(path, token, options);

  // Some browser sessions keep a stale JWT briefly. Refresh once and retry.
  if (res.status === 401) {
    const refreshed = await supabase.auth.refreshSession();
    token = refreshed.data.session?.access_token || "";
    if (token) {
      res = await buildAuthedRequest(path, token, options);
    }
  }

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const err = await res.json();
      detail = err.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  me: () => apiFetch<UserProfile>("/me"),

  history: () =>
    apiFetch<{ conversations: Conversation[] }>("/history").then(
      (r) => r.conversations
    ),

  conversation: (id: string) =>
    apiFetch<ConversationDetail>(`/history/${id}`),

  deleteConversation: (id: string) =>
    apiFetch<void>(`/conversations/${id}`, { method: "DELETE" }),

  documents: () =>
    apiFetch<{ documents: BusinessDocument[] }>("/documents").then(
      (r) => r.documents
    ),

  uploadDocument: async (file: File) => {
    const token = await getAccessToken();
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_URL}/api/v1/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Upload failed");
    }
    return res.json() as Promise<BusinessDocument>;
  },

  deleteDocument: (id: string) =>
    apiFetch<void>(`/documents/${id}`, { method: "DELETE" }),

  memory: () => apiFetch<MemoryItem[]>("/memory"),

  createMemory: (payload: {
    content: string;
    key?: string;
    category?: string;
  }) =>
    apiFetch<MemoryItem>("/memory", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  deleteMemory: (id: string) =>
    apiFetch<void>(`/memory/${id}`, { method: "DELETE" }),

  automationModules: () =>
    apiFetch<{ modules: AutomationModuleInfo[] }>("/automation/modules").then(
      (r) => r.modules
    ),

  automationHistory: (module?: string) => {
    const q = module ? `?module=${encodeURIComponent(module)}` : "";
    return apiFetch<{ runs: AutomationHistoryItem[] }>(
      `/automation/runs${q}`
    ).then((r) => r.runs);
  },

  automationStart: (payload: { module: string; prompt: string }) =>
    apiFetch<AutomationRun>("/automation/runs", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  automationRun: (id: string) =>
    apiFetch<AutomationRun>(`/automation/runs/${id}`),

  automationApprove: (id: string) =>
    apiFetch<AutomationRun>(`/automation/runs/${id}/approve`, {
      method: "POST",
    }),

  automationCancel: (id: string) =>
    apiFetch<AutomationRun>(`/automation/runs/${id}/cancel`, {
      method: "POST",
    }),

  automationUpdateItem: (
    id: string,
    payload: { content: Record<string, unknown>; title?: string }
  ) =>
    apiFetch(`/automation/items/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  specialistAgents: () =>
    apiFetch<{ agents: SpecialistAgentInfo[] }>("/agents").then((r) => r.agents),

  channelStatus: () => apiFetch<ChannelStatus>("/channels/status"),

  createChannelIdentity: (payload: {
    channel?: string;
    external_id: string;
    display_name?: string;
    allowed?: boolean;
    is_owner?: boolean;
    user_id?: string;
  }) =>
    apiFetch<ChannelIdentity>("/channels/identities", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  updateChannelIdentity: (
    id: string,
    payload: {
      display_name?: string;
      allowed?: boolean;
      is_owner?: boolean;
    }
  ) =>
    apiFetch<ChannelIdentity>(`/channels/identities/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  deleteChannelIdentity: (id: string) =>
    apiFetch<void>(`/channels/identities/${id}`, { method: "DELETE" }),

  // ---- Email ----
  emailDraft: (payload: {
    recipient: string;
    subject: string;
    body_html?: string;
    body_text?: string;
    recipient_name?: string;
    template_id?: string;
  }) =>
    apiFetch<LuceroEmail>("/email/draft", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  emailSend: (email_id: string, confirm = true) =>
    apiFetch<LuceroEmail>("/email/send", {
      method: "POST",
      body: JSON.stringify({ email_id, confirm }),
    }),

  emailApprove: (id: string) =>
    apiFetch<LuceroEmail>(`/email/${id}/approve`, { method: "POST" }),

  emailCancel: (id: string) =>
    apiFetch<LuceroEmail>(`/email/${id}/cancel`, { method: "POST" }),

  emailRetry: (id: string) =>
    apiFetch<LuceroEmail>(`/email/${id}/retry`, { method: "POST" }),

  emailUpdate: (
    id: string,
    payload: Partial<{
      recipient: string;
      subject: string;
      body_html: string;
      body_text: string;
      recipient_name: string;
    }>
  ) =>
    apiFetch<LuceroEmail>(`/email/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),

  emailHistory: (params?: { folder?: string; status?: string }) => {
    const q = new URLSearchParams();
    if (params?.folder) q.set("folder", params.folder);
    if (params?.status) q.set("status", params.status);
    const qs = q.toString() ? `?${q}` : "";
    return apiFetch<{ emails: LuceroEmail[] }>(`/email/history${qs}`).then(
      (r) => r.emails
    );
  },

  emailInbox: () =>
    apiFetch<{ emails: LuceroEmail[] }>("/email/inbox").then((r) => r.emails),

  emailTemplates: () =>
    apiFetch<{ templates: EmailTemplate[] }>("/email/templates").then(
      (r) => r.templates
    ),

  emailCreateTemplate: (payload: {
    name: string;
    subject: string;
    body_html?: string;
    body_text?: string;
    category?: string;
  }) =>
    apiFetch<EmailTemplate>("/email/template", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  emailLogs: () =>
    apiFetch<{ logs: EmailLog[] }>("/email/logs").then((r) => r.logs),

  // ---- Bookings ----
  bookings: (params?: { status?: string; search?: string }) => {
    const q = new URLSearchParams();
    if (params?.status) q.set("status", params.status);
    if (params?.search) q.set("search", params.search);
    const qs = q.toString() ? `?${q}` : "";
    return apiFetch<{ bookings: Booking[] }>(`/bookings${qs}`).then(
      (r) => r.bookings
    );
  },

  createBooking: (payload: Record<string, unknown>) =>
    apiFetch<Booking>("/bookings", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  bookingSummary: (payload: Record<string, unknown>) =>
    apiFetch<{ summary: string; payload: Record<string, unknown> }>(
      "/bookings/summary",
      { method: "POST", body: JSON.stringify(payload) }
    ),

  updateBooking: (id: string, payload: Record<string, unknown>) =>
    apiFetch<Booking>(`/bookings/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),

  approveBooking: (id: string) =>
    apiFetch<Booking>(`/bookings/${id}/approve`, {
      method: "POST",
      body: JSON.stringify({ confirm: true }),
    }),

  deleteBooking: (id: string) =>
    apiFetch<void>(`/bookings/${id}`, { method: "DELETE" }),

  // ---- Calendar ----
  calendarEvents: (params?: { start?: string; end?: string }) => {
    const q = new URLSearchParams();
    if (params?.start) q.set("start", params.start);
    if (params?.end) q.set("end", params.end);
    const qs = q.toString() ? `?${q}` : "";
    return apiFetch<{ events: CalendarEvent[] }>(`/calendar/events${qs}`).then(
      (r) => r.events
    );
  },

  // ---- Reminders ----
  reminders: () =>
    apiFetch<{ reminders: Reminder[] }>("/reminders").then((r) => r.reminders),

  runReminders: () =>
    apiFetch<{ processed: number; sent: number; failed: number }>(
      "/reminders/run",
      { method: "POST" }
    ),

  // ---- CRM ----
  customers: () =>
    apiFetch<{ customers: Customer[] }>("/crm/customers").then(
      (r) => r.customers
    ),

  customerProfile: (id: string) =>
    apiFetch<{
      customer: Customer;
      bookings: Booking[];
      email_history: Record<string, unknown>[];
      timeline: Array<{
        id: string;
        activity_type: string;
        title: string;
        body?: string | null;
        created_at?: string | null;
      }>;
    }>(`/crm/customers/${id}`),

  // ---- OS / multimodal ----
  osGetJob: (id: string) => apiFetch<any>(`/os/jobs/${id}`),
  osListJobs: () => apiFetch<{ jobs: any[] }>("/os/jobs"),
  osDownloadAsset: async (assetId: string, filename: string) => {
    const { downloadViaProxy, saveBlob } = await import("@/lib/download");
    const token = await getAccessToken();
    const res = await fetch(
      `${API_URL}/api/v1/os/assets/${assetId}/download`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (!res.ok) {
      // Fall back to public URL via same-origin Next proxy
      const meta = await apiFetch<{ public_url?: string; url?: string }>(
        `/os/assets/${assetId}`
      ).catch(() => null);
      const remote = meta?.public_url || (meta as { url?: string } | null)?.url;
      if (remote) {
        await downloadViaProxy(remote, filename || "lucero-asset");
        return;
      }
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "Download failed");
    }
    const blob = await res.blob();
    saveBlob(
      new Blob([blob], { type: "application/octet-stream" }),
      filename || "lucero-asset"
    );
  },
  /** Always saves via same-origin proxy — never opens the image in Lucero's tab. */
  downloadFile: async (url: string, filename: string) => {
    const { downloadViaProxy } = await import("@/lib/download");
    await downloadViaProxy(url, filename || "lucero-asset");
  },
  osListAssets: (jobId?: string) =>
    apiFetch<{
      assets: Array<{
        id: string;
        kind: string;
        title: string;
        public_url?: string | null;
        mime?: string;
        created_at?: string;
        meta?: Record<string, unknown>;
      }>;
    }>(jobId ? `/os/assets?job_id=${jobId}` : "/os/assets"),
  osCreateJob: (body: {
    task_type: string;
    input?: Record<string, unknown>;
    conversation_id?: string | null;
    client_request_id?: string | null;
  }) =>
    apiFetch<any>("/os/jobs", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  osTts: (text: string, voice = "af_bella") =>
    apiFetch<any>("/os/tts", {
      method: "POST",
      body: JSON.stringify({ text, voice }),
    }),
  osStt: async (blob: Blob, language?: string) => {
    const token = await getAccessToken();
    const form = new FormData();
    form.append("file", blob, "audio.webm");
    if (language) form.append("language", language);
    const res = await fetch(`${API_URL}/api/v1/os/stt`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || "STT failed");
    }
    return res.json() as Promise<{ text: string }>;
  },
  osUpscale: (image_url: string) =>
    apiFetch<any>("/os/tools/upscale", {
      method: "POST",
      body: JSON.stringify({ image_url }),
    }),
  osRemoveBg: (image_url: string) =>
    apiFetch<any>("/os/tools/remove-bg", {
      method: "POST",
      body: JSON.stringify({ image_url }),
    }),
  osVariations: (prompt: string, image_url?: string) =>
    apiFetch<any>("/os/tools/variations", {
      method: "POST",
      body: JSON.stringify({ prompt, image_url }),
    }),
};

export type StreamHandlers = {
  onMeta?: (meta: ChatMeta) => void;
  onProgress?: (progress: ChatProgress) => void;
  onToken?: (token: string) => void;
  onJob?: (job: { id: string; task_type: string; status: string; progress?: number }) => void;
  onAsset?: (asset: import("@/types").MediaAsset) => void;
  onDone?: (done: ChatDone) => void;
  onError?: (error: string) => void;
};

export async function streamChat(
  payload: {
    message: string;
    conversation_id?: string | null;
    model?: string;
    regenerate_message_id?: string | null;
    agent_id?: string | null;
  },
  handlers: StreamHandlers,
  signal?: AbortSignal
): Promise<void> {
  const token = await getAccessToken();
  let res: Response;
  try {
    res = await fetch(`${API_URL}/api/v1/chat`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
        Accept: "text/event-stream",
      },
      body: JSON.stringify(payload),
      signal,
    });
  } catch (err) {
    const raw = (err as Error).message || "Network error";
    throw new Error(
      /failed to fetch|networkerror|network error|load failed/i.test(raw)
        ? "Connection dropped while talking to L.U.C.E.R.O. Try again in a moment."
        : raw
    );
  }

  if (!res.ok || !res.body) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Chat request failed");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let eventName = "message";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("event:")) {
        eventName = line.slice(6).trim();
        continue;
      }
      if (line.startsWith("data:")) {
        const data = line.slice(5).trimStart();
        if (eventName === "meta") {
          try {
            handlers.onMeta?.(JSON.parse(data) as ChatMeta);
          } catch {
            /* ignore */
          }
        } else if (eventName === "progress") {
          try {
            handlers.onProgress?.(JSON.parse(data) as ChatProgress);
          } catch {
            /* ignore */
          }
        } else if (eventName === "token") {
          try {
            handlers.onToken?.(JSON.parse(data) as string);
          } catch {
            handlers.onToken?.(data);
          }
        } else if (eventName === "job") {
          try {
            handlers.onJob?.(JSON.parse(data));
          } catch {
            /* ignore */
          }
        } else if (eventName === "asset") {
          try {
            handlers.onAsset?.(JSON.parse(data));
          } catch {
            /* ignore */
          }
        } else if (eventName === "done") {
          try {
            handlers.onDone?.(JSON.parse(data) as ChatDone);
          } catch {
            /* ignore */
          }
        } else if (eventName === "error") {
          handlers.onError?.(data);
        }
        eventName = "message";
      }
    }
  }
}
