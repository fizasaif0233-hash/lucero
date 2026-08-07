"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Brain,
  Bot,
  Calendar,
  FileText,
  Images,
  LogOut,
  Mail,
  MessageCircle,
  MessageSquare,
  Settings,
  CalendarCheck,
  Workflow,
} from "lucide-react";
import { createClient } from "@/lib/supabase/client";
import { cn } from "@/lib/utils";

const NAV = [
  { href: "/dashboard", label: "Chat", icon: MessageSquare },
  { href: "/dashboard/agents", label: "AI Agents", icon: Bot },
  { href: "/dashboard/channels", label: "Channels", icon: MessageCircle },
  { href: "/dashboard/email", label: "Email", icon: Mail },
  { href: "/dashboard/bookings", label: "Bookings", icon: CalendarCheck },
  { href: "/dashboard/calendar", label: "Calendar", icon: Calendar },
  { href: "/dashboard/automation", label: "Automation", icon: Workflow },
  { href: "/dashboard/media", label: "Media", icon: Images },
  { href: "/dashboard/documents", label: "Documents", icon: FileText },
  { href: "/dashboard/memory", label: "Memory", icon: Brain },
  { href: "/dashboard/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();

  async function signOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <aside className="flex h-full w-[220px] shrink-0 flex-col border-r border-jarvis-border bg-jarvis-panel/60 backdrop-blur">
      <div className="px-5 py-6">
        <Link href="/dashboard" className="block">
          <span className="font-display text-3xl tracking-tight">L.U.C.E.R.O</span>
        </Link>
        <p className="mt-1 text-[11px] uppercase tracking-[0.18em] text-jarvis-muted">
          Business Assistant
        </p>
      </div>

      <nav className="flex-1 px-3 space-y-1">
        {NAV.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition",
                active
                  ? "bg-jarvis-elevated text-jarvis-text border border-jarvis-border"
                  : "text-jarvis-muted hover:text-jarvis-text hover:bg-jarvis-elevated/50"
              )}
            >
              <Icon size={17} strokeWidth={1.75} />
              {label}
            </Link>
          );
        })}
      </nav>

      <div className="p-3 border-t border-jarvis-border">
        <button
          onClick={signOut}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-jarvis-muted hover:text-jarvis-danger hover:bg-jarvis-elevated/50 transition"
        >
          <LogOut size={17} strokeWidth={1.75} />
          Sign out
        </button>
      </div>
    </aside>
  );
}
