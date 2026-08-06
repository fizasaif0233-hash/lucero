"use client";

import { cn } from "@/lib/utils";

const MODELS = [
  { id: "openai/gpt-4o-mini", label: "GPT-4o Mini" },
  { id: "openai/gpt-4o", label: "GPT-4o" },
  { id: "anthropic/claude-3.5-sonnet", label: "Claude 3.5 Sonnet" },
  { id: "google/gemini-2.0-flash-001", label: "Gemini 2.0 Flash" },
];

type Status = "idle" | "thinking" | "streaming" | "error";

interface TopBarProps {
  userName?: string | null;
  userEmail?: string | null;
  role?: string | null;
  model: string;
  onModelChange: (model: string) => void;
  status: Status;
}

export function TopBar({
  userName,
  userEmail,
  role,
  model,
  onModelChange,
  status,
}: TopBarProps) {
  const statusLabel =
    status === "thinking"
      ? "Thinking"
      : status === "streaming"
        ? "Responding"
        : status === "error"
          ? "Error"
          : "Ready";

  const statusColor =
    status === "error"
      ? "bg-jarvis-danger"
      : status === "idle"
        ? "bg-jarvis-success"
        : "bg-jarvis-accent animate-pulseDot";

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-jarvis-border bg-jarvis-panel/40 px-4 backdrop-blur">
      <div className="flex items-center gap-3 min-w-0">
        <div className="min-w-0">
          <p className="text-sm font-medium truncate">
            {userName || userEmail || "User"}
          </p>
          <p className="text-[11px] text-jarvis-muted capitalize truncate">
            {role || "member"}
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <label className="flex items-center gap-2 text-xs text-jarvis-muted">
          Model
          <select
            value={model}
            onChange={(e) => onModelChange(e.target.value)}
            className="rounded-md border border-jarvis-border bg-jarvis-bg px-2 py-1.5 text-xs text-jarvis-text outline-none focus:border-jarvis-accent"
          >
            {MODELS.map((m) => (
              <option key={m.id} value={m.id}>
                {m.label}
              </option>
            ))}
          </select>
        </label>

        <div className="flex items-center gap-2 text-xs text-jarvis-muted">
          <span className={cn("h-2 w-2 rounded-full", statusColor)} />
          {statusLabel}
        </div>
      </div>
    </header>
  );
}
