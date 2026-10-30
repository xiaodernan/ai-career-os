"use client";

import * as React from "react";
import { UserX } from "lucide-react";
import { AuthField } from "@/components/auth/auth-field";
import { ConfirmDialog } from "@/components/common/confirm-dialog";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { emailIssue } from "@/lib/auth-recovery";
import { eraseRefusal } from "@/lib/erase-account";
import { useEraseAccount } from "@/lib/hooks/account";
import { useUser } from "@/lib/hooks/auth";
import { describe } from "@/lib/hooks/failure";
import { useLocale } from "@/lib/i18n/locale-context";
import { issueText } from "@/lib/i18n/issue";

/**
 * The door out (38.5).
 *
 * The API has erased an account since 24.2 — files behind `documents.file_key` first, then
 * the `users` row every other row cascades from — but no screen ever asked, so the only way
 * out was to call the route by hand. The card is written around what the server does, not
 * around what a destructive button usually says: it names what leaves (every row that names
 * the account, and the stored files behind its documents) and what does not (backups outside
 * the live system, until their retention window passes; letters already delivered).
 *
 * The route re-authenticates twice, so the card takes both proofs and posts nothing until a
 * confirmation restates them: the address as typed, and that the password is checked first.
 * A wrong password and an address that is not this account's come back as two named codes
 * and touch nothing; each sentence goes under its field. Success is not a panel here — the
 * hook drops the token pair and the cache and leaves through a full navigation, because the
 * account whose rows just left cannot refresh, and a page that stayed would only be a 401.
 */
export function EraseAccountCard() {
  const { t } = useLocale();
  const { data: user } = useUser();
  const erase = useEraseAccount();

  const [password, setPassword] = React.useState("");
  const [confirmEmail, setConfirmEmail] = React.useState("");
  const [passwordError, setPasswordError] = React.useState<string | undefined>();
  const [emailError, setEmailError] = React.useState<string | undefined>();
  const [formError, setFormError] = React.useState<string | undefined>();
  const [confirming, setConfirming] = React.useState(false);

  const current = user?.email ?? "";
  const typed = confirmEmail.trim();

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const passwordText = password ? undefined : t("auth.issues.passwordRequired");
    const emailText = issueText(emailIssue(typed), t);
    setPasswordError(passwordText);
    setEmailError(emailText);
    setFormError(undefined);
    if (passwordText || emailText || erase.isPending) return;
    setConfirming(true);
  };

  const eraseConfirmed = () => {
    erase.mutate(
      { password, confirmEmail: typed },
      {
        onError: (err) => {
          setConfirming(false);
          const field = eraseRefusal(err);
          if (field === "password") setPasswordError(describe(err));
          else if (field === "email") setEmailError(describe(err));
          else setFormError(describe(err));
        },
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <UserX className="size-4 text-muted-foreground" aria-hidden />
          {t("eraseAccount.title")}
        </CardTitle>
        <CardDescription>{t("eraseAccount.description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {current ? (
          <p className="text-sm text-muted-foreground">{t("eraseAccount.current", { email: current })}</p>
        ) : null}

        <div className="grid gap-3 sm:grid-cols-2">
          <div className="rounded-lg border border-border p-3">
            <p className="text-sm font-medium">{t("eraseAccount.leavesTitle")}</p>
            <p className="text-sm text-muted-foreground">{t("eraseAccount.leavesBody")}</p>
          </div>
          <div className="rounded-lg border border-border p-3">
            <p className="text-sm font-medium">{t("eraseAccount.staysTitle")}</p>
            <p className="text-sm text-muted-foreground">{t("eraseAccount.staysBody")}</p>
          </div>
        </div>

        <Separator />

        <form onSubmit={submit} noValidate className="space-y-4">
          <AuthField
            id="erase-password"
            name="password"
            label={t("eraseAccount.passwordLabel")}
            type="password"
            autoComplete="current-password"
            placeholder={t("eraseAccount.passwordPlaceholder")}
            value={password}
            error={passwordError}
            onChange={(event) => {
              setPassword(event.target.value);
              if (passwordError) setPasswordError(undefined);
            }}
          />
          <AuthField
            id="erase-email"
            name="confirmEmail"
            label={t("eraseAccount.confirmLabel")}
            type="email"
            autoComplete="email"
            spellCheck={false}
            placeholder={current ? t("eraseAccount.confirmPlaceholder", { email: current }) : undefined}
            value={confirmEmail}
            error={emailError}
            onChange={(event) => {
              setConfirmEmail(event.target.value);
              if (emailError) setEmailError(issueText(emailIssue(event.target.value.trim()), t));
            }}
            onBlur={() => setEmailError(issueText(emailIssue(typed), t))}
          />
          <p className="text-sm text-muted-foreground">{t("eraseAccount.hint")}</p>
          {formError ? <p className="text-sm text-danger">{formError}</p> : null}
          <Button type="submit" variant="danger" loading={erase.isPending} disabled={erase.isPending}>
            {t("eraseAccount.submit")}
          </Button>
        </form>
      </CardContent>

      <ConfirmDialog
        open={confirming}
        onOpenChange={(open) => {
          if (!open && !erase.isPending) setConfirming(false);
        }}
        title={t("eraseAccount.dialogTitle")}
        description={t("eraseAccount.dialogDescription", { email: typed })}
        confirmLabel={t("eraseAccount.dialogConfirm")}
        destructive
        loading={erase.isPending}
        onConfirm={eraseConfirmed}
      />
    </Card>
  );
}
