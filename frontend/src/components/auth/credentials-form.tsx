"use client";

import * as React from "react";
import { useLocale } from "@/lib/i18n/locale-context";
import Link from "next/link";
import { toast } from "sonner";
import { AuthField } from "@/components/auth/auth-field";
import { Button } from "@/components/ui/button";
import { authFormErrorMessage, displayNameIssue, emailIssue, passwordIssue } from "@/lib/auth-recovery";
import { useLogin, useRegister } from "@/lib/hooks/auth";

export interface FieldConfig {
  name: "displayName" | "email" | "password" | "confirmPassword";
  label: string;
  type: string;
  autoComplete: string;
  placeholder: string;
  validate?: (v: string, all: Record<string, string>) => string | undefined;
}

const baseFields: FieldConfig[] = [
  {
    name: "email",
    label: "Email",
    type: "email",
    autoComplete: "email",
    placeholder: "you@example.com",
    validate: emailIssue,
  },
  {
    name: "password",
    label: "Password",
    type: "password",
    autoComplete: "current-password",
    placeholder: "••••••••••",
    validate: passwordIssue,
  },
];

const registerFields: FieldConfig[] = [
  {
    name: "displayName",
    label: "Full name",
    type: "text",
    autoComplete: "name",
    placeholder: "Ada Zhang",
    validate: displayNameIssue,
  },
  ...baseFields.map((f) =>
    f.name === "password" ? { ...f, autoComplete: "new-password" } : f
  ),
  {
    name: "confirmPassword",
    label: "Confirm password",
    type: "password",
    autoComplete: "new-password",
    placeholder: "••••••••••",
    validate: (v, all) => (v !== all.password ? "Passwords do not match" : undefined),
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
    for (const f of fields) nextErrors[f.name] = f.validate?.(values[f.name] ?? "", values);
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
          {isLogin
            ? "Pick up where the agents left off."
            : "Your resume becomes a knowledge base in minutes."}
        </p>
      </header>

      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {fields.map((f) => {
          return (
            <AuthField
              key={f.name}
              id={f.name}
              name={f.name}
              label={f.label}
              type={f.type}
              autoComplete={f.autoComplete}
              placeholder={f.placeholder}
              value={values[f.name] ?? ""}
              error={touched[f.name] ? errors[f.name] : undefined}
              onChange={(e) => {
                const v = e.target.value;
                setValues((prev) => ({ ...prev, [f.name]: v }));
                if (touched[f.name]) {
                  setErrors((prev) => ({ ...prev, [f.name]: f.validate?.(v, { ...values, [f.name]: v }) }));
                }
              }}
              onBlur={() => {
                setTouched((prev) => ({ ...prev, [f.name]: true }));
                setErrors((prev) => ({ ...prev, [f.name]: f.validate?.(values[f.name] ?? "", values) }));
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
            No account yet?{" "}
            <Link href="/register" className="font-medium text-primary underline-offset-4 hover:underline">
              Create one
            </Link>
          </>
        ) : (
          <>
            Already registered?{" "}
            <Link href="/login" className="font-medium text-primary underline-offset-4 hover:underline">
              Sign in
            </Link>
          </>
        )}
      </p>
    </div>
  );
}
