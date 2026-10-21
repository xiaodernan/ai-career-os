import { sectionMetadata } from "@/lib/i18n/metadata";
import { ResetPasswordForm } from "@/components/auth/reset-password-form";

export const generateMetadata = sectionMetadata("auth.pageTitles.resetPassword");

export default function ResetPasswordPage() {
  return <ResetPasswordForm />;
}
