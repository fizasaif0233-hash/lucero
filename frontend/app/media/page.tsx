import { redirect } from "next/navigation";

/** Short alias so /media always reaches the gallery. */
export default function MediaAliasPage() {
  redirect("/dashboard/media");
}
