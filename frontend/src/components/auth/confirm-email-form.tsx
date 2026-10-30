"use client";

import * as React from "react";
import Link from "next/link";
import { toast } from "sonner";
import { AuthField } from "@/components/auth/auth-field";
import { Button } from "@/components/ui/button";
import { recoveryErrorMessage, tokenIssue } from "@/lib/auth-recovery";
import { emailChangeOutcome, emailChangeTokenFrom } from "@/lib/email-change";
import { useConfirmEmailChange } from "@/lib/hooks/auth";
import { issueText } from "@/lib/i18n/issue";
import { useLocale } from "@/lib/i18n/locale-context";

/**
 * The landing for the letter 26.1 mails.
 *
 * Until this screen existed the letter's link was a 404: the backend mailed
 * `<app.web.base-url>/confirm-email?token=…` and no route answered it. The page is public
 * on purpose — the token is the proof, exactly as on the reset route — so the mailbox
 * that received the letter can answer it without the account's session.
 *
 * The link is answered once per mount. A second answer would be a second POST for a token
 * the first one spent, and the API would rightly call that invalid; the guard is a ref
 * because React may mount the effect twice in development.
 */
export function ConfirmEmailChangeForm() {
  const confirm = useConfirmEmailChange();
  const { t } = useLocale();
  const [linkToken, setLinkToken] = React.useState<string | null>(null);
  const [typedToken, setTypedToken] = React.useState("");
  const [checked, setChecked] = React.useState(false);
  const [outcome, setOutcome] = React.useState<"moved" | "invalid" | "registered" | null>(null);
  const [tokenError, setTokenError] = React.useState<string | undefined>();
  const fired = React.useRef(false);

  const fail = React.useCallback((err: unknown) => {
    const refusal = emailChangeOutcome(err);
    if (refusal) setOutcome(refusal);
    else toast.error(recoveryErrorMessage(err));
  }, []);

  const send = React.useCallback(
    (token: string) => {
      confirm.mutate({ token }, { onSuccess: () => setOutcome("moved"), onError: fail });
    },
    [confirm, fail],
  );

  React.useEffect(() => {
    const token = emailChangeTokenFrom(window.location.search);
    setLinkToken(token);
    setChecked(true);
    if (!token || fired.current) return;
    fired.current = true;
    send(token);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const signIn = (
    <Button asChild variant="ai" size="lg" className="w-full">
      <Link href="/login">{t("recovery.signIn")}</Link>
    </Button>
  );

  if (outcome === "moved") {
    return (
      <div className="space-y-6">
        <header className="space-y-1.5">
          <h2 className="font-serif text-display-sm font-medium">{t("emailChange.movedTitle")}</h2>
          <p className="text-sm text-muted-foreground">{t("emailChange.movedBody")}</p>
        </header>
        {signIn}
      </div>
    );
  }

  if (outcome === "invalid" || outcome === "registered") {
    return (
      <div className="space-y-6">
        <header className="space-y-1.5">
          <h2 className="font-serif text-display-sm font-medium">
            {t(outcome === "invalid" ? "emailChange.invalidTitle" : "emailChange.registeredTitle")}
          </h2>
          <p className="text-sm text-muted-foreground">
            {t(outcome === "invalid" ? "emailChange.invalidBody" : "emailChange.registeredBody")}
          </p>
        </header>
        {signIn}
      </div>
    );
  }

  // Before hydration, while the link is being answered, and after a retryable failure:
  // the page never draws a paste field over a link it is already working on.
  if (!checked || linkToken) {
    const failed = checked && !confirm.isPending;
    return (
      <div className="space-y-6">
        <header className="space-y-1.5">
          <h2 className="font-serif text-display-sm font-medium">{t("emailChange.confirmHeading")}</h2>
          <p className="text-sm text-muted-foreground">
            {t(failed ? "emailChange.retryBody" : "emailChange.answering")}
          </p>
        </header>
        {failed && (
          <Button
            variant="ai"
            size="lg"
            className="w-full"
            loading={confirm.isPending}
            onClick={() => linkToken && send(linkToken)}
          >
            {t("emailChange.retry")}
          </Button>
        )}
      </div>
    );
  }

  const submit = (event: React.FormEvent) => {
    event.preventDefault();
    const issue = issueText(tokenIssue(typedToken), t);
    setTokenError(issue);
    if (issue || confirm.isPending) return;
    send(typedToken.trim());
  };

  return (
    <div className="space-y-6">
      <header className="space-y-1.5">
        <h2 className="font-serif text-display-sm font-medium">{t("emailChange.confirmHeading")}</h2>
        <p className="text-sm text-muted-foreground">{t("emailChange.pasteBody")}</p>
      </header>

      <form onSubmit={submit} noValidate className="space-y-4">
        <AuthField
          id="token"
          name="token"
          label={t("emailChange.tokenLabel")}
          type="text"
          autoComplete="one-time-code"
          spellCheck={false}
          placeholder={t("emailChange.tokenPlaceholder")}
          value={typedToken}
          error={tokenError}
          onChange={(event) => {
            setTypedToken(event.target.value);
            if (tokenError) setTokenError(issueText(tokenIssue(event.target.value), t));
          }}
          onBlur={() => setTokenError(issueText(tokenIssue(typedToken), t))}
        />
        <Button type="submit" variant="ai" size="lg" className="w-full" loading={confirm.isPending}>
          {t("emailChange.confirm")}
        </Button>
      </form>
    </div>
  );
}
