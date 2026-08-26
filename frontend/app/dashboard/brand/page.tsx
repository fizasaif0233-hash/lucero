"use client";

import Link from "next/link";
import { Download, Printer, Wine } from "lucide-react";
import { SecondaryShell } from "@/components/jarvis/SecondaryShell";
import { FLYERS, PRODUCT_PHOTOS, photoById } from "@/lib/brand/assets";

export default function BrandStudioPage() {
  return (
    <SecondaryShell title="Brand studio">
      <div className="h-full overflow-y-auto p-6 md:p-8">
        <div className="mx-auto max-w-6xl animate-fadeIn">
          <div className="mb-8 flex items-start gap-4">
            <span className="rounded-2xl border border-jarvis-cyan/30 bg-jarvis-cyan/10 p-3 text-jarvis-cyan">
              <Wine size={22} />
            </span>
            <div>
              <h1 className="font-display text-3xl tracking-wide mb-2">
                Brand studio
              </h1>
              <p className="text-sm text-jarvis-muted max-w-2xl">
                Official Blue Prince 21 McKinzy bottle photography is now in
                L.U.C.E.R.O. These are the real bottles — use them on magazine
                pages, ads, and menus. Open a flyer, then Print / Save as PDF.
                Public lookbook:{" "}
                <Link href="/brand" className="text-jarvis-cyan hover:underline">
                  /brand
                </Link>
                .
              </p>
            </div>
          </div>

          <h2 className="mb-3 text-[11px] uppercase tracking-[0.18em] text-jarvis-cyan">
            Official product photos
          </h2>
          <div className="mb-10 grid gap-4 md:grid-cols-3">
            {PRODUCT_PHOTOS.map((photo) => (
              <figure
                key={photo.id}
                className="overflow-hidden rounded-2xl border border-jarvis-border bg-jarvis-elevated/50"
              >
                <img
                  src={photo.src}
                  alt={photo.alt}
                  className="aspect-[4/5] w-full object-cover"
                />
                <figcaption className="px-4 py-3">
                  <p className="text-sm text-jarvis-text">{photo.title}</p>
                  <p className="text-[11px] text-jarvis-muted">{photo.details}</p>
                  <a
                    href={photo.src}
                    download
                    className="mt-2 inline-flex items-center gap-1.5 text-[11px] text-jarvis-cyan hover:underline"
                  >
                    <Download size={12} />
                    Download original
                  </a>
                </figcaption>
              </figure>
            ))}
          </div>

          <h2 className="mb-3 text-[11px] uppercase tracking-[0.18em] text-jarvis-cyan">
            Magazine flyers
          </h2>
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {FLYERS.map((flyer) => {
              const photo = photoById(flyer.photoId);
              return (
                <article
                  key={flyer.slug}
                  className="flex flex-col overflow-hidden rounded-2xl border border-jarvis-border bg-jarvis-elevated/50"
                >
                  <Link
                    href={`/brand/flyers/${flyer.slug}`}
                    className="relative block aspect-[8.5/11] overflow-hidden"
                  >
                    <img
                      src={photo.src}
                      alt={photo.alt}
                      className="h-full w-full object-cover"
                    />
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/35" />
                    <div className="absolute inset-x-0 bottom-0 p-3">
                      <p className="text-[10px] uppercase tracking-[0.22em] text-amber-200/90">
                        {flyer.kicker}
                      </p>
                      <p className="font-display text-sm tracking-wide text-white">
                        {flyer.headline}
                      </p>
                    </div>
                  </Link>
                  <div className="flex items-center justify-between gap-2 px-3 py-3">
                    <div>
                      <p className="text-sm">{flyer.title}</p>
                      <p className="text-[11px] text-jarvis-muted">
                        {flyer.subtitle}
                      </p>
                    </div>
                    <Link
                      href={`/brand/flyers/${flyer.slug}`}
                      className="inline-flex items-center gap-1 rounded-lg border border-jarvis-cyan/40 px-2 py-1 text-[11px] text-jarvis-cyan hover:bg-jarvis-cyan/10"
                    >
                      <Printer size={12} />
                      Print
                    </Link>
                  </div>
                </article>
              );
            })}
          </div>
        </div>
      </div>
    </SecondaryShell>
  );
}
