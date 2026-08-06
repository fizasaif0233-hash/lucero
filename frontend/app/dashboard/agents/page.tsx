"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  Bot,
  BarChart3,
  Coins,
  FileText,
  Handshake,
  Headphones,
  Megaphone,
  Sparkles,
} from "lucide-react";
import { SecondaryShell } from "@/components/jarvis/SecondaryShell";
import { api } from "@/services/api";
import type { SpecialistAgentInfo } from "@/types";

const ICONS: Record<string, React.ComponentType<{ size?: number }>> = {
  megaphone: Megaphone,
  coins: Coins,
  handshake: Handshake,
  file: FileText,
  chart: BarChart3,
  headset: Headphones,
  bot: Bot,
};

const EMOJI: Record<string, string> = {
  marketing: "📈",
  investor: "💰",
  distributor: "🤝",
  document: "📄",
  finance: "📊",
  support: "🛎️",
};

export default function AgentsPage() {
  const router = useRouter();
  const [agents, setAgents] = useState<SpecialistAgentInfo[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const list = await api.specialistAgents();
      setAgents(list);
    } catch (err) {
      setError((err as Error).message);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function openAgent(id: string) {
    router.push(`/dashboard?agent=${encodeURIComponent(id)}`);
  }

  return (
    <SecondaryShell title="AI Agents">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="mx-auto max-w-6xl animate-fadeIn">
          <div className="mb-8">
            <h1 className="font-display text-3xl tracking-wide mb-2">
              AI Agents
            </h1>
            <p className="text-sm text-jarvis-muted max-w-2xl">
              L.U.C.E.R.O routes each request to specialist agents. Open an agent
              to chat with that specialty, or ask from the main HUD and the
              Agent Router will choose automatically — including multi-agent
              collaboration when needed.
            </p>
          </div>

          {error && (
            <div className="mb-6 rounded-xl border border-jarvis-danger/40 bg-jarvis-danger/10 px-4 py-3 text-sm text-jarvis-danger">
              {error}
            </div>
          )}

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
            {agents.map((agent) => {
              const Icon = ICONS[agent.icon] || Bot;
              return (
                <div key={agent.id} className="hud-card flex flex-col p-5">
                  <div className="mb-3 flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-xl">{EMOJI[agent.id] || "🤖"}</span>
                      <div className="rounded-xl border border-jarvis-cyan/30 bg-jarvis-cyan/10 p-2 text-jarvis-cyan">
                        <Icon size={16} />
                      </div>
                    </div>
                    <span className="rounded-full border border-jarvis-border px-2 py-0.5 text-[10px] uppercase tracking-wider text-jarvis-muted">
                      {agent.status}
                    </span>
                  </div>
                  <h2 className="font-display text-lg tracking-wide mb-2">
                    {agent.title}
                  </h2>
                  <p className="text-sm text-jarvis-muted mb-4 flex-1">
                    {agent.description}
                  </p>
                  <div className="mb-4">
                    <p className="mb-2 text-[10px] uppercase tracking-[0.14em] text-jarvis-cyan">
                      Available skills
                    </p>
                    <ul className="space-y-1">
                      {agent.skills.slice(0, 5).map((skill) => (
                        <li
                          key={skill}
                          className="flex items-start gap-2 text-xs text-jarvis-muted"
                        >
                          <Sparkles
                            size={12}
                            className="mt-0.5 shrink-0 text-jarvis-cyan/70"
                          />
                          {skill}
                        </li>
                      ))}
                    </ul>
                  </div>
                  <button
                    type="button"
                    onClick={() => openAgent(agent.id)}
                    className="rounded-xl bg-jarvis-cyan/90 px-3 py-2.5 text-sm font-medium text-jarvis-bg hover:bg-jarvis-accent"
                  >
                    Open Agent
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </SecondaryShell>
  );
}
