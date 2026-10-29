"use client";

import * as React from "react";
import { KeyRound } from "lucide-react";
import { AuthField } from "@/components/auth/auth-field";
import { CopyButton } from "@/components/common/export-buttons";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import type { MfaEnrollment } from "@/lib/api/client";
import {
  useActivateMfa,
  useDisableMfa,
  useEnrollMfa,
  useMfaStatus,
  useReissueRecoveryCodes,
} from "@/lib/hooks/mfa";
import { issueText, type TextIssue } from "@/lib/i18n/issue";
import { useLocale } from "@/lib/i18n/locale-context";
import {
  activateCodeIssue,
  proofCodeIssue,
  proofPasswordIssue,
  recoveryCodesText,
  spacedSecret,
} from "@/lib/mfa";

/**
 * The second door's card (roadmap 36.4).
 *
 * The card is the only screen that can turn the factor on, hand out the printed codes and take
 * the factor off again, so each state says what the next action costs rather than what it does:
 * an unproven enrollment's seed is shown exactly once, an activation answers the ten codes
 * exactly once, and a turn-off revokes them. The sheet stays on screen until the reader
 * acknowledges it, because the answer from the server is the only copy of those codes that will
 * ever exist.
 *
 * A pending enrollment is not recovered after a reload -- the seed cannot be shown again, by
 * design -- so that state offers "start over" rather than a form to prove a seed nobody can see.
 */

type Panel = "activate" | "replace" | "disable";

export function SecurityCard() {
  const { t } = useLocale();
  const status = useMfaStatus();
  const enroll = useEnrollMfa();
  const activate = useActivateMfa();
  const reissue = useReissueRecoveryCodes();
  const disable = useDisableMfa();

  const [panel, setPanel] = React.useState<Panel | null>(null);
  const [enrollment, setEnrollment] = React.useState<MfaEnrollment | null>(null);
  const [sheet, setSheet] = React.useState<string[] | null>(null);
  const [password, setPassword] = React.useState("");
  const [code, setCode] = React.useState("");
  const [passwordError, setPasswordError] = React.useState<string | undefined>();
  const [codeError, setCodeError] = React.useState<string | undefined>();

  const enabled = status.data?.enabled ?? false;
  const pending = status.data?.pending ?? false;
  const remaining = status.data?.recoveryCodesRemaining ?? 0;

  const resetForm = () => {
    setPassword("");
    setCode("");
    setPasswordError(undefined);
    setCodeError(undefined);
  };

  const closePanels = () => {
    setPanel(null);
    setEnrollment(null);
    resetForm();
  };

  const openPanel = (next: Panel) => {
    setPanel(next);
    setEnrollment(null);
    setSheet(null);
    resetForm();
  };

  const startEnrollment = () => {
    enroll.mutate(undefined, {
      onSuccess: (data) => {
        setPanel("activate");
        setEnrollment(data);
        setSheet(null);
        resetForm();
      },
    });
  };

  const check = (codeCheck: (value: string) => TextIssue | undefined): boolean => {
    const passwordIssue = proofPasswordIssue(password);
    const typedCodeIssue = codeCheck(code);
    setPasswordError(issueText(passwordIssue, t));
    setCodeError(issueText(typedCodeIssue, t));
    return !passwordIssue && !typedCodeIssue;
  };

  const activateNow = () => {
    if (!check(activateCodeIssue) || activate.isPending) return;
    activate.mutate(
      { password, code: code.trim() },
      {
        onSuccess: (data) => {
          setSheet(data.recoveryCodes);
          closePanels();
        },
      },
    );
  };

  const replaceNow = () => {
    if (!check(proofCodeIssue) || reissue.isPending) return;
    reissue.mutate(
      { password, code: code.trim() },
      {
        onSuccess: (data) => {
          setSheet(data.recoveryCodes);
          closePanels();
        },
      },
    );
  };

  const disableNow = () => {
    if (!check(proofCodeIssue) || disable.isPending) return;
    disable.mutate(
      { password, code: code.trim() },
      {
        onSuccess: () => {
          setSheet(null);
          closePanels();
        },
      },
    );
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <CardTitle className="flex items-center gap-2 text-base">
            <KeyRound className="size-4 text-muted-foreground" aria-hidden />
            {t("security.title")}
          </CardTitle>
          {!status.isPending && !status.isError ? (
            <Badge variant={enabled ? "success" : pending ? "warning" : "outline"}>
              {enabled ? t("security.on") : pending ? t("security.pending") : t("security.off")}
            </Badge>
          ) : null}
        </div>
        <CardDescription>{t("security.description")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {status.isPending ? (
          <p className="text-sm text-muted-foreground">{t("security.loading")}</p>
        ) : status.isError ? (
          <p className="text-sm text-danger">{t("security.loadFailed")}</p>
        ) : (
          <>
            <p className="text-sm text-muted-foreground">
              {enabled
                ? t("security.onDescription")
                : pending
                  ? t("security.pendingDescription")
                  : t("security.offDescription")}
            </p>

            {enabled ? (
              <p className="text-sm text-muted-foreground">
                {remaining > 0
                  ? t("security.remaining", { count: remaining })
                  : t("security.remainingNone")}
              </p>
            ) : null}

            {/* The one copy of the printed codes that will ever exist. */}
            {sheet ? (
              <div className="space-y-3 rounded-lg border border-border bg-muted/40 p-4">
                <p className="text-sm font-medium">{t("security.codesTitle")}</p>
                <p className="text-sm text-muted-foreground">{t("security.codesHint")}</p>
                <pre className="overflow-x-auto rounded-md border border-border bg-background p-3 font-mono text-xs leading-6">
                  {recoveryCodesText(sheet)}
                </pre>
                <div className="flex flex-wrap items-center gap-2">
                  <CopyButton
                    text={recoveryCodesText(sheet)}
                    label={t("security.copyAll")}
                  />
                  <Button size="sm" variant="ghost" onClick={() => setSheet(null)}>
                    {t("security.codesDone")}
                  </Button>
                </div>
              </div>
            ) : null}

            {/* The seed and the proof, in one panel: the seed is useless without the code and
                the code cannot be checked against a seed the reader has not been shown. */}
            {panel === "activate" && enrollment ? (
              <div className="space-y-4 rounded-lg border border-border p-4">
                <p className="text-sm text-muted-foreground">{t("security.enrollHint")}</p>

                <div className="space-y-2">
                  <Label htmlFor="mfa-secret">{t("security.secretLabel")}</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      id="mfa-secret"
                      value={spacedSecret(enrollment.secret)}
                      readOnly
                      spellCheck={false}
                      className="font-mono text-xs"
                      onFocus={(event) => event.currentTarget.select()}
                    />
                    <CopyButton text={enrollment.secret} label={t("security.copySecret")} />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="mfa-uri">{t("security.uriLabel")}</Label>
                  <div className="flex items-center gap-2">
                    <Input
                      id="mfa-uri"
                      value={enrollment.otpauthUri}
                      readOnly
                      spellCheck={false}
                      className="font-mono text-xs"
                      onFocus={(event) => event.currentTarget.select()}
                    />
                    <CopyButton text={enrollment.otpauthUri} label={t("security.copyUri")} />
                  </div>
                </div>

                <Separator />

                <AuthField
                  id="mfa-password"
                  label={t("security.passwordLabel")}
                  type="password"
                  autoComplete="current-password"
                  placeholder={t("security.passwordPlaceholder")}
                  value={password}
                  error={passwordError}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <AuthField
                  id="mfa-code"
                  label={t("security.codeLabel")}
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  autoComplete="one-time-code"
                  placeholder={t("security.codePlaceholder")}
                  value={code}
                  error={codeError}
                  onChange={(event) => setCode(event.target.value)}
                />

                <div className="flex flex-wrap gap-2">
                  <Button size="sm" loading={activate.isPending} disabled={activate.isPending} onClick={activateNow}>
                    {t("security.activate")}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={closePanels}>
                    {t("security.cancel")}
                  </Button>
                </div>
              </div>
            ) : null}

            {/* A reprint and a turn-off share the same proof: the password proves the reader,
                the code proves the phone is still in hand. */}
            {panel === "replace" || panel === "disable" ? (
              <div className="space-y-4 rounded-lg border border-border p-4">
                <p className="text-sm text-muted-foreground">
                  {panel === "replace" ? t("security.replaceHint") : t("security.disableHint")}
                </p>

                <AuthField
                  id="mfa-proof-password"
                  label={t("security.passwordLabel")}
                  type="password"
                  autoComplete="current-password"
                  placeholder={t("security.passwordPlaceholder")}
                  value={password}
                  error={passwordError}
                  onChange={(event) => setPassword(event.target.value)}
                />
                <AuthField
                  id="mfa-proof-code"
                  label={t("security.proofCodeLabel")}
                  type="text"
                  maxLength={64}
                  autoComplete="one-time-code"
                  placeholder={t("security.proofCodePlaceholder")}
                  value={code}
                  error={codeError}
                  onChange={(event) => setCode(event.target.value)}
                />

                <div className="flex flex-wrap gap-2">
                  <Button
                    size="sm"
                    variant={panel === "disable" ? "danger" : "secondary"}
                    loading={panel === "replace" ? reissue.isPending : disable.isPending}
                    disabled={panel === "replace" ? reissue.isPending : disable.isPending}
                    onClick={panel === "replace" ? replaceNow : disableNow}
                  >
                    {panel === "replace" ? t("security.replace") : t("security.disable")}
                  </Button>
                  <Button size="sm" variant="ghost" onClick={closePanels}>
                    {t("security.cancel")}
                  </Button>
                </div>
              </div>
            ) : null}

            {enabled ? (
              <div className="flex flex-wrap gap-2">
                <Button size="sm" variant="outline" onClick={() => openPanel("replace")}>
                  {t("security.replace")}
                </Button>
                <Button size="sm" variant="danger" onClick={() => openPanel("disable")}>
                  {t("security.disable")}
                </Button>
              </div>
            ) : (
              <Button size="sm" variant="outline" loading={enroll.isPending} disabled={enroll.isPending} onClick={startEnrollment}>
                {pending ? t("security.startOver") : t("security.start")}
              </Button>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
