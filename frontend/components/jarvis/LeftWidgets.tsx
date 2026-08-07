"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Database, HardDrive, Activity, Bot, Workflow, MessageCircle, Mail, Calendar, Images } from "lucide-react";

interface LeftWidgetsProps {
  knowledgeReady: boolean;
  messageCount: number;
  sessionStartedAt: number;
  voiceModeLabel: string;
}

function formatUptime(ms: number): string {
  const total = Math.floor(ms / 1000);
  const h = String(Math.floor(total / 3600)).padStart(2, "0");
  const m = String(Math.floor((total % 3600) / 60)).padStart(2, "0");
  const s = String(total % 60).padStart(2, "0");
  return `${h}:${m}:${s}`;
}

export function LeftWidgets({
  knowledgeReady,
  messageCount,
  sessionStartedAt,
  voiceModeLabel,
}: LeftWidgetsProps) {
  const [uptime, setUptime] = useState("00:00:00");

  useEffect(() => {
    const tick = () => setUptime(formatUptime(Date.now() - sessionStartedAt));
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [sessionStartedAt]);

  return (
    <div className="flex h-full min-h-0 flex-col gap-2.5 overflow-y-auto overflow-x-hidden p-3 pt-3">
      <div className="hud-card shrink-0 p-3">
        <div className="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-jarvis-cyan">
          <Workflow size={13} />
          Operations
        </div>
        <div className="space-y-1.5">
          <Link
            href="/dashboard/agents"
            className="flex items-center gap-2.5 rounded-xl border border-jarvis-border/70 bg-jarvis-elevated/50 px-2.5 py-2.5 transition hover:border-jarvis-cyan/50 hover:bg-jarvis-cyan/10"
          >
            <span className="rounded-lg border border-jarvis-cyan/30 bg-jarvis-cyan/10 p-1.5 text-jarvis-cyan">
              <Bot size={14} />
            </span>
            <span className="min-w-0">
              <span className="block text-sm text-jarvis-text">AI Agents</span>
              <span className="block text-[10px] text-jarvis-muted">
                Marketing · Investor · Finance
              </span>
            </span>
          </Link>
          <Link
            href="/media"
            className="flex items-center gap-2.5 rounded-xl border border-jarvis-cyan/40 bg-jarvis-cyan/10 px-2.5 py-2.5 transition hover:border-jarvis-cyan/70 hover:bg-jarvis-cyan/20"
          >
            <span className="rounded-lg border border-jarvis-cyan/40 bg-jarvis-cyan/15 p-1.5 text-jarvis-cyan">
              <Images size={14} />
            </span>
            <span className="min-w-0">
              <span className="block text-sm text-jarvis-text">Media</span>
              <span className="block text-[10px] text-jarvis-muted">
                Flyers · Posts · Downloads
              </span>
            </span>
          </Link>
          <Link
            href="/dashboard/channels"
            className="flex items-center gap-2.5 rounded-xl border border-jarvis-border/70 bg-jarvis-elevated/50 px-2.5 py-2.5 transition hover:border-jarvis-cyan/50 hover:bg-jarvis-cyan/10"
          >
            <span className="rounded-lg border border-jarvis-cyan/30 bg-jarvis-cyan/10 p-1.5 text-jarvis-cyan">
              <MessageCircle size={14} />
            </span>
            <span className="min-w-0">
              <span className="block text-sm text-jarvis-text">Channels</span>
              <span className="block text-[10px] text-jarvis-muted">
                WhatsApp · ZeroClaw
              </span>
            </span>
          </Link>
          <Link
            href="/dashboard/automation"
            className="flex items-center gap-2.5 rounded-xl border border-jarvis-border/70 bg-jarvis-elevated/50 px-2.5 py-2.5 transition hover:border-jarvis-cyan/50 hover:bg-jarvis-cyan/10"
          >
            <span className="rounded-lg border border-jarvis-cyan/30 bg-jarvis-cyan/10 p-1.5 text-jarvis-cyan">
              <Workflow size={14} />
            </span>
            <span className="min-w-0">
              <span className="block text-sm text-jarvis-text">Automation</span>
              <span className="block text-[10px] text-jarvis-muted">
                Email · CRM · Reports
              </span>
            </span>
          </Link>
          <Link
            href="/dashboard/email"
            className="flex items-center gap-2.5 rounded-xl border border-jarvis-border/70 bg-jarvis-elevated/50 px-2.5 py-2.5 transition hover:border-jarvis-cyan/50 hover:bg-jarvis-cyan/10"
          >
            <span className="rounded-lg border border-jarvis-cyan/30 bg-jarvis-cyan/10 p-1.5 text-jarvis-cyan">
              <Mail size={14} />
            </span>
            <span className="min-w-0">
              <span className="block text-sm text-jarvis-text">Email</span>
              <span className="block text-[10px] text-jarvis-muted">
                Draft · Approve · Resend
              </span>
            </span>
          </Link>
          <Link
            href="/dashboard/calendar"
            className="flex items-center gap-2.5 rounded-xl border border-jarvis-border/70 bg-jarvis-elevated/50 px-2.5 py-2.5 transition hover:border-jarvis-cyan/50 hover:bg-jarvis-cyan/10"
          >
            <span className="rounded-lg border border-jarvis-cyan/30 bg-jarvis-cyan/10 p-1.5 text-jarvis-cyan">
              <Calendar size={14} />
            </span>
            <span className="min-w-0">
              <span className="block text-sm text-jarvis-text">Calendar</span>
              <span className="block text-[10px] text-jarvis-muted">
                Tastings · Schedule
              </span>
            </span>
          </Link>
        </div>
      </div>

      <div className="hud-card shrink-0 p-3">
        <div className="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-jarvis-cyan">
          <Activity size={13} />
          System
        </div>
        <div className="space-y-2.5 text-sm">
          <div>
            <div className="mb-1 flex justify-between text-[11px] text-jarvis-muted">
              <span>Voice</span>
              <span className="text-jarvis-text">{voiceModeLabel}</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-jarvis-elevated">
              <div className="h-full w-2/3 rounded-full bg-jarvis-cyan shadow-glow-sm" />
            </div>
          </div>
          <div>
            <div className="mb-1 flex justify-between text-[11px] text-jarvis-muted">
              <span>Backend</span>
              <span className="text-jarvis-success">Connected</span>
            </div>
            <div className="h-1.5 overflow-hidden rounded-full bg-jarvis-elevated">
              <div className="h-full w-[92%] rounded-full bg-jarvis-success/80" />
            </div>
          </div>
        </div>
      </div>

      <div className="hud-card shrink-0 p-3">
        <div className="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-jarvis-cyan">
          <Database size={13} />
          Knowledge
        </div>
        <p className="font-display text-xl text-jarvis-text">
          {knowledgeReady ? "Indexed" : "Loading"}
        </p>
        <p className="mt-1 text-[11px] leading-relaxed text-jarvis-muted">
          Assets · sites · uploads
        </p>
        <div className="mt-2.5 grid grid-cols-2 gap-1.5 text-[10px] text-jarvis-muted">
          <div className="rounded-lg bg-jarvis-elevated/70 px-2 py-1">Tequila</div>
          <div className="rounded-lg bg-jarvis-elevated/70 px-2 py-1">Token</div>
          <div className="rounded-lg bg-jarvis-elevated/70 px-2 py-1">Exchange</div>
          <div className="rounded-lg bg-jarvis-elevated/70 px-2 py-1">Brand</div>
        </div>
        <Link
          href="/media"
          className="mt-2.5 block rounded-lg border border-jarvis-cyan/30 bg-jarvis-cyan/10 px-2 py-1.5 text-center text-[10px] uppercase tracking-wider text-jarvis-cyan hover:bg-jarvis-cyan/20"
        >
          Generated media library
        </Link>
      </div>

      <div className="hud-card shrink-0 p-3">
        <div className="mb-2 flex items-center gap-2 text-[10px] uppercase tracking-[0.16em] text-jarvis-cyan">
          <HardDrive size={13} />
          Session
        </div>
        <p className="font-mono text-xl text-jarvis-text">{uptime}</p>
        <div className="mt-2 flex justify-between text-[11px] text-jarvis-muted">
          <span>Commands</span>
          <span className="text-jarvis-text">{messageCount}</span>
        </div>
        <div className="mt-2">
          <div className="mb-1 flex justify-between text-[10px] text-jarvis-muted">
            <span>System load</span>
            <span>Moderate</span>
          </div>
          <div className="h-1.5 overflow-hidden rounded-full bg-jarvis-elevated">
            <div className="h-full w-[35%] rounded-full bg-jarvis-accent" />
          </div>
        </div>
      </div>
    </div>
  );
}
