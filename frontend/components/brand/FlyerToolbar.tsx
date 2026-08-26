"use client";

import Link from "next/link";
import { Printer, Download, ArrowLeft } from "lucide-react";
import { flyerBySlug, photoById } from "@/lib/brand/assets";

export function FlyerToolbar({ slug }: { slug: string }) {
  const spec = flyerBySlug(slug);
  const photo = spec ? photoById(spec.photoId) : null;

  return (
    <div className="flyer-toolbar no-print flex w-full max-w-[42rem] flex-wrap items-center justify-between gap-2 rounded-2xl border border-white/10 bg-black/40 px-3 py-2 text-sm text-[#f6edd8] backdrop-blur">
      <Link
        href="/dashboard/brand"
        className="inline-flex items-center gap-2 rounded-lg px-2 py-1.5 text-[#e8d5a3] hover:text-white"
      >
        <ArrowLeft size={15} />
        Brand studio
      </Link>
      <div className="flex flex-wrap items-center gap-2">
        {photo && (
          <a
            href={photo.src}
            download
            className="inline-flex items-center gap-2 rounded-lg border border-white/15 px-3 py-1.5 hover:bg-white/10"
          >
            <Download size={14} />
            Original photo
          </a>
        )}
        <button
          type="button"
          onClick={() => window.print()}
          className="inline-flex items-center gap-2 rounded-lg bg-[#d4b056] px-3 py-1.5 font-medium text-black hover:bg-[#e4c56a]"
        >
          <Printer size={14} />
          Print / Save PDF
        </button>
      </div>
    </div>
  );
}
