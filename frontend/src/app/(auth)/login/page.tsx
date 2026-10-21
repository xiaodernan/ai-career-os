import { CredentialsForm } from "@/components/auth/credentials-form";
import { sessionNotice } from "@/lib/session-expiry";

export default async function LoginPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const { reason } = await searchParams;
  return <CredentialsForm mode="login" notice={sessionNotice(reason)} />;
}
