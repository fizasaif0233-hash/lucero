/** Browser helpers that save a file without navigating the Lucero tab. */

export function saveBlob(blob: Blob, filename: string): void {
  const name = (filename || "lucero-asset").replace(/[^\w.\-]+/g, "_");
  const objectUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.style.display = "none";
  a.href = objectUrl;
  a.download = name;
  // Critical: never open a new browsing context
  a.target = "_self";
  a.rel = "noopener";
  document.body.appendChild(a);
  a.dispatchEvent(
    new MouseEvent("click", { bubbles: true, cancelable: true, view: window })
  );
  // Keep blob alive until the browser starts the download
  window.setTimeout(() => {
    a.remove();
    URL.revokeObjectURL(objectUrl);
  }, 5000);
}

/**
 * Download via same-origin Next.js proxy (most reliable — no tab navigation).
 */
export async function downloadViaProxy(
  remoteUrl: string,
  filename: string
): Promise<void> {
  const qs = new URLSearchParams({
    url: remoteUrl,
    filename: filename || "lucero-asset",
  });
  const res = await fetch(`/api/media-download?${qs.toString()}`, {
    method: "GET",
    credentials: "include",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(
      typeof err.detail === "string" ? err.detail : `Download failed (${res.status})`
    );
  }
  const blob = await res.blob();
  // Force octet-stream so browsers prefer "save" over "display"
  const forced = new Blob([blob], {
    type: "application/octet-stream",
  });
  saveBlob(forced, filename || "lucero-asset");
}
