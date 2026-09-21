import type { Metadata } from "next";
import { CredentialsForm } from "@/components/auth/credentials-form";

export const metadata: Metadata = { title: "Create account" };

export default function RegisterPage() {
  return <CredentialsForm mode="register" />;
}
