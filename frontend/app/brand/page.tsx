import Link from "next/link";
import { FLYERS, PRODUCT_PHOTOS, photoById } from "@/lib/brand/assets";

export default function BrandLookbookPage() {
  const hero = photoById("pair");

  return (
    <main className="min-h-dvh bg-[#07080c] text-[#f6edd8]">
      <section className="relative min-h-[88dvh] overflow-hidden">
        <img
          src={hero.src}
          alt={hero.alt}
          className="absolute inset-0 h-full w-full object-cover"
        />
        <div className="absolute inset-0 bg-gradient-to-t from-black via-black/25 to-black/45" />
        <div className="relative z-10 flex min-h-[88dvh] flex-col justify-between px-6 py-8 md:px-12">
          <p
            className="text-[11px] uppercase tracking-[0.42em] text-[#e8d5a3]"
            style={{ fontFamily: "var(--font-cinzel), serif" }}
          >
            McKinzy · Hecho en México
          </p>
          <div>
            <h1
              className="text-4xl uppercase tracking-[0.12em] md:text-6xl"
              style={{ fontFamily: "var(--font-cinzel), serif" }}
            >
              Blue Prince 21
            </h1>
            <p
              className="mt-2 text-3xl text-[#f0d48a]"
              style={{ fontFamily: "var(--font-script), cursive" }}
            >
              Sipping Elegance
            </p>
            <p className="mt-4 max-w-xl text-sm text-[#f3e6c8]/85 md:text-base">
              Official bottle photography for magazine, menu, and campaign use.
              Blanco and Añejo — the real bottles, never a stand-in.
            </p>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-6 py-14 md:px-12">
        <h2
          className="mb-6 text-[11px] uppercase tracking-[0.28em] text-[#d4b056]"
          style={{ fontFamily: "var(--font-cinzel), serif" }}
        >
          The bottles
        </h2>
        <div className="grid gap-5 md:grid-cols-3">
          {PRODUCT_PHOTOS.map((photo) => (
            <figure key={photo.id} className="overflow-hidden rounded-2xl border border-[#d4b056]/25">
              <img src={photo.src} alt={photo.alt} className="aspect-[4/5] w-full object-cover" />
              <figcaption className="px-4 py-3">
                <p className="text-sm">{photo.title}</p>
                <p className="text-[11px] text-[#cbb890]">{photo.details}</p>
              </figcaption>
            </figure>
          ))}
        </div>

        <h2
          className="mb-6 mt-14 text-[11px] uppercase tracking-[0.28em] text-[#d4b056]"
          style={{ fontFamily: "var(--font-cinzel), serif" }}
        >
          Print flyers
        </h2>
        <div className="grid gap-3 sm:grid-cols-2">
          {FLYERS.map((flyer) => (
            <Link
              key={flyer.slug}
              href={`/brand/flyers/${flyer.slug}`}
              className="rounded-2xl border border-[#d4b056]/25 px-4 py-4 hover:border-[#d4b056]/60 hover:bg-white/5"
            >
              <p className="text-sm">{flyer.title}</p>
              <p className="text-[11px] text-[#cbb890]">{flyer.subtitle} · Letter 8.5×11</p>
            </Link>
          ))}
        </div>
      </section>
    </main>
  );
}
