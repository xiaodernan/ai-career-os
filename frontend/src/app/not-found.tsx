import type { Metadata } from "next";
import { NotFoundBody } from "@/components/common/not-found-body";

export const metadata: Metadata = { title: "Page not found" };

/**
 * The 404 page.
 *
 * It stays a server component because it exports `metadata`, and Next does
 * not allow that from a `"use client"` file. The body it renders is a
 * client component, because the body reads the locale table and the locale
 * table is a context.
 */
export default function NotFound() {
  return <NotFoundBody />;
}
