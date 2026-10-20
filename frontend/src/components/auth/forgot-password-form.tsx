"use client";

import * as React from "react";
import Link from "next/link";
import { toast } from "sonner";
import { AuthField } from "@/components/auth/auth-field";
import { Button } from "@/components/ui/button";
import { emailIssue, recoveryErrorMessage } from "@/lib/auth-recovery";
import { useForgotPassword } from "@/lib/hooks/auth";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * Ask for a reset token.
 *
 * The endpoint answers 200 for an address with no account, so this screen can only say "if
 * that address has an account" — inventing a stronger confirmation here would undo the
 * enumeration-safety the API deliberately bought.
 */
export function ForgotPasswordForm() {
  const forgot = useForgotPassword();
  const { t } = useLocale();
  const [email, setEmail] = React.useState("");
  const [error, setError] = React.useState<string | undefined>();
  const [accepted, setAccepted] = React.useState<string | null>(null);

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const issue = emailIssue(email);
    setError(issue);
    if (issue || forgot.isPending) return;
    const address = email.trim();
    forgot.mutate(
      { email: address },
      {
        onSuccess: () => setAccepted(address),
        onError: (err) => toast.error(recoveryErrorMessage(err)),
      },
    );
  };

  if (accepted) {
    return (
      <div className="space-y-6">
        <header className="space-y-1.5">
          <h2 className="font-serif text-display-sm font-medium">{t("recovery.checkEmail")}</h2>
          <p className="text-sm text-muted-foreground">
            {t("recovery.checkEmailBody", { email: accepted })}
          </p>
        </header>
        <div className="space-y-2">
          <Button asChild variant="outline" size="lg" className="w-full">
            <Link href="/reset-password">{t("recovery.alreadyHaveToken")}</Link>
          </Button>
          <Button variant="ghost" size="lg" className="w-full" onClick={() => setAccepted(null)}>
            {t("recovery.differentAddress")}
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1.5">
        <h2 className="font-serif text-display-sm font-medium">{t("recovery.resetHeading")}</h2>
        <p className="text-sm text-muted-foreground">
          {t("recovery.resetBody")}
        </p>
      </header>

      <form onSubmit={submit} noValidate className="space-y-4">
        <AuthField
          id="email"
          name="email"
          label={t("recovery.email")}
          type="email"
          autoComplete="email"
          placeholder={t("recovery.emailPlaceholder")}
          value={email}
          error={error}
          onChange={(event) => {
            setEmail(event.target.value);
            if (error) setError(emailIssue(event.target.value));
          }}
          onBlur={() => setError(emailIssue(email))}
        />
        <Button type="submit" variant="ai" size="lg" className="w-full" loading={forgot.isPending}>
          {t("recovery.sendToken")}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        {t("recovery.remembered")}{" "}
        <Link href="/login" className="font-medium text-primary underline-offset-4 hover:underline">
          {t("recovery.signIn")}
        </Link>
      </p>
    </div>
  );
}
