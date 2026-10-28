"use client";

import * as React from "react";
import Link from "next/link";
import { toast } from "sonner";
import { AuthField } from "@/components/auth/auth-field";
import { Button } from "@/components/ui/button";
import {
  confirmationIssue,
  passwordIssue,
  recoveryErrorMessage,
  resetTokenFrom,
  tokenIssue,
} from "@/lib/auth-recovery";
import { issueText } from "@/lib/i18n/issue";
import { useResetPassword } from "@/lib/hooks/auth";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * Spend a reset token and set a new password.
 *
 * Two ways in, because the mail and the link can part company: a clicked link carries the token
 * in the URL, and a truncated one -- or a token copied straight out of the mail -- is typed into
 * the field below. The URL is unreadable to the server render, so it is picked up in an effect;
 * that is also why the token field waits for hydration instead of claiming the link is broken.
 */
export function ResetPasswordForm() {
  const reset = useResetPassword();
  const { t } = useLocale();
  const [linkToken, setLinkToken] = React.useState<string | null>(null);
  const [typedToken, setTypedToken] = React.useState("");
  const [checked, setChecked] = React.useState(false);
  const [password, setPassword] = React.useState("");
  const [confirm, setConfirm] = React.useState("");
  const [errors, setErrors] = React.useState<{
    token?: string;
    password?: string;
    confirm?: string;
  }>({});
  const [done, setDone] = React.useState(false);

  React.useEffect(() => {
    setLinkToken(resetTokenFrom(window.location.search));
    setChecked(true);
  }, []);

  // A token in the link is the same token the mail prints, so whichever arrived first wins.
  const token = linkToken ?? typedToken.trim();
  const needsToken = checked && !linkToken;

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const next = {
      token: needsToken ? issueText(tokenIssue(typedToken), t) : undefined,
      password: issueText(passwordIssue(password), t),
      confirm: issueText(confirmationIssue(confirm, password), t),
    };
    setErrors(next);
    if (next.token || next.password || next.confirm || reset.isPending || !token) return;
    reset.mutate(
      { token, newPassword: password },
      {
        onSuccess: () => setDone(true),
        onError: (err) => toast.error(recoveryErrorMessage(err)),
      },
    );
  };

  if (done) {
    return (
      <div className="space-y-6">
        <header className="space-y-1.5">
          <h2 className="font-serif text-display-sm font-medium">{t("recovery.passwordUpdated")}</h2>
          <p className="text-sm text-muted-foreground">
            {t("recovery.signedOutEverywhere")}
          </p>
        </header>
        <Button asChild variant="ai" size="lg" className="w-full">
          <Link href="/login">{t("recovery.signIn")}</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1.5">
        <h2 className="font-serif text-display-sm font-medium">{t("recovery.setNewPassword")}</h2>
        <p className="text-sm text-muted-foreground">
          {needsToken ? t("recovery.pasteToken") : t("recovery.stopsElsewhere")}
        </p>
      </header>

      <form onSubmit={submit} noValidate className="space-y-4">
        {needsToken && (
          <AuthField
            id="token"
            name="token"
            label={t("recovery.resetToken")}
            type="text"
            autoComplete="one-time-code"
            spellCheck={false}
            placeholder={t("recovery.resetTokenPlaceholder")}
            value={typedToken}
            error={errors.token}
            onChange={(event) => {
              setTypedToken(event.target.value);
              if (errors.token) setErrors((prev) => ({ ...prev, token: issueText(tokenIssue(event.target.value), t) }));
            }}
            onBlur={() => setErrors((prev) => ({ ...prev, token: issueText(tokenIssue(typedToken), t) }))}
          />
        )}
        <AuthField
          id="password"
          name="password"
          label={t("recovery.newPassword")}
          type="password"
          autoComplete="new-password"
          placeholder="••••••••••"
          value={password}
          error={errors.password}
          onChange={(event) => {
            setPassword(event.target.value);
            if (errors.password) setErrors((prev) => ({ ...prev, password: issueText(passwordIssue(event.target.value), t) }));
          }}
          onBlur={() => setErrors((prev) => ({ ...prev, password: issueText(passwordIssue(password), t) }))}
        />
        <AuthField
          id="confirmPassword"
          name="confirmPassword"
          label={t("recovery.confirmNewPassword")}
          type="password"
          autoComplete="new-password"
          placeholder="••••••••••"
          value={confirm}
          error={errors.confirm}
          onChange={(event) => {
            setConfirm(event.target.value);
            if (errors.confirm) {
              setErrors((prev) => ({
                ...prev,
                confirm: issueText(confirmationIssue(event.target.value, password), t),
              }));
            }
          }}
          onBlur={() =>
            setErrors((prev) => ({
              ...prev,
              confirm: issueText(confirmationIssue(confirm, password), t),
            }))
          }
        />
        <Button type="submit" variant="ai" size="lg" className="w-full" loading={reset.isPending}>
          {t("recovery.saveNewPassword")}
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        {t("recovery.tokenExpired")}{" "}
        <Link
          href="/forgot-password"
          className="font-medium text-primary underline-offset-4 hover:underline"
        >
          {t("recovery.requestAnother")}
        </Link>
      </p>
    </div>
  );
}
