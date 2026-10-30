import Link from "next/link";
import { cookies } from "next/headers";
import { Button } from "@/components/ui/button";
import { LOCALE_COOKIE, localeFromCookie } from "@/lib/i18n/locale-cookie";
import { readKey, sectionMetadata } from "@/lib/i18n/metadata";

export const generateMetadata = sectionMetadata("auth.pageTitles.accountErased");

/**
 * Where the erasure ends (38.5).
 *
 * The reader has no account and no session any more, so this page must not be behind the
 * app shell and must not bounce through a request that answers 401 or 404. It is a public
 * (auth) page, rendered on the server from the locale cookie like the titles are: nothing
 * here is interactive, and the sentence has to be painted in the reader's language on the
 * first response — it is the only confirmation the reader gets.
 *
 * It says what the erasure did and what it could not reach: the live system's rows and
 * stored files are gone; backups outside it keep what they captured until their retention
 * window passes, and letters already delivered stay in their mailboxes. The two doors that
 * remain are the two links.
 */
export default async function AccountErasedPage() {
  const store = await cookies();
  const locale = localeFromCookie(store.get(LOCALE_COOKIE)?.value);

  return (
    <div className="space-y-6">
      <header className="space-y-1.5">
        <h2 className="font-serif text-display-sm font-medium">
          {readKey(locale, "accountErased.title")}
        </h2>
        <p className="text-sm text-muted-foreground">{readKey(locale, "accountErased.body")}</p>
      </header>

      <div className="space-y-1.5 rounded-lg border border-border bg-muted/40 p-4">
        <p className="text-sm font-medium">{readKey(locale, "accountErased.keptTitle")}</p>
        <p className="text-sm text-muted-foreground">{readKey(locale, "accountErased.keptBody")}</p>
      </div>

      <div className="space-y-3">
        <Button asChild variant="ai" size="lg" className="w-full">
          <Link href="/register">{readKey(locale, "accountErased.startAgain")}</Link>
        </Button>
        <p className="text-center text-sm text-muted-foreground">
          <Link href="/login" className="text-primary underline-offset-4 hover:underline">
            {readKey(locale, "accountErased.signInOther")}
          </Link>
        </p>
      </div>
    </div>
  );
}
