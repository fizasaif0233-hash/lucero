import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { downloadViaProxy } from "@/lib/download";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  const diff = Date.now() - date.getTime();
  const minutes = Math.floor(diff / 60000);
  if (minutes < 1) return "Just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 7) return `${days}d ago`;
  return date.toLocaleDateString();
}

/** Save a remote file without leaving / navigating the Lucero tab. */
export async function forceDownload(
  url: string,
  filename: string
): Promise<void> {
  await downloadViaProxy(url, filename || "lucero-asset");
}
