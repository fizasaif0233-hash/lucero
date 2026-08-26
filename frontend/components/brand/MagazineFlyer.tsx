import {
  LUCERO_ORB,
  flyerBySlug,
  photoById,
  type FlyerSpec,
} from "@/lib/brand/assets";

export function MagazineFlyer({ slug }: { slug: string }) {
  const spec = flyerBySlug(slug);
  if (!spec) return null;
  return <FlyerCanvas spec={spec} />;
}

function FlyerCanvas({ spec }: { spec: FlyerSpec }) {
  const photo = photoById(spec.photoId);
  const collection = spec.slug === "collection";

  return (
    <article className="flyer-sheet" aria-label={spec.title}>
      <img className="flyer-photo" src={photo.src} alt={photo.alt} />
      <div className={`flyer-veil${collection ? " collection" : ""}`} />
      {collection && (
        <img className="flyer-orb" src={LUCERO_ORB} alt="" />
      )}
      <div className="flyer-copy">
        <header>
          <p className="flyer-kicker">{spec.kicker}</p>
          <div className="flyer-rule" />
        </header>
        <footer>
          <h1 className="flyer-headline">{spec.headline}</h1>
          <p className="flyer-script">{spec.script}</p>
          {spec.notes && spec.notes.length > 0 && (
            <ul className="flyer-notes">
              {spec.notes.map((note) => (
                <li key={note}>{note}</li>
              ))}
            </ul>
          )}
          <p className="flyer-footer" style={{ marginTop: "0.9rem" }}>
            {spec.footer}
          </p>
        </footer>
      </div>
    </article>
  );
}

