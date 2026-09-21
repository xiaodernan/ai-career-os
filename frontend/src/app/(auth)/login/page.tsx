import type { Metadata } from "next";
import { CredentialsForm } from "@/components/auth/credentials-form";

export const metadata: Metadata = { title: "Sign in" };

export default function LoginPage() {
  return <CredentialsForm mode="login" />;
}
