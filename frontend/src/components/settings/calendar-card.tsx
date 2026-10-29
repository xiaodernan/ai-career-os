"use client";

import { CalendarDays } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { CopyButton } from "@/components/common/export-buttons";
import { useLocale } from "@/lib/i18n/locale-context";
import { useCalendarLink } from "@/lib/hooks/calendar";

/**
 * The address a calendar app subscribes to (roadmap 34.1).
 *
 * The card shows the signed URL and nothing else: the backend already decided who
 * this account is, so the screen is a copy target, not a form. The address is read
 * only -- typing into it would only produce a token the backend refuses -- and a
 * failed sign-in-free read is a sentence rather than an empty box, because a blank
 * input reads as "no address exists" when the truth is "try again".
 */
export function CalendarCard() {
  const { t } = useLocale();
  const { data, isPending, isError } = useCalendarLink();
  const url = data?.url ?? "";

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("calendar.title")}</CardTitle>
        <CardDescription>{t("calendar.description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-2">
          <Label htmlFor="calendar-link" className="flex items-center gap-2">
            <CalendarDays className="size-4 text-muted-foreground" aria-hidden />
            {t("calendar.linkLabel")}
          </Label>
          {isPending ? (
            <p className="text-sm text-muted-foreground">{t("calendar.loading")}</p>
          ) : isError ? (
            <p className="text-sm text-danger">{t("calendar.loadFailed")}</p>
          ) : (
            <div className="flex items-center gap-2">
              <Input
                id="calendar-link"
                value={url}
                readOnly
                spellCheck={false}
                className="font-mono text-xs"
                onFocus={(event) => event.currentTarget.select()}
              />
              <CopyButton text={url} label={t("calendar.copy")} />
            </div>
          )}
        </div>
        <p className="text-sm text-muted-foreground">{t("calendar.hint")}</p>
      </CardContent>
    </Card>
  );
}
