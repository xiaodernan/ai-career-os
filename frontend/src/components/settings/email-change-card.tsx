"use client";

import * as React from "react";
import { AtSign } from "lucide-react";
import { AuthField } from "@/components/auth/auth-field";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { emailIssue } from "@/lib/auth-recovery";
import { addressMoveRefusal } from "@/lib/email-change";
import { useRequestEmailChange } from "@/lib/hooks/account";
import { describe } from "@/lib/hooks/failure";
import { useUser } from "@/lib/hooks/auth";
import { useLocale } from "@/lib/i18n/locale-context";
import { issueText } from "@/lib/i18n/issue";

/**
 * The address this account signs in with (38.2).
 *
 * The API has accepted a move since Epic 26, but no screen ever asked: the only way to
 * change an address was to call the route by hand. The card is written around what the
 * server actually does rather than what a reader might assume. Asking sends *two*
 * letters — the confirmation to the claimed address and a heads-up to the one on the
 * account — and nothing moves until the new mailbox answers. The success panel therefore
 * names both inboxes and the two-hour window; "check your email" would be wrong for one
 * of the two readers, and "your address has changed" would be wrong for both.
 *
 * A refusal is shown under the field that caused it (the wrong password, an address the
 * server will not take), except the limiter's, which belongs to no field. Everything the
 * form cannot attribute keeps the shared describer's sentence.
 */
export function EmailChangeCard() {
  const { t } = useLocale();
  const { data: user } = useUser();
  const request = useRequestEmailChange();

  const [newEmail, setNewEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [emailError, setEmailError] = React.useState<string | undefined>();
  const [passwordError, setPasswordError] = React.useState<string | undefined>();
  const [formError, setFormError] = React.useState<string | undefined>();
  const [sentTo, setSentTo] = React.useState<string | null>(null);

  const current = user?.email ?? "";

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const typedEmail = newEmail.trim();
    const emailText = issueText(emailIssue(typedEmail), t);
    const passwordText = password ? undefined : t("auth.issues.passwordRequired");
    setEmailError(emailText);
    setPasswordError(passwordText);
    setFormError(undefined);
    if (emailText || passwordText || request.isPending) return;
    request.mutate(
      { password, newEmail: typedEmail },
      {
        onSuccess: () => {
          setSentTo(typedEmail);
          setNewEmail("");
          setPassword("");
          setEmailError(undefined);
          setPasswordError(undefined);
        },
        onError: (err) => {
          const field = addressMoveRefusal(err);
          if (field === "password") setPasswordError(describe(err));
          else if (field === "email") setEmailError(describe(err));
          else setFormError(describe(err));
        },
      },
    );
  };

  const again = () => {
    setSentTo(null);
    setFormError(undefined);
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <AtSign className="size-4 text-muted-foreground" aria-hidden />
          {t("emailMove.title")}
        </CardTitle>
        <CardDescription>{t("emailMove.description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {current ? (
          <p className="text-sm text-muted-foreground">{t("emailMove.current", { email: current })}</p>
        ) : null}

        {sentTo ? (
          <div className="space-y-3 rounded-lg border border-border bg-muted/40 p-4">
            <p className="text-sm font-medium">{t("emailMove.sentTitle")}</p>
            <p className="text-sm text-muted-foreground">
              {t("emailMove.sentBody", { newEmail: sentTo, oldEmail: current })}
            </p>
            <Button size="sm" variant="ghost" onClick={again}>
              {t("emailMove.askAgain")}
            </Button>
          </div>
        ) : (
          <form onSubmit={submit} noValidate className="space-y-4">
            <AuthField
              id="email-move-address"
              name="newEmail"
              label={t("emailMove.newLabel")}
              type="email"
              autoComplete="email"
              spellCheck={false}
              placeholder={t("emailMove.newPlaceholder")}
              value={newEmail}
              error={emailError}
              onChange={(event) => {
                setNewEmail(event.target.value);
                if (emailError) setEmailError(issueText(emailIssue(event.target.value.trim()), t));
              }}
              onBlur={() => setEmailError(issueText(emailIssue(newEmail.trim()), t))}
            />
            <AuthField
              id="email-move-password"
              name="password"
              label={t("emailMove.passwordLabel")}
              type="password"
              autoComplete="current-password"
              placeholder={t("emailMove.passwordPlaceholder")}
              value={password}
              error={passwordError}
              onChange={(event) => setPassword(event.target.value)}
            />
            {formError ? <p className="text-sm text-danger">{formError}</p> : null}
            <Button
              type="submit"
              size="sm"
              variant="outline"
              loading={request.isPending}
              disabled={request.isPending}
            >
              {t("emailMove.send")}
            </Button>
            <p className="text-sm text-muted-foreground">{t("emailMove.hint")}</p>
          </form>
        )}
      </CardContent>
    </Card>
  );
}
