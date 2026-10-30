import { sectionMetadata } from "@/lib/i18n/metadata";
import { ConfirmEmailChangeForm } from "@/components/auth/confirm-email-form";

export const generateMetadata = sectionMetadata("auth.pageTitles.confirmEmail");

export default function ConfirmEmailPage() {
  return <ConfirmEmailChangeForm />;
}
