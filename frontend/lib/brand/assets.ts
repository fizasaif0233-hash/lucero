export type ProductPhoto = {
  id: "blanco" | "anejo" | "pair";
  title: string;
  expression: string;
  src: "/brand/product/blanco.jpeg" | "/brand/product/anejo.jpeg" | "/brand/product/pair.jpeg";
  alt: string;
  details: string;
};

export type FlyerSpec = {
  slug: "cover" | "blanco" | "anejo" | "collection";
  title: string;
  subtitle: string;
  photoId: ProductPhoto["id"];
  kicker: string;
  headline: string;
  script: string;
  footer: string;
  notes?: string[];
};

export const PRODUCT_PHOTOS: ProductPhoto[] = [
  {
    id: "blanco",
    title: "Blue Prince 21 Blanco",
    expression: "Tequila Blanco",
    src: "/brand/product/blanco.jpeg",
    alt: "Official Blue Prince 21 McKinzy Tequila Blanco bottle in an agave field at sunset",
    details: "40% Alc. Vol. · 100% Agave · 750 ml · Hecho en México",
  },
  {
    id: "anejo",
    title: "Blue Prince 21 Añejo",
    expression: "Tequila Añejo",
    src: "/brand/product/anejo.jpeg",
    alt: "Official Blue Prince 21 McKinzy Tequila Añejo bottle in an agave field at sunset",
    details: "40% Alc. Vol. · 100% Agave · 750 ml · Hecho en México",
  },
  {
    id: "pair",
    title: "The Collection",
    expression: "Blanco & Añejo",
    src: "/brand/product/pair.jpeg",
    alt: "Official Blue Prince 21 McKinzy Blanco and Añejo bottles together at golden hour",
    details: "Sipping Elegance · Anthony Warren Mckinzy",
  },
];

export const FLYERS: FlyerSpec[] = [
  {
    slug: "cover",
    title: "Magazine cover",
    subtitle: "Both expressions · golden hour",
    photoId: "pair",
    kicker: "McKinzy · Vol. 21",
    headline: "Blue Prince",
    script: "Sipping Elegance",
    footer: "Blanco  ·  Añejo  ·  100% Agave  ·  Hecho en México",
  },
  {
    slug: "blanco",
    title: "Blanco editorial",
    subtitle: "Crystal-clear sipping tequila",
    photoId: "blanco",
    kicker: "Tequila Blanco",
    headline: "Blue Prince 21",
    script: "Sipping Elegance",
    footer: "40% Alc. Vol.  ·  100% Agave  ·  750 ml  ·  Hecho en México",
    notes: [
      "Unaged 100% agave Blanco",
      "Floral wreath bottle · crystal stopper",
      "Signed Anthony Warren Mckinzy",
    ],
  },
  {
    slug: "anejo",
    title: "Añejo editorial",
    subtitle: "Barrel-aged gold",
    photoId: "anejo",
    kicker: "Tequila Añejo",
    headline: "Blue Prince 21",
    script: "Sipping Elegance",
    footer: "40% Alc. Vol.  ·  100% Agave  ·  750 ml  ·  Hecho en México",
    notes: [
      "Amber Añejo · gold lettering on glass",
      "Crystal stopper · navy agave seal",
      "Signed Anthony Warren Mckinzy",
    ],
  },
  {
    slug: "collection",
    title: "Luxury collection",
    subtitle: "House of McKinzy · print ad",
    photoId: "pair",
    kicker: "The House of McKinzy",
    headline: "Two Expressions",
    script: "Sipping Elegance",
    footer: "Blue Prince 21  ·  Blanco & Añejo  ·  Hecho en México",
  },
];

export const LUCERO_ORB = "/brand/lucero.webp";

export function photoById(id: ProductPhoto["id"]): ProductPhoto {
  const photo = PRODUCT_PHOTOS.find((item) => item.id === id);
  if (!photo) throw new Error(`Unknown product photo: ${id}`);
  return photo;
}

export function flyerBySlug(slug: string): FlyerSpec | undefined {
  return FLYERS.find((item) => item.slug === slug);
}
