"use client";

import { useEffect, useState } from "react";
import { SecondaryShell } from "@/components/jarvis/SecondaryShell";
import { api } from "@/services/api";
import type { UserProfile } from "@/types";

export default function SettingsPage() {
  const [profile, setProfile] = useState<UserProfile | null>(null);

  useEffect(() => {
    api.me().then(setProfile).catch(() => undefined);
  }, []);

  return (
    <SecondaryShell title="Settings">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="mx-auto max-w-2xl animate-fadeIn">
          <h1 className="font-display text-3xl mb-2 tracking-wide">Settings</h1>
          <p className="text-sm text-jarvis-muted mb-8">
            Account and voice assistant preferences.
          </p>

          <section className="hud-card p-6 space-y-4">
            <h2 className="text-sm uppercase tracking-wider text-jarvis-cyan">
              Profile
            </h2>
            <div className="grid gap-3 text-sm">
              <div className="flex justify-between gap-4 border-b border-jarvis-border pb-3">
                <span className="text-jarvis-muted">Name</span>
                <span>{profile?.full_name || "—"}</span>
              </div>
              <div className="flex justify-between gap-4 border-b border-jarvis-border pb-3">
                <span className="text-jarvis-muted">Email</span>
                <span>{profile?.email || "—"}</span>
              </div>
              <div className="flex justify-between gap-4">
                <span className="text-jarvis-muted">Role</span>
                <span className="capitalize">{profile?.role || "—"}</span>
              </div>
            </div>
          </section>

          <section className="mt-6 hud-card p-6">
            <h2 className="text-sm uppercase tracking-wider text-jarvis-cyan mb-3">
              Voice
            </h2>
            <p className="text-sm text-jarvis-muted leading-relaxed">
              On the main HUD, enable the microphone and say{" "}
              <span className="text-jarvis-cyan">“Hey Lucero”</span> followed by
              your question. L.U.C.E.R.O answers from your indexed knowledge base
              and can speak replies aloud.
            </p>
            <p className="mt-3 text-xs text-jarvis-muted">
              Best in Chrome / Edge. Allow microphone access when prompted.
            </p>
          </section>

          <section className="mt-6 hud-card p-6">
            <h2 className="text-sm uppercase tracking-wider text-jarvis-cyan mb-3">
              Coming later
            </h2>
            <ul className="text-sm text-jarvis-muted space-y-2 list-disc pl-5">
              <li>WhatsApp / Telegram channels</li>
              <li>Website chat widget on anthonywarrenmckinzy.com</li>
              <li>Marketing & research agents</li>
            </ul>
          </section>
        </div>
      </div>
    </SecondaryShell>
  );
}
