import { sectionMetadata } from "@/lib/i18n/metadata";
import { ForgotPasswordForm } from "@/components/auth/forgot-password-form";

export const generateMetadata = sectionMetadata("auth.pageTitles.forgotPassword");

export default function ForgotPasswordPage() {
  return <ForgotPasswordForm />;
}
