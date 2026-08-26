import { notFound } from "next/navigation";
import { FlyerToolbar } from "@/components/brand/FlyerToolbar";
import { MagazineFlyer } from "@/components/brand/MagazineFlyer";
import { FLYERS, flyerBySlug } from "@/lib/brand/assets";

export function generateStaticParams() {
  return FLYERS.map((flyer) => ({ slug: flyer.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const spec = flyerBySlug(slug);
  return {
    title: spec ? `${spec.title} | Blue Prince 21` : "Flyer | Blue Prince 21",
  };
}

export default async function FlyerPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const spec = flyerBySlug(slug);
  if (!spec) notFound();

  return (
    <div className="flyer-stage">
      <FlyerToolbar slug={slug} />
      <MagazineFlyer slug={slug} />
      <p className="no-print max-w-[42rem] text-center text-[11px] tracking-[0.18em] text-[#cbb890]/80 uppercase">
        Letter 8.5×11 · print or save as PDF · official bottle photography
      </p>
    </div>
  );
}
