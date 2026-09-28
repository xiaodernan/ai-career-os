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
import { useResetPassword } from "@/lib/hooks/auth";

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
      token: needsToken ? tokenIssue(typedToken) : undefined,
      password: passwordIssue(password),
      confirm: confirmationIssue(confirm, password),
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
          <h2 className="font-serif text-display-sm font-medium">Password updated</h2>
          <p className="text-sm text-muted-foreground">
            Every device that was signed in has been signed out. Use the new password to get back
            in.
          </p>
        </header>
        <Button asChild variant="ai" size="lg" className="w-full">
          <Link href="/login">Sign in</Link>
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1.5">
        <h2 className="font-serif text-display-sm font-medium">Set a new password</h2>
        <p className="text-sm text-muted-foreground">
          {needsToken
            ? "Paste the token from your email, then pick a password. Signing in everywhere else stops as soon as you save."
            : "Signing in everywhere else stops as soon as you save."}
        </p>
      </header>

      <form onSubmit={submit} noValidate className="space-y-4">
        {needsToken && (
          <AuthField
            id="token"
            name="token"
            label="Reset token"
            type="text"
            autoComplete="one-time-code"
            spellCheck={false}
            placeholder="the token from the email"
            value={typedToken}
            error={errors.token}
            onChange={(event) => {
              setTypedToken(event.target.value);
              if (errors.token) setErrors((prev) => ({ ...prev, token: tokenIssue(event.target.value) }));
            }}
            onBlur={() => setErrors((prev) => ({ ...prev, token: tokenIssue(typedToken) }))}
          />
        )}
        <AuthField
          id="password"
          name="password"
          label="New password"
          type="password"
          autoComplete="new-password"
          placeholder="••••••••••"
          value={password}
          error={errors.password}
          onChange={(event) => {
            setPassword(event.target.value);
            if (errors.password) setErrors((prev) => ({ ...prev, password: passwordIssue(event.target.value) }));
          }}
          onBlur={() => setErrors((prev) => ({ ...prev, password: passwordIssue(password) }))}
        />
        <AuthField
          id="confirmPassword"
          name="confirmPassword"
          label="Confirm new password"
          type="password"
          autoComplete="new-password"
          placeholder="••••••••••"
          value={confirm}
          error={errors.confirm}
          onChange={(event) => {
            setConfirm(event.target.value);
            if (errors.confirm) {
              setErrors((prev) => ({ ...prev, confirm: confirmationIssue(event.target.value, password) }));
            }
          }}
          onBlur={() => setErrors((prev) => ({ ...prev, confirm: confirmationIssue(confirm, password) }))}
        />
        <Button type="submit" variant="ai" size="lg" className="w-full" loading={reset.isPending}>
          Save new password
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Token expired?{" "}
        <Link
          href="/forgot-password"
          className="font-medium text-primary underline-offset-4 hover:underline"
        >
          Request another
        </Link>
      </p>
    </div>
  );
}
