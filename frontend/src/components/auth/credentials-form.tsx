"use client";

import * as React from "react";
import { useLocale } from "@/lib/i18n/locale-context";
import Link from "next/link";
import { toast } from "sonner";
import { AuthField } from "@/components/auth/auth-field";
import { Button } from "@/components/ui/button";
import {
  authFormErrorMessage,
  confirmationIssue,
  displayNameIssue,
  emailIssue,
  issueText,
  passwordIssue,
  type Translate,
} from "@/lib/auth-recovery";
import { useLogin, useRegister } from "@/lib/hooks/auth";

export interface FieldConfig {
  name: "displayName" | "email" | "password" | "confirmPassword";
  labelKey: string;
  type: string;
  autoComplete: string;
  /** A placeholder that is the same in every language -- an address, bullets. */
  placeholder?: string;
  /** A placeholder that is a word, so it follows the reader's language. */
  placeholderKey?: string;
  validate?: (v: string, all: Record<string, string>, t: Translate) => string | undefined;
}

const baseFields: FieldConfig[] = [
  {
    name: "email",
    labelKey: "auth.email",
    type: "email",
    autoComplete: "email",
    placeholder: "you@example.com",
    validate: (v, _all, t) => issueText(emailIssue(v), t),
  },
  {
    name: "password",
    labelKey: "auth.password",
    type: "password",
    autoComplete: "current-password",
    placeholder: "••••••••••",
    validate: (v, _all, t) => issueText(passwordIssue(v), t),
  },
];

const registerFields: FieldConfig[] = [
  {
    name: "displayName",
    labelKey: "auth.fullName",
    type: "text",
    autoComplete: "name",
    placeholderKey: "auth.fullNamePlaceholder",
    validate: (v, _all, t) => issueText(displayNameIssue(v), t),
  },
  ...baseFields.map((f) =>
    f.name === "password" ? { ...f, autoComplete: "new-password" } : f
  ),
  {
    name: "confirmPassword",
    labelKey: "auth.confirmPassword",
    type: "password",
    autoComplete: "new-password",
    placeholder: "••••••••••",
    validate: (v, all, t) => issueText(confirmationIssue(v, all.password ?? ""), t),
  },
];

export function CredentialsForm({ mode, notice }: { mode: "login" | "register"; notice?: string }) {
  const { t } = useLocale();
  const isLogin = mode === "login";
  const fields = isLogin ? baseFields : registerFields;
  const login = useLogin();
  const register = useRegister();
  const mutation = isLogin ? login : register;

  const [values, setValues] = React.useState<Record<string, string>>({});
  const [errors, setErrors] = React.useState<Record<string, string | undefined>>({});
  const [touched, setTouched] = React.useState<Record<string, boolean>>({});

  const onSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const nextErrors: Record<string, string | undefined> = {};
    for (const f of fields) nextErrors[f.name] = f.validate?.(values[f.name] ?? "", values, t);
    setErrors(nextErrors);
    setTouched(Object.fromEntries(fields.map((f) => [f.name, true])));
    if (Object.values(nextErrors).some(Boolean)) return;

    if (mutation.isPending) return;
    const handlers = {
      onSuccess: () =>
        toast.success(isLogin ? t("auth.welcomeBack") : t("auth.accountCreated")),
        onError: (err: unknown) => toast.error(authFormErrorMessage(err)),
    };
    if (isLogin) {
      login.mutate({ email: values.email, password: values.password }, handlers);
    } else {
      register.mutate(
        { displayName: values.displayName, email: values.email, password: values.password },
        handlers
      );
    }
  };

  return (
    <div className="space-y-6">
      {notice ? (
        <div
          role="alert"
          className="rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
        >
          {notice}
        </div>
      ) : null}
      <header className="space-y-1.5">
        <h2 className="font-serif text-display-sm font-medium">
          {isLogin ? t("auth.signInToWorkspace") : t("auth.createYourAccount")}
        </h2>
        <p className="text-sm text-muted-foreground">
          {isLogin ? t("auth.loginBlurb") : t("auth.registerBlurb")}
        </p>
      </header>

      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {fields.map((f) => {
          return (
            <AuthField
              key={f.name}
              id={f.name}
              name={f.name}
              label={t(f.labelKey)}
              type={f.type}
              autoComplete={f.autoComplete}
              placeholder={f.placeholderKey ? t(f.placeholderKey) : f.placeholder}
              value={values[f.name] ?? ""}
              error={touched[f.name] ? errors[f.name] : undefined}
              onChange={(e) => {
                const v = e.target.value;
                setValues((prev) => ({ ...prev, [f.name]: v }));
                if (touched[f.name]) {
                  setErrors((prev) => ({ ...prev, [f.name]: f.validate?.(v, { ...values, [f.name]: v }, t) }));
                }
              }}
              onBlur={() => {
                setTouched((prev) => ({ ...prev, [f.name]: true }));
                setErrors((prev) => ({ ...prev, [f.name]: f.validate?.(values[f.name] ?? "", values, t) }));
              }}
            />
          );
        })}

        <Button type="submit" variant="ai" size="lg" className="w-full" loading={mutation.isPending}>
          {isLogin ? t("auth.signIn") : t("auth.createAccount")}
        </Button>
      </form>

      {isLogin && (
        <p className="text-center text-sm">
          <Link
            href="/forgot-password"
            className="font-medium text-primary underline-offset-4 hover:underline"
          >
            {t("auth.forgotPassword")}
          </Link>
        </p>
      )}

      <p className="text-center text-sm text-muted-foreground">
        {isLogin ? (
          <>
            {t("auth.noAccount")}{" "}
            <Link href="/register" className="font-medium text-primary underline-offset-4 hover:underline">
              {t("auth.createOne")}
            </Link>
          </>
        ) : (
          <>
            {t("auth.alreadyRegistered")}{" "}
            <Link href="/login" className="font-medium text-primary underline-offset-4 hover:underline">
              {t("auth.signIn")}
            </Link>
          </>
        )}
      </p>
    </div>
  );
}
