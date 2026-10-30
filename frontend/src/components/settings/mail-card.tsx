"use client";

import { ArrowUpRight, Mail } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { CopyButton } from "@/components/common/export-buttons";
import { useLocale } from "@/lib/i18n/locale-context";
import { useMailSettings, useSetMailDial, type MailDial } from "@/lib/hooks/mail-settings";
import { safeHref } from "@/lib/safe-href";

/**
 * The three mail dials, reachable without an old letter (42.1, 42.2).
 *
 * The card states what each letter is doing, settles each dial through the account,
 * and hands over the same signed page a letter's footer would have opened -- so a
 * reader who deleted every mail, or who never waited for one, has every way in. The
 * booleans come from the account's own columns, so the switches and the page's buttons
 * are two doors to one state rather than two answers.
 *
 * One press at a time: every write answers with all three dials, so two writes in
 * flight would each answer with the other's before-state. A failed write moves the
 * switch back and says so, because a switch left where the reader put it would claim
 * a letter is off that the sweep still mails.
 *
 * A failed read is a sentence rather than blank toggles, because "nothing is on" and
 * "the answer did not arrive" are different facts and only the second is fixed by
 * reloading.
 */
export function MailCard() {
  const { t } = useLocale();
  const { data, isPending, isError } = useMailSettings();
  const save = useSetMailDial();
  const url = data?.url ?? "";
  // The address is built by the backend, but it is still a value this card did not
  // build: `safeHref` is what turns it into an href that may open a page, and a value
  // it refuses is a card with no link rather than a click that goes somewhere else.
  const href = safeHref(data?.url);

  const dials: { key: MailDial; label: string; on: boolean | undefined }[] = [
    { key: "weekly", label: t("mailLetters.weekly"), on: data?.weekly },
    { key: "signals", label: t("mailLetters.signals"), on: data?.signals },
    { key: "reminders", label: t("mailLetters.reminders"), on: data?.reminders },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{t("mailLetters.title")}</CardTitle>
        <CardDescription>{t("mailLetters.description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-3">
        {isPending ? (
          <p className="text-sm text-muted-foreground">{t("mailLetters.loading")}</p>
        ) : isError ? (
          <p className="text-sm text-danger">{t("mailLetters.loadFailed")}</p>
        ) : (
          <>
            <ul className="space-y-2">
              {dials.map((dial) => (
                <li key={dial.key} className="flex items-center justify-between gap-3 text-sm">
                  <Label
                    htmlFor={`mail-dial-${dial.key}`}
                    className="font-normal text-muted-foreground"
                  >
                    {dial.label}
                  </Label>
                  <span className="flex items-center gap-2">
                    <span className="w-6 text-right text-xs text-muted-foreground">
                      {dial.on ? t("mailLetters.on") : t("mailLetters.off")}
                    </span>
                    <Switch
                      id={`mail-dial-${dial.key}`}
                      size="sm"
                      checked={Boolean(dial.on)}
                      disabled={save.isPending}
                      onCheckedChange={(next) => save.mutate({ list: dial.key, enabled: next })}
                    />
                  </span>
                </li>
              ))}
            </ul>
            <div className="space-y-2">
              <Label htmlFor="mail-settings-link" className="flex items-center gap-2">
                <Mail className="size-4 text-muted-foreground" aria-hidden />
                {t("mailLetters.linkLabel")}
              </Label>
              <div className="flex items-center gap-2">
                <Input
                  id="mail-settings-link"
                  value={url}
                  readOnly
                  spellCheck={false}
                  className="font-mono text-xs"
                  onFocus={(event) => event.currentTarget.select()}
                />
                <CopyButton text={url} label={t("mailLetters.copy")} />
              </div>
            </div>
          </>
        )}
        <div className="flex items-start justify-between gap-3 pt-1">
          <p className="text-sm text-muted-foreground">{t("mailLetters.hint")}</p>
          {!isPending && !isError && href ? (
            <Button asChild size="sm" variant="ghost" className="shrink-0">
              <a href={href} target="_blank" rel="noreferrer">
                <ArrowUpRight aria-hidden />
                {t("mailLetters.open")}
              </a>
            </Button>
          ) : null}
        </div>
      </CardContent>
    </Card>
  );
}
