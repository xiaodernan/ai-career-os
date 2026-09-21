"use client";

import * as React from "react";
import Link from "next/link";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { ApiError } from "@/lib/api/client";
import { useLogin, useRegister } from "@/lib/hooks/auth";

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

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
    validate: (v) => (!v ? "Email is required" : !EMAIL_RE.test(v) ? "Enter a valid email address" : undefined),
  },
  {
    name: "password",
    label: "Password",
    type: "password",
    autoComplete: "current-password",
    placeholder: "••••••••••",
    validate: (v) => (!v ? "Password is required" : v.length < 8 ? "At least 8 characters" : undefined),
  },
];

const registerFields: FieldConfig[] = [
  {
    name: "displayName",
    label: "Full name",
    type: "text",
    autoComplete: "name",
    placeholder: "Ada Zhang",
    validate: (v) => (!v.trim() ? "Name is required" : undefined),
  },
  ...baseFields.map((f) =>
    f.name === "password"
      ? {
          ...f,
          autoComplete: "new-password",
          validate: (v: string) =>
            !v ? "Password is required" : v.length < 8 ? "Use at least 8 characters" : undefined,
        }
      : f
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

function describeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.code === "AUTH_INVALID_CREDENTIALS" || err.status === 401)
      return "Incorrect email or password.";
    return err.message;
  }
  if (err instanceof TypeError) return "Cannot reach the API — is the backend running on :8080?";
  return "Something went wrong. Please try again.";
}

export function CredentialsForm({ mode }: { mode: "login" | "register" }) {
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
        toast.success(isLogin ? "Welcome back." : "Account created — welcome to Career OS."),
      onError: (err: unknown) => toast.error(describeError(err)),
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
      <header className="space-y-1.5">
        <h2 className="font-serif text-display-sm font-medium">
          {isLogin ? "Sign in to your workspace" : "Create your account"}
        </h2>
        <p className="text-sm text-muted-foreground">
          {isLogin
            ? "Pick up where the agents left off."
            : "Your resume becomes a knowledge base in minutes."}
        </p>
      </header>

      <form onSubmit={onSubmit} noValidate className="space-y-4">
        {fields.map((f) => {
          const showError = touched[f.name] && errors[f.name];
          return (
            <div key={f.name} className="space-y-1.5">
              <Label htmlFor={f.name}>{f.label}</Label>
              <Input
                id={f.name}
                name={f.name}
                type={f.type}
                autoComplete={f.autoComplete}
                placeholder={f.placeholder}
                value={values[f.name] ?? ""}
                aria-invalid={showError ? true : undefined}
                aria-describedby={showError ? `${f.name}-error` : undefined}
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
              {showError && (
                <p id={`${f.name}-error`} className="text-xs text-destructive">
                  {errors[f.name]}
                </p>
              )}
            </div>
          );
        })}

        <Button type="submit" variant="ai" size="lg" className="w-full" loading={mutation.isPending}>
          {isLogin ? "Sign in" : "Create account"}
        </Button>
      </form>

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
