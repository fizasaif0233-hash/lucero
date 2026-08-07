import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

/**
 * Same-origin download proxy. Returns Content-Disposition: attachment
 * so the browser saves the file instead of navigating Lucero away.
 */
export async function GET(req: NextRequest) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401 });
  }

  const url = req.nextUrl.searchParams.get("url");
  const filename =
    req.nextUrl.searchParams.get("filename") || "lucero-asset.bin";
  if (!url || !/^https?:\/\//i.test(url)) {
    return NextResponse.json({ detail: "Invalid url" }, { status: 400 });
  }

  let host = "";
  try {
    host = new URL(url).hostname.toLowerCase();
  } catch {
    return NextResponse.json({ detail: "Invalid url" }, { status: 400 });
  }
  const allowed =
    host.endsWith(".supabase.co") ||
    host.includes("replicate.delivery") ||
    host.endsWith(".replicate.delivery");
  if (!allowed) {
    return NextResponse.json({ detail: "Host not allowed" }, { status: 403 });
  }

  const upstream = await fetch(url, { redirect: "follow" });
  if (!upstream.ok) {
    return NextResponse.json(
      { detail: `Upstream ${upstream.status}` },
      { status: 502 }
    );
  }

  const buf = Buffer.from(await upstream.arrayBuffer());
  const mime =
    upstream.headers.get("content-type") || "application/octet-stream";
  const safe = filename.replace(/[^\w.\-]+/g, "_").slice(0, 120);

  return new NextResponse(buf, {
    status: 200,
    headers: {
      "Content-Type": mime.split(";")[0].trim(),
      "Content-Disposition": `attachment; filename="${safe}"`,
      "Cache-Control": "private, no-store",
      "X-Content-Type-Options": "nosniff",
    },
  });
}
