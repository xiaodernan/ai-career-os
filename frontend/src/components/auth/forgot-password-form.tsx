"use client";

import * as React from "react";
import Link from "next/link";
import { toast } from "sonner";
import { AuthField } from "@/components/auth/auth-field";
import { Button } from "@/components/ui/button";
import { emailIssue, recoveryErrorMessage } from "@/lib/auth-recovery";
import { useForgotPassword } from "@/lib/hooks/auth";

/**
 * Ask for a reset token.
 *
 * The endpoint answers 200 for an address with no account, so this screen can only say "if
 * that address has an account" — inventing a stronger confirmation here would undo the
 * enumeration-safety the API deliberately bought.
 */
export function ForgotPasswordForm() {
  const forgot = useForgotPassword();
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
          <h2 className="font-serif text-display-sm font-medium">Check your email</h2>
          <p className="text-sm text-muted-foreground">
            If {accepted} has an account, a reset token is on its way. The token is good for 30
            minutes.
          </p>
        </header>
        <div className="space-y-2">
          <Button asChild variant="outline" size="lg" className="w-full">
            <Link href="/reset-password">I already have a token</Link>
          </Button>
          <Button variant="ghost" size="lg" className="w-full" onClick={() => setAccepted(null)}>
            Use a different address
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="space-y-1.5">
        <h2 className="font-serif text-display-sm font-medium">Reset your password</h2>
        <p className="text-sm text-muted-foreground">
          Tell us the address on the account and we will send it a reset token.
        </p>
      </header>

      <form onSubmit={submit} noValidate className="space-y-4">
        <AuthField
          id="email"
          name="email"
          label="Email"
          type="email"
          autoComplete="email"
          placeholder="you@example.com"
          value={email}
          error={error}
          onChange={(event) => {
            setEmail(event.target.value);
            if (error) setError(emailIssue(event.target.value));
          }}
          onBlur={() => setError(emailIssue(email))}
        />
        <Button type="submit" variant="ai" size="lg" className="w-full" loading={forgot.isPending}>
          Send reset token
        </Button>
      </form>

      <p className="text-center text-sm text-muted-foreground">
        Remembered it?{" "}
        <Link href="/login" className="font-medium text-primary underline-offset-4 hover:underline">
          Sign in
        </Link>
      </p>
    </div>
  );
}
