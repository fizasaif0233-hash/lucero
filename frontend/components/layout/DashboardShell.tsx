"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";
import { api } from "@/services/api";
import { createClient } from "@/lib/supabase/client";
import type { UserProfile } from "@/types";

const DEFAULT_MODEL =
  process.env.NEXT_PUBLIC_DEFAULT_MODEL || "openai/gpt-4o-mini";

export function DashboardShell({
  children,
  status = "idle",
  model,
  onModelChange,
}: {
  children: React.ReactNode;
  status?: "idle" | "thinking" | "streaming" | "error";
  model?: string;
  onModelChange?: (m: string) => void;
}) {
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [localModel, setLocalModel] = useState(model || DEFAULT_MODEL);

  useEffect(() => {
    if (model) setLocalModel(model);
  }, [model]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await api.me();
        if (!cancelled) setProfile(me);
      } catch {
        const supabase = createClient();
        const { data } = await supabase.auth.getUser();
        if (!cancelled && data.user) {
          setProfile({
            id: data.user.id,
            email: data.user.email || "",
            full_name: data.user.user_metadata?.full_name,
            role: data.user.user_metadata?.role || "owner",
          });
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  function handleModelChange(m: string) {
    setLocalModel(m);
    onModelChange?.(m);
  }

  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar
          userName={profile?.full_name}
          userEmail={profile?.email}
          role={profile?.role}
          model={localModel}
          onModelChange={handleModelChange}
          status={status}
        />
        <main className="min-h-0 flex-1 overflow-hidden">{children}</main>
      </div>
    </div>
  );
}
