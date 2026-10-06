import type { Metadata } from "next";

export const metadata: Metadata = { title: "Run" };

export default function Layout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return children;
}
