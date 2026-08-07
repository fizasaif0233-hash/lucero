import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

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

/** Force a real file save. Cross-origin `download` attrs are ignored by browsers. */
export async function forceDownload(
  url: string,
  filename: string,
  opts?: { authUrl?: string; token?: string | null }
): Promise<void> {
  const tryBlob = async (fetchUrl: string, headers?: HeadersInit) => {
    const res = await fetch(fetchUrl, { headers, mode: "cors" });
    if (!res.ok) throw new Error(`download failed: ${res.status}`);
    const blob = await res.blob();
    const objectUrl = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = objectUrl;
    a.download = filename || "lucero-asset";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(objectUrl);
  };

  // Prefer authenticated API proxy when available (always attachment)
  if (opts?.authUrl && opts.token) {
    try {
      await tryBlob(opts.authUrl, { Authorization: `Bearer ${opts.token}` });
      return;
    } catch {
      /* fall through */
    }
  }

  try {
    await tryBlob(url);
    return;
  } catch {
    // Last resort: new tab (better than replacing the chat)
    window.open(url, "_blank", "noopener,noreferrer");
  }
}
