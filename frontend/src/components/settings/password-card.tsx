"use client";

import * as React from "react";
import { KeyRound } from "lucide-react";
import { AuthField } from "@/components/auth/auth-field";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { confirmationIssue, passwordIssue } from "@/lib/auth-recovery";
import { useChangePassword } from "@/lib/hooks/account";
import { describe } from "@/lib/hooks/failure";
import { useLocale } from "@/lib/i18n/locale-context";
import { issueText } from "@/lib/i18n/issue";
import { currentPasswordIssue, passwordChangeRefusal } from "@/lib/password-change";

/**
 * The lock on the account (38.4).
 *
 * `PATCH /me/password` has taken a new value since Epic 24, but the page that shows the
 * account's open doors never offered it: the only way to replace a password was the
 * mailed reset. The card asks for the current password because the server does — a
 * borrowed tab must not be able to lock the owner out — and for the new one twice,
 * checking the record's own `(8, 72)` bounds before a request leaves the browser.
 *
 * Success replaces the form rather than clearing it into a toast, because the server's
 * consequence is larger than "saved": every refresh token is revoked, so every other
 * device signs out at its next refresh, and this tab keeps working only until its own
 * access token expires. A cleared form would read as if nothing else had happened.
 *
 * `PASSWORD_UNCHANGED` is drawn under the new-password field as a refusal, not an
 * error: re-storing the same value would sign every other device out for nothing, so
 * the server declines before it writes and nothing was revoked.
 */
export function PasswordCard() {
  const { t } = useLocale();
  const change = useChangePassword();

  const [current, setCurrent] = React.useState("");
  const [next, setNext] = React.useState("");
  const [confirm, setConfirm] = React.useState("");
  const [currentError, setCurrentError] = React.useState<string | undefined>();
  const [nextError, setNextError] = React.useState<string | undefined>();
  const [confirmError, setConfirmError] = React.useState<string | undefined>();
  const [formError, setFormError] = React.useState<string | undefined>();
  const [changed, setChanged] = React.useState(false);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const currentText = issueText(currentPasswordIssue(current), t);
    const nextText = issueText(passwordIssue(next), t);
    const confirmText = issueText(confirmationIssue(confirm, next), t);
    setCurrentError(currentText);
    setNextError(nextText);
    setConfirmError(confirmText);
    setFormError(undefined);
    if (currentText || nextText || confirmText || change.isPending) return;
    change.mutate(
      { currentPassword: current, newPassword: next },
      {
        onSuccess: () => {
          setChanged(true);
          setCurrent("");
          setNext("");
          setConfirm("");
          setCurrentError(undefined);
          setNextError(undefined);
          setConfirmError(undefined);
        },
        onError: (err) => {
          const field = passwordChangeRefusal(err);
          if (field === "current") setCurrentError(describe(err));
          else if (field === "new") setNextError(describe(err));
          else setFormError(describe(err));
        },
      },
    );
  };

  const again = () => {
    setChanged(false);
    setFormError(undefined);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <KeyRound className="size-4 text-muted-foreground" aria-hidden />
          {t("passwordChange.title")}
        </CardTitle>
        <CardDescription>{t("passwordChange.description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {changed ? (
          <div className="space-y-3 rounded-lg border border-border bg-muted/40 p-4">
            <p className="text-sm font-medium">{t("passwordChange.changedTitle")}</p>
            <p className="text-sm text-muted-foreground">{t("passwordChange.changedBody")}</p>
            <Button size="sm" variant="ghost" onClick={again}>
              {t("passwordChange.again")}
            </Button>
          </div>
        ) : (
          <form onSubmit={submit} noValidate className="space-y-4">
            <AuthField
              id="password-change-current"
              name="currentPassword"
              label={t("passwordChange.currentLabel")}
              type="password"
              autoComplete="current-password"
              placeholder={t("passwordChange.currentPlaceholder")}
              value={current}
              error={currentError}
              onChange={(event) => {
                setCurrent(event.target.value);
                if (currentError) setCurrentError(undefined);
              }}
            />
            <AuthField
              id="password-change-new"
              name="newPassword"
              label={t("passwordChange.newLabel")}
              type="password"
              autoComplete="new-password"
              placeholder={t("passwordChange.newPlaceholder")}
              value={next}
              error={nextError}
              onChange={(event) => setNext(event.target.value)}
              onBlur={() => setNextError(issueText(passwordIssue(next), t))}
            />
            <AuthField
              id="password-change-confirm"
              name="confirmPassword"
              label={t("passwordChange.confirmLabel")}
              type="password"
              autoComplete="new-password"
              placeholder={t("passwordChange.confirmPlaceholder")}
              value={confirm}
              error={confirmError}
              onChange={(event) => {
                setConfirm(event.target.value);
                if (confirmError) setConfirmError(undefined);
              }}
              onBlur={() => setConfirmError(issueText(confirmationIssue(confirm, next), t))}
            />
            {formError ? <p className="text-sm text-danger">{formError}</p> : null}
            <Button
              type="submit"
              size="sm"
              variant="outline"
              loading={change.isPending}
              disabled={change.isPending}
            >
              {t("passwordChange.submit")}
            </Button>
            <p className="text-sm text-muted-foreground">{t("passwordChange.hint")}</p>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
