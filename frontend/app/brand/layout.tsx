import { Cinzel, Cormorant_Garamond, Great_Vibes } from "next/font/google";
import type { Metadata } from "next";
import "./flyers/print.css";

const cinzel = Cinzel({
  subsets: ["latin"],
  variable: "--font-cinzel",
  weight: ["400", "600"],
});

const editorial = Cormorant_Garamond({
  subsets: ["latin"],
  variable: "--font-editorial",
  weight: ["400", "500", "600"],
});

const script = Great_Vibes({
  subsets: ["latin"],
  variable: "--font-script",
  weight: "400",
});

export const metadata: Metadata = {
  title: "Blue Prince 21 | Magazine flyers",
  description: "Print-ready Blue Prince 21 McKinzy flyers using official bottle photography.",
};

export default function BrandLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <div className={`${cinzel.variable} ${editorial.variable} ${script.variable}`}>
      {children}
    </div>
  );
}
