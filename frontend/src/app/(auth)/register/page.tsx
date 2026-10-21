import { sectionMetadata } from "@/lib/i18n/metadata";
import { CredentialsForm } from "@/components/auth/credentials-form";

export const generateMetadata = sectionMetadata("auth.pageTitles.signUp");

export default function RegisterPage() {
  return <CredentialsForm mode="register" />;
}
