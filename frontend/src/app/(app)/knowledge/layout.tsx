import { sectionMetadata } from "@/lib/i18n/metadata";
export const generateMetadata = sectionMetadata("nav.knowledge");

export default function Layout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return children;
}
