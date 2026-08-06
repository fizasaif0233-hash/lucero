"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { ArrowLeft, LogOut } from "lucide-react";
import { createClient } from "@/lib/supabase/client";

export function SecondaryShell({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  const router = useRouter();

  async function signOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="flex h-14 items-center justify-between border-b border-jarvis-border/70 bg-jarvis-panel/50 px-4 backdrop-blur">
        <div className="flex items-center gap-3">
          <Link
            href="/dashboard"
            className="rounded-lg p-2 text-jarvis-muted hover:text-jarvis-cyan"
          >
            <ArrowLeft size={16} />
          </Link>
          <div>
            <p className="font-display text-sm tracking-[0.2em]">L.U.C.E.R.O</p>
            <p className="text-xs text-jarvis-muted">{title}</p>
          </div>
        </div>
        <button
          onClick={signOut}
          className="rounded-lg p-2 text-jarvis-muted hover:text-jarvis-danger"
        >
          <LogOut size={16} />
        </button>
      </header>
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
