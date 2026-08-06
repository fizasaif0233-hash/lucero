"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  Brain,
  Bot,
  FileText,
  LogOut,
  MessageCircle,
  Settings,
  Volume2,
  VolumeX,
  Workflow,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

interface HudTopBarProps {
  online: boolean;
  userName?: string | null;
  speakerOn: boolean;
  onToggleSpeaker: () => void;
}

export function HudTopBar({
  online,
  userName,
  speakerOn,
  onToggleSpeaker,
}: HudTopBarProps) {
  const [now, setNow] = useState(() => new Date());
  const router = useRouter();

  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  async function signOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  const time = now.toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
  const date = now.toLocaleDateString([], {
    month: "long",
    day: "numeric",
    year: "numeric",
  });

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-3 border-b border-jarvis-border/70 bg-jarvis-panel/60 px-4 backdrop-blur-md z-20">
      <div className="flex items-center gap-3 min-w-0">
        <span className="font-display text-lg tracking-[0.25em]">L.U.C.E.R.O</span>
        <span className="flex items-center gap-1.5 text-xs text-jarvis-muted">
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              online ? "bg-jarvis-success" : "bg-jarvis-danger"
            )}
          />
          {online ? "Online" : "Offline"}
        </span>
      </div>

      <div className="hidden md:block font-mono text-xs text-jarvis-muted tracking-wide">
        {time} <span className="text-jarvis-border">|</span> {date}
      </div>

      <div className="flex items-center gap-1 sm:gap-2">
        <span className="hidden sm:inline text-xs text-jarvis-muted truncate max-w-[140px]">
          {userName || "Owner"}
        </span>
        <Link
          href="/dashboard/agents"
          className="rounded-lg p-2 text-jarvis-muted hover:text-jarvis-cyan hover:bg-jarvis-elevated"
          title="AI Agents"
        >
          <Bot size={16} />
        </Link>
        <Link
          href="/dashboard/channels"
          className="rounded-lg p-2 text-jarvis-muted hover:text-jarvis-cyan hover:bg-jarvis-elevated"
          title="Channels"
        >
          <MessageCircle size={16} />
        </Link>
        <Link
          href="/dashboard/automation"
          className="rounded-lg p-2 text-jarvis-muted hover:text-jarvis-cyan hover:bg-jarvis-elevated"
          title="Automation"
        >
          <Workflow size={16} />
        </Link>
        <Link
          href="/dashboard/documents"
          className="rounded-lg p-2 text-jarvis-muted hover:text-jarvis-cyan hover:bg-jarvis-elevated"
          title="Documents"
        >
          <FileText size={16} />
        </Link>
        <Link
          href="/dashboard/memory"
          className="rounded-lg p-2 text-jarvis-muted hover:text-jarvis-cyan hover:bg-jarvis-elevated"
          title="Memory"
        >
          <Brain size={16} />
        </Link>
        <Link
          href="/dashboard/settings"
          className="rounded-lg p-2 text-jarvis-muted hover:text-jarvis-cyan hover:bg-jarvis-elevated"
          title="Settings"
        >
          <Settings size={16} />
        </Link>
        <button
          onClick={onToggleSpeaker}
          className="rounded-lg p-2 text-jarvis-muted hover:text-jarvis-cyan hover:bg-jarvis-elevated"
          title={speakerOn ? "Mute voice" : "Unmute voice"}
        >
          {speakerOn ? <Volume2 size={16} /> : <VolumeX size={16} />}
        </button>
        <button
          onClick={signOut}
          className="rounded-lg p-2 text-jarvis-muted hover:text-jarvis-danger hover:bg-jarvis-elevated"
          title="Sign out"
        >
          <LogOut size={16} />
        </button>
      </div>
    </header>
  );
}
