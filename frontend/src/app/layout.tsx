import type { Metadata, Viewport } from "next";
import { Inter, Newsreader, JetBrains_Mono } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";
import { DocumentTitle } from "@/components/layout/document-title";
import { LocaleProvider } from "@/lib/i18n/locale-context";

const inter = Inter({
  variable: "--font-inter",
  subsets: ["latin"],
  display: "swap",
});

const newsreader = Newsreader({
  variable: "--font-newsreader",
  subsets: ["latin"],
  style: ["normal", "italic"],
  display: "swap",
});

const jetbrains = JetBrains_Mono({
  variable: "--font-jetbrains",
  subsets: ["latin"],
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "AI Career OS",
    template: "%s · AI Career OS",
  },
  description:
    "Your personal job-search operating system — evidence-backed matching, resume intelligence, and AI-guided interviews.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#fcfcfd" },
    { media: "(prefers-color-scheme: dark)", color: "#141518" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body
        className={`${inter.variable} ${newsreader.variable} ${jetbrains.variable} min-h-dvh bg-background text-foreground`}
      >
        <LocaleProvider>
          <Providers>
            <DocumentTitle />
            {children}
          </Providers>
        </LocaleProvider>
      </body>
    </html>
  );
}
