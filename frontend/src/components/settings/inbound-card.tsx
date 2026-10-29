"use client";

import Link from "next/link";
import { ArrowUpRight, Mail } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { CopyButton } from "@/components/common/export-buttons";
import { ApiError } from "@/lib/api/client";
import { useLocale } from "@/lib/i18n/locale-context";
import { useInboundLink } from "@/lib/hooks/replies";

/**
 * The address recruiters' replies come back to (37.4).
 *
 * A reply arrives through a mail provider's webhook, not through a mailbox the reader
 * signs into, so this card is the one place the address exists on screen: a copy target,
 * with the warning that the address is the whole credential directly beside it. A
 * deployment that has no receiving domain is a sentence, not an empty box -- "no inbox
 * here" and "try again" are different answers, and the card can tell them apart because
 * the backend names the first with `INBOUND_NOT_CONFIGURED`.
 */
export function InboundCard() {
  const { t } = useLocale();
  const { data, isPending, isError, error } = useInboundLink();
  const address = data?.address ?? "";
  const notConfigured = error instanceof ApiError && error.code === "INBOUND_NOT_CONFIGURED";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("inbound.title")}</CardTitle>
        <CardDescription>{t("inbound.description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label htmlFor="inbound-address" className="flex items-center gap-2">
            <Mail className="size-4 text-muted-foreground" aria-hidden />
            {t("inbound.addressLabel")}
          </Label>
          {isPending ? (
            <p className="text-sm text-muted-foreground">{t("inbound.loading")}</p>
          ) : notConfigured ? (
            <p className="text-sm text-muted-foreground">{t("inbound.notConfigured")}</p>
          ) : isError ? (
            <p className="text-sm text-danger">{t("inbound.loadFailed")}</p>
          ) : (
            <>
              <div className="flex items-center gap-2">
                <Input
                  id="inbound-address"
                  value={address}
                  readOnly
                  spellCheck={false}
                  className="font-mono text-xs"
                  onFocus={(event) => event.currentTarget.select()}
                />
                <CopyButton text={address} label={t("inbound.copy")} />
              </div>
              <p className="rounded-md border border-border/70 bg-muted/40 px-3 py-2 text-xs text-muted-foreground">
                {t("inbound.rotationWarning")}
              </p>
            </>
          )}
        </div>
        <div className="flex items-start justify-between gap-3 pt-1">
          <p className="text-sm text-muted-foreground">{t("inbound.hint")}</p>
          <Button asChild size="sm" variant="ghost" className="shrink-0">
            <Link href="/replies">
              <ArrowUpRight aria-hidden />
              {t("inbound.openReplies")}
            </Link>
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
