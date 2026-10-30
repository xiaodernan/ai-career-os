"use client";

import * as React from "react";
import { LogOut, MonitorSmartphone, ShieldCheck } from "lucide-react";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import type { AccountSession } from "@/lib/api/types";
import { formatDateTime } from "@/lib/format";
import { useRevokeAllSessions, useRevokeSession, useSessions } from "@/lib/hooks/account";
import { describe } from "@/lib/hooks/failure";
import { useLocale } from "@/lib/i18n/locale-context";
import { deviceLabel, sessionCloseRefusal } from "@/lib/sessions";

type Confirmation = { kind: "one"; session: AccountSession } | { kind: "all" } | null;

/**
 * The account's open doors (38.3).
 *
 * One refresh-token family is one row, however often it rotates, and the family that is
 * asking is marked — the backend reads it from the access token, so the screen never has
 * to guess which row is this tab. Closing a row is a real revocation, and the two dialogs
 * say the true consequence instead of "signed out": closing another device signs it out
 * at its next refresh, closing this one behaves like logout, and closing everything leaves
 * this tab working only until its access token expires.
 *
 * A family that is not live for this account answers one 404. The reader cannot act on
 * that refusal, so it is read as "this door was already shut" and the list refetches,
 * rather than an apology for an error the screen could have caught itself.
 */
export function SessionsCard() {
  const { t, locale } = useLocale();
  const sessions = useSessions();
  const revokeOne = useRevokeSession();
  const revokeAll = useRevokeAllSessions();

  const [confirm, setConfirm] = React.useState<Confirmation>(null);
  const [notice, setNotice] = React.useState<string | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const label = (session: AccountSession) =>
    deviceLabel(session.userAgent, t("sessions.unknownDevice"));

  const closeConfirmed = () => {
    if (!confirm) return;
    setNotice(null);
    setError(null);
    if (confirm.kind === "all") {
      revokeAll.mutate(undefined, {
        onSuccess: () => setConfirm(null),
        onError: (err) => {
          setConfirm(null);
          setError(describe(err));
        },
      });
      return;
    }
    revokeOne.mutate(confirm.session.id, {
      onSuccess: () => setConfirm(null),
      onError: (err) => {
        setConfirm(null);
        if (sessionCloseRefusal(err) === "gone") setNotice(t("sessions.alreadyClosed"));
        else setError(describe(err));
      },
    });
  };

  const busy = revokeOne.isPending || revokeAll.isPending;
  const rows = sessions.data ?? [];
  const closing = confirm;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <MonitorSmartphone className="size-4 text-muted-foreground" aria-hidden />
          {t("sessions.title")}
        </CardTitle>
        <CardDescription>{t("sessions.description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {sessions.isPending ? (
          <p className="text-sm text-muted-foreground">{t("sessions.loading")}</p>
        ) : sessions.isError ? (
          <div className="flex items-center justify-between gap-3">
            <p className="text-sm text-danger">{t("sessions.loadFailed")}</p>
            <Button size="sm" variant="outline" onClick={() => void sessions.refetch()}>
              {t("common.retry")}
            </Button>
          </div>
        ) : rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">{t("sessions.empty")}</p>
        ) : (
          <ul className="divide-y divide-border rounded-lg border border-border">
            {rows.map((session) => {
              const device = label(session);
              return (
                <li key={session.id} className="flex flex-wrap items-start justify-between gap-3 p-3">
                  <div className="min-w-0 space-y-1">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="truncate text-sm font-medium" title={device}>
                        {device}
                      </span>
                      {session.current ? (
                        <Badge variant="outline" className="gap-1">
                          <ShieldCheck className="size-3" aria-hidden />
                          {t("sessions.current")}
                        </Badge>
                      ) : null}
                    </div>
                    {session.current ? (
                      <p className="text-xs text-muted-foreground">{t("sessions.currentNote")}</p>
                    ) : null}
                    <div className="flex flex-wrap gap-x-3 gap-y-1 text-xs text-muted-foreground">
                      {session.clientIp ? (
                        <span>{t("sessions.address", { address: session.clientIp })}</span>
                      ) : null}
                      <span>{t("sessions.started", { when: formatDateTime(session.startedAt, locale) })}</span>
                      {session.lastSeenAt ? (
                        <span>{t("sessions.seen", { when: formatDateTime(session.lastSeenAt, locale) })}</span>
                      ) : null}
                      {session.expiresAt ? (
                        <span>{t("sessions.expires", { when: formatDateTime(session.expiresAt, locale) })}</span>
                      ) : null}
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={busy}
                    aria-label={t("sessions.closeNamed", { device })}
                    onClick={() => {
                      setNotice(null);
                      setError(null);
                      setConfirm({ kind: "one", session });
                    }}
                  >
                    {t("sessions.close")}
                  </Button>
                </li>
              );
            })}
          </ul>
        )}

        {notice ? (
          <p className="text-sm text-muted-foreground" aria-live="polite">
            {notice}
          </p>
        ) : null}
        {error ? (
          <p className="text-sm text-danger" aria-live="polite">
            {error}
          </p>
        ) : null}

        {rows.length > 0 ? (
          <>
            <Separator />
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="text-sm text-muted-foreground">{t("sessions.closeAllHint")}</p>
              <Button
                size="sm"
                variant="danger"
                disabled={busy}
                onClick={() => {
                  setNotice(null);
                  setError(null);
                  setConfirm({ kind: "all" });
                }}
              >
                <LogOut aria-hidden />
                {t("sessions.closeAll")}
              </Button>
            </div>
          </>
        ) : null}
      </CardContent>

      <ConfirmDialog
        open={closing !== null}
        onOpenChange={(open) => {
          if (!open && !busy) setConfirm(null);
        }}
        title={closing?.kind === "all" ? t("sessions.closeAllTitle") : t("sessions.closeTitle")}
        description={
          closing === null
            ? undefined
            : closing.kind === "all"
              ? t("sessions.closeAllDescription")
              : closing.session.current
                ? t("sessions.closeCurrentDescription")
                : t("sessions.closeOneDescription", { device: label(closing.session) })
        }
        confirmLabel={closing?.kind === "all" ? t("sessions.closeAll") : t("sessions.close")}
        destructive
        loading={busy}
        onConfirm={closeConfirmed}
      />
    </Card>
  );
}
